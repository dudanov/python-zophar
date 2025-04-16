from __future__ import annotations

import logging
from typing import cast

from bs4 import Tag

from ..models import Browsable
from .parsers import get_tag_from_html, item_from_link

_LOGGER = logging.getLogger(__name__)


def parse_infopage(html: str) -> list[Browsable]:
    """Scrapes child items from `infopage`."""

    page = get_tag_from_html(html, "infopage")

    return [x for x in map(item_from_link, cast(list[Tag], page("a"))) if x]
