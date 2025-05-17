import logging
from typing import Final, Mapping, cast

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer

from .types import Browsable

type Consoles = Mapping[str, str]
"""Mapping between console name and search id"""

type Menu = Mapping[str, list[Browsable]]
"""Root menu mapping"""

_BLACKLIST: Final = ["Emulated Files"]
_LOGGER: Final = logging.getLogger(__name__)


def _menu(sidebar: Tag) -> Menu:
    blacklisted = True
    menu: dict[str, list[Browsable]] = {}

    for tag in cast(list[Tag], sidebar(["a", "h2"])):
        name = str(tag.string)

        if (path := tag.get("href")) is None:
            # Menu section header

            blacklisted = name in _BLACKLIST

            _LOGGER.debug(
                "Found menu section header: '%s', blacklisted: %s.",
                name,
                blacklisted,
            )

            if not blacklisted:
                menu[name] = (section := [])

        elif not blacklisted:
            # Menu browsable item

            path = str(path).removeprefix("/music/")
            section.append(item := Browsable(name, path))

            _LOGGER.debug("Found menu item: %s", item)

    return menu


def _consoles(select: Tag) -> Consoles:
    return {
        str(x.string): str(x["value"])
        for x in cast(list[Tag], select("option"))
    }


def parse_searchpage(html: str) -> tuple[Menu, Consoles]:
    """Search page parser"""

    x = SoupStrainer("div", id=["sidebarSearch", "searchsearch"])
    x = BeautifulSoup(html, "lxml", parse_only=x)
    sidebar, select = cast(list[Tag], x.contents)

    return _menu(sidebar), _consoles(select)
