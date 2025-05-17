from typing import Iterator, cast

from bs4 import Tag

from .types import Browsable, InfoPage


def _parse_page(page: Tag) -> Iterator[Browsable]:
    for x in cast(list[Tag], page("a")):
        name, path = str(x.string), str(x["href"])[7:]

        yield Browsable(name, path)


def parse_infopage(page: Tag) -> InfoPage:
    """Scrapes child items from `infopage`."""

    return InfoPage(
        entries=list(_parse_page(page)),
        description=str(cast(Tag, page.p).string),
    )
