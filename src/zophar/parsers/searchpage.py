from __future__ import annotations

import logging
import re
from types import MappingProxyType
from typing import cast

from bs4 import BeautifulSoup, Tag

from ..models import MenuItem
from .parsers import get_tag

_LOGGER = logging.getLogger(__name__)


_BLACKLIST = ["Emulated Files"]


def parse_mainpage(
    html: str,
) -> tuple[MappingProxyType[str, MenuItem], MappingProxyType[str, str]]:
    """Main page parser"""

    menu_items, blacklisted = {}, True
    page = BeautifulSoup(html, "lxml")
    sidebar = get_tag(page, id="sidebarSearch")

    for tag in cast(list[Tag], sidebar(re.compile(r"^[ah]"), string=True)):
        name = cast(str, tag.string)

        if (path := tag.get("href")) is None:
            # Root menu category
            blacklisted = name in _BLACKLIST

            _LOGGER.debug(
                "Found top menu entry: '%s', blacklisted: %s.",
                name,
                blacklisted,
            )

            if not blacklisted:
                menu = name

            continue

        # Link
        if blacklisted:
            continue

        path = str(path)

        if not path.startswith("/music/"):
            continue

        path = path[7:]  # remove prefix `/music/`

        _LOGGER.debug("Found menu entry: '%s', path: '%s'.", name, path)

        menu_items[path] = MenuItem(path, name, menu)

    # parsing available platforms for search engine
    select_options = cast(list[Tag], get_tag(page, name="select")("option"))
    platforms = {cast(str, x.string): str(x["value"]) for x in select_options}

    return MappingProxyType(menu_items), MappingProxyType(platforms)
