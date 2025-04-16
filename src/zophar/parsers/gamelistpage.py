from __future__ import annotations

import logging
import re
from typing import cast

from bs4 import Tag

from ..models import GameEntry
from .helpers import (
    ParseError,
    get_img_src,
    get_string,
    get_tag,
    get_tag_from_html,
    item_from_link,
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


def _parse_gamelist_raw(raw: Tag) -> GameEntry:
    """Scrapes game record from `gamelistpage`."""

    assert raw.name == "tr"
    # tag class must be `regularrow` or `regularrow_image`
    assert any(x.startswith("regularrow") for x in raw["class"])

    def _tag(x: str):
        return get_tag(raw, class_=x)

    # class `name`: (mandatory)
    assert (game := item_from_link(_tag("name"), cls=GameEntry))
    # class `image`: (optional)
    game.cover = get_img_src(_tag("image"))
    # class `year`: (optional)
    game.release_date = item_from_link(_tag("year"))
    # class `developer`: (optional)
    game.developer = item_from_link(_tag("developer"))

    return game


def parse_gamelistpage(html: str) -> tuple[list[GameEntry], int]:
    """Scrapes list of game entries from `gamelistpage`."""

    page = get_tag_from_html(html, "gamelistpage")

    return list(
        map(
            _parse_gamelist_raw,
            cast(list[Tag], page("tr", class_=re.compile("^regularrow"))),
        )
    ), _parse_npages(page)
