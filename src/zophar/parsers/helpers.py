from __future__ import annotations

import logging
from typing import Any, cast

from bs4 import BeautifulSoup, Tag
from yarl import URL

from ..models import Browsable

_LOGGER = logging.getLogger(__name__)


class ParseError(Exception):
    """Scraping error exception"""


def get_tag(root: Tag, **kwargs: Any) -> Tag:
    if x := root.find(**kwargs):
        return cast(Tag, x)

    raise ParseError(f"Tag not found. Params: {kwargs}.")


def get_tag_from_html(html: str, id: str) -> Tag:
    soup = BeautifulSoup(html, "lxml")

    try:
        return get_tag(soup, id=id)

    except ParseError:
        raise ParseError("This item possibly for another method.")


def get_img_src(root: Tag) -> URL | None:
    if img := root.img:
        return URL(str(img["src"]), encoded=True)


def get_string(tag: Tag, **kwargs):
    if kwargs:
        tag = get_tag(tag, **kwargs)

    return " ".join(tag.stripped_strings)


def parse_link(root: Tag, **kwargs) -> tuple[str, URL]:
    string = get_string(root)

    if root.name != "a":
        root = get_tag(root, name="a", **kwargs)

    path = str(root["href"]).removeprefix("/music/")

    return string, URL(path, encoded=True)


def item_from_link[T: Browsable](
    tag: Tag, *, cls: type[T] = Browsable
) -> T | None:
    """Creates Entity instance from tag"""

    try:
        name, url = parse_link(tag)

    except ParseError:
        return

    if name and (path := url.raw_path):
        return cls(path, name)
