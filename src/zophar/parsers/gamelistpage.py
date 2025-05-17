from typing import Iterator, cast

from bs4 import Tag
from yarl import URL

from .types import GameEntry, GameListPage


def _parse_npages(page: Tag) -> tuple[int, int]:
    # Gamelists with more than 200 items may be divided into multiple pages.
    # Each page in this case have 'counter' tag string.
    # Search results ALWAYS displayed in one page.
    if (x := cast(Tag, page.find("p", class_="counter"))) is None:
        return 1, 1

    # Split text 'Page {npage} of {total_pages}' and convert to integers
    _, npage, _, total_pages = str(x.string).split()

    return int(npage), int(total_pages)


def _parse_list(page: Tag) -> Iterator[GameEntry]:
    # Empty search result do not have table.
    if (table := page.table) is None:
        return

    # First and last rows always are headers.
    if len(rows := cast(list[Tag], table("tr"))) <= 2:
        return

    for row in rows[1:-1]:  # ignore headers
        # Get two first cells in row with classes 'image' and 'name'.
        image, name = cast(list[Tag], row("td"))[:2]

        # Cover image is `optional`, name is `mandatory`.
        image, name = image.img, cast(Tag, name.a)

        if image is not None:
            # Replace URL with large image version (not so large, about 200px).
            x = str(image["src"]).replace("/thumbs_small/", "/thumbs_large/")
            image = URL(x)  # not encoded!

        yield GameEntry(
            name=str(name.string),
            path=str(name["href"])[7:],  # remove prefix '/music/'
            cover=image,
        )


def parse_gamelistpage(page: Tag) -> GameListPage:
    """Parses page of `gamelistpage` class to `GameListPage` instance."""

    npage, total_pages = _parse_npages(page)

    return GameListPage(
        entries=list(_parse_list(page)),
        title=str(cast(Tag, page.h2).string),
        description=str(cast(Tag, page.p).string),
        page=npage,
        total_pages=total_pages,
    )
