from __future__ import annotations

import logging
from typing import Any, cast

from bs4 import BeautifulSoup, Tag
from yarl import URL

from ..models import Browsable

_LOGGER = logging.getLogger(__name__)


class ParseError(Exception):
    """Parsing error exception"""


def get_tag(root: Tag, **kwargs: Any) -> Tag:
    if x := root.find(**kwargs):
        return cast(Tag, x)

    raise ParseError(f"Tag not found. Search params: {kwargs}.")


def get_tag_from_html(html: str, id: str) -> Tag:
    soup = BeautifulSoup(html, "lxml")

    try:
        return get_tag(soup, id=id)

    except ParseError:
        raise ParseError("This page for another parsing method.")


def get_img_src(root: Tag) -> URL | None:
    if img := root.img:
        return URL(str(img["src"]), encoded=True)


def get_string(tag: Tag, **kwargs):
    if kwargs:
        tag = get_tag(tag, **kwargs)

    return " ".join(tag.stripped_strings)


def parse_link(tag: Tag, **kwargs) -> dict[str, Any]:
    """Parse link to args for create `Browsable` based objects"""

    if not (string := get_string(tag)):
        raise ParseError("Tag without name.")

    if tag.name != "a":
        tag = get_tag(tag, name="a", **kwargs)

    path = str(tag["href"]).removeprefix("/music/")
    url = URL(path, encoded=True)

    return {"path": url.raw_path, "name": string}


def browsable_from_link(tag: Tag) -> Browsable | None:
    """Creates `Browsable` from tag"""

    try:
        return Browsable(**parse_link(tag))

    except ParseError:
        pass
