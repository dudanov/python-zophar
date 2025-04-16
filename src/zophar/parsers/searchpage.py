import logging
import re
from types import MappingProxyType
from typing import cast

from bs4 import BeautifulSoup, Tag

from ..models import Menu, Platforms
from .helpers import get_tag

_LOGGER = logging.getLogger(__name__)


_BLACKLIST = ["Emulated Files"]


def parse_searchpage(html: str) -> tuple[Menu, Platforms]:
    """Search page parser"""

    menu_items: dict[str, dict[str, str]] = {}
    page, blacklisted = BeautifulSoup(html, "lxml"), True
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

        menu_items.setdefault(menu, {})[path] = name

    # parsing available platforms for search engine
    select_options = cast(list[Tag], get_tag(page, name="select")("option"))
    platforms = {cast(str, x.string): str(x["value"]) for x in select_options}

    return MappingProxyType(menu_items), MappingProxyType(platforms)
