from __future__ import annotations

import logging
import re
from typing import cast

from bs4 import Tag

from ..models import GameEntry
from .helpers import (
    ParseError,
    browsable_from_link,
    get_img_src,
    get_string,
    get_tag,
    get_tag_from_html,
    parse_link,
)

_LOGGER = logging.getLogger(__name__)


def _parse_npages(page: Tag) -> int:
    """Returns number of available pages"""

    try:
        counter = get_string(page, class_="counter")

    except ParseError:
        return 1

    if m := re.match(r"Page \d{1,3} of (\d{1,3})$", counter):
        return int(m.group(1))

    raise ParseError(f"RegExp npages failed. Input: '{counter}'.")


def _parse_raw(raw: Tag) -> GameEntry:
    def _tag(x: str):
        return get_tag(raw, class_=x)

    # class `name`: (mandatory)
    tag = _tag("name")
    args = parse_link(tag)

    # class `image`: (optional)
    tag = _tag("image")
    args["cover"] = get_img_src(tag)

    # class `year`: (optional)
    tag = _tag("year")
    args["release_date"] = browsable_from_link(tag)

    # class `developer`: (optional)
    tag = _tag("developer")
    args["developer"] = browsable_from_link(tag)

    return GameEntry(**args)


def parse_gamelistpage(html: str) -> tuple[list[GameEntry], int]:
    """Scrapes list of game entries from `gamelistpage`."""

    page = get_tag_from_html(html, "gamelistpage")

    return list(
        map(
            _parse_raw,
            cast(list[Tag], page("tr", class_=re.compile("^regularrow"))),
        )
    ), _parse_npages(page)
