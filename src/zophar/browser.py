import asyncio
import itertools as it
from typing import AsyncIterator, Final, Iterable, overload

import aiohttp
from yarl import URL

from .parsers import (
    Browsable,
    Consoles,
    GameEntry,
    GameListPage,
    GamePage,
    InfoPage,
    Menu,
    PagesSupported,
    ParseError,
    parse_page,
    parse_searchpage,
)

type PageLink = Browsable | URL | str
"""Supported page link types"""

_BASE_URL: Final = URL("https://www.zophar.net/music/", encoded=True)

_RANDOM_PATH: Final = "/random-music"


def _make_url(link: PageLink, page: int | None = None) -> URL:
    if isinstance(link, Browsable):
        link = URL(link.path, encoded=True)

    elif isinstance(link, str):
        link = URL(link)

    if page:
        query = {"page": page} if page > 1 else None
        link = link.with_query(query)

    return _BASE_URL.join(link)


class MusicBrowser:
    """Zophar's Game Music browser"""

    _cli: aiohttp.ClientSession
    _close_connector: bool
    _menu: Menu
    _consoles: Consoles
    _cache: dict[str, PagesSupported]

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._cli = session or aiohttp.ClientSession()
        self._close_connector = session is None
        self._menu = {}
        self._consoles = {}
        self._cache = {}

    async def __aenter__(self):
        try:
            await self.open()

        except aiohttp.ClientError:
            await self.close()
            raise

        return self

    async def __aexit__(self, exc_type, exc_value, traceback):
        await self.close()

    async def open(self) -> None:
        """
        Makes initial read of main menu struct and available
        hardware platforms.
        """

        url = _BASE_URL.joinpath("search")

        async with self._cli.get(url) as x:
            html = await x.text()

        self._menu, self._consoles = parse_searchpage(html)

    async def close(self):
        """Closes HTTPS client session"""

        if self._close_connector:
            await self._cli.close()

    @property
    def menu(self) -> Menu:
        """Main menu. Tree walking starting from here."""

        return self._menu

    @property
    def consoles(self) -> list[str]:
        """Available consoles (hardware platforms). Used for searching."""

        return list(self._consoles)

    @overload
    async def page(
        self,
        link: None = None,
    ) -> GamePage:
        """
        Returns random game page.

        Returns:
            Instance of random `GamePage`.
        """

    @overload
    async def page(
        self,
        link: PageLink,
        *,
        npage: int | None = None,
    ) -> PagesSupported:
        """
        Generic parser of all supported pages.

        Args:
            link: Any of supported link types.
            npage: Page number (used for game lists only). Default is first page.

        Returns:
            Instance of page entity.
        """

    async def page(
        self,
        link: PageLink | None = None,
        *,
        npage: int | None = None,
    ) -> PagesSupported:
        url = _make_url(link or _RANDOM_PATH, npage)

        if url.raw_path == _RANDOM_PATH:
            # URL is random game page, gets new URL to use caching.
            async with self._cli.get(url, allow_redirects=False) as x:
                if x.status != 302:
                    raise ParseError(
                        "Could not get random game. No redirection from server."
                    )

                location = x.headers["location"]

            url = URL(location).with_scheme("https")

        if page := self._cache.get(path_qs := url.path_qs):
            return page

        async with self._cli.get(url, allow_redirects=False) as x:
            if x.status != 200:
                raise ParseError("Page not found.")

            html = await x.text()

        self._cache[path_qs] = page = parse_page(html)

        return page

    async def gamelist_page(
        self,
        link: PageLink,
        *,
        npage: int | None = None,
    ) -> GameListPage:
        """
        Gets and parses the specified game list page.

        Args:
            link: Any supported page link type.
            npage: Page number. The default is the first page.

        Returns:
            Instance of the game list page entity `GameListPage`.
        """

        page = await self.page(link, npage=npage)
        assert isinstance(page, GameListPage)

        return page

    async def gamelist_iter(
        self,
        link: PageLink,
    ) -> AsyncIterator[GameListPage]:
        """
        Scrapes game lists page by page.

        Args:
            link: Any of supported link types.

        Returns:
            Instances of `GameListPage`.
        """

        for n in it.count(1):
            yield (x := await self.gamelist_page(link, npage=n))

            if x.page >= x.total_pages:
                break

    async def gamelist(self, link: PageLink) -> list[GameEntry]:
        """
        Scrapes all game list.

        Args:
            link: Any of supported link types.

        Returns:
            Game entries list.
        """

        page = await self.gamelist_page(link, npage=1)

        if (total := page.total_pages) < 2:
            return page.entries

        async with asyncio.TaskGroup() as tg:
            tasks = [
                tg.create_task(self.gamelist_page(link, npage=n))
                for n in range(2, total + 1)
            ]

        for x in tasks:
            page.entries.extend(x.result().entries)

        return page.entries

    async def infopage(self, link: PageLink) -> InfoPage:
        """
        Scrapes info pages (developers, publishers lists).

        Args:
            link: Any of supported link types.

        Returns:
            Items list.
        """

        page = await self.page(link)
        assert isinstance(page, InfoPage)

        return page

    async def gamepage(self, link: PageLink | None = None) -> GamePage:
        """
        Returns game page.

        Args:
            link: Any of supported link types. Default: random game page.

        Returns:
            Instance of `GamePage`.
        """

        page = await self.page(link)
        assert isinstance(page, GamePage)

        return page

    async def gamepages(
        self,
        links: Iterable[PageLink | None],
    ) -> list[GamePage]:
        """
        Scrapes games pages.

        Args:
            links: Iterable of any supported link types.

        Returns:
            List of `GamePage` instances.
        """

        async with asyncio.TaskGroup() as tg:
            tasks = [tg.create_task(self.gamepage(x)) for x in links]

        return [x.result() for x in tasks]

    async def search(
        self,
        context: str,
        *,
        console: str | None = None,
    ) -> GameListPage:
        """
        Search games by context and optionally filtered by platform ID.

        Args:
            context: Game search context.
            platform: Filter by hardware platform (default: All).

        Returns:
            Instance of `GameListPage`.
        """

        query, id = {"search": context}, "0"

        if console and (id := self._consoles.get(console)) is None:
            raise ValueError(f"Unknown console '{console}'.")

        if id != "0":
            query["search_consoleid"] = id

        link = URL.build(path="search", query=query)

        page = await self.gamelist_page(link)
        assert page.total_pages == 1

        return page
