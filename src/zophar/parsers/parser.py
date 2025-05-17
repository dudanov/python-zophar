from typing import cast

from bs4 import BeautifulSoup, Tag
from bs4.filter import SoupStrainer

from .gamelistpage import parse_gamelistpage
from .gamepage import parse_gamepage
from .infopage import parse_infopage
from .types import GameListPage, GamePage, InfoPage, PageType, ParseError

type PagesSupported = GameListPage | GamePage | InfoPage


def parse_page(html: str) -> PagesSupported:
    """Parses all supported pages"""

    x = SoupStrainer("div", id=list(PageType))
    soup = BeautifulSoup(html, "lxml", parse_only=x)

    if len(contents := cast(list[Tag], soup.contents)) != 1:
        raise ParseError("Unsupported page. May be broken link.")

    page = contents[0]

    match PageType(page["id"]):
        case PageType.GameListPage:
            return parse_gamelistpage(page)

        case PageType.GamePage:
            return parse_gamepage(page)

        case PageType.InfoPage:
            return parse_infopage(page)
