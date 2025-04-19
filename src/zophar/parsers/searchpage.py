import logging
import re
from types import MappingProxyType
from typing import Mapping, cast

from bs4 import BeautifulSoup, Tag

from .helpers import get_tag
from .models import Container

type Platforms = Mapping[str, str]

_LOGGER = logging.getLogger(__name__)


_BLACKLIST = ["Emulated Files"]


def parse_searchpage(html: str) -> tuple[Container, Platforms]:
    """Search page parser"""

    menu = Container("", "")
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
                menu.add(folder := Container("", name))

            continue

        # Link
        if blacklisted:
            continue

        path = str(path)

        if not path.startswith("/music/"):
            continue

        path = path[7:]  # remove prefix `/music/`

        _LOGGER.debug("Found menu entry: '%s', path: '%s'.", name, path)

        folder.add(Container(path, name))

    # parsing available platforms for search engine
    select_options = cast(list[Tag], get_tag(page, name="select")("option"))
    platforms = {cast(str, x.string): str(x["value"]) for x in select_options}

    return menu, MappingProxyType(platforms)
