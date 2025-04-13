import asyncio
import itertools as it
import logging
from types import MappingProxyType
from typing import AsyncIterator, Iterable

import aiohttp
from yarl import URL

from .const import BASE_URL
from .models import BrowsableItem, ChildItem, GameEntry, GameInfo, MenuItem
from .parsers import (
    parse_gamelistpage,
    parse_gamepage,
    parse_infopage,
    parse_mainpage,
)

_LOGGER = logging.getLogger(__name__)


class ZopharMusicBrowser:
    _cli: aiohttp.ClientSession
    _main_menu: MappingProxyType[str, MenuItem]
    _platforms: MappingProxyType[str, str]
    _games_cache: dict[str, GameInfo]

    def __init__(
        self,
        *,
        session: aiohttp.ClientSession | None = None,
    ) -> None:
        self._cli = session or aiohttp.ClientSession()
        self._close_connector = not session
        self._main_menu = MappingProxyType({})
        self._platforms = MappingProxyType({})
        self._games_cache = {}

    async def __aenter__(self):
        await self.open()
        return self

    def __aexit__(self, exc_type, exc_value, traceback):
        return self.close()

    async def _get(self, url_or_path: URL | str) -> str:
        url = BASE_URL.join(URL(url_or_path, encoded=True))
        async with self._cli.get(url) as x:
            _LOGGER.debug("GET %s", x.url)
            return await x.text()

    async def open(self) -> None:
        html = await self._get("search")
        self._main_menu, self._platforms = parse_mainpage(html)

    async def close(self):
        """Close"""

        if self._close_connector:
            await self._cli.close()

    @property
    def menu_root(self) -> list[str]:
        """Returns main menu items"""

        return list(dict.fromkeys(x.menu for x in self._main_menu.values()))

    @property
    def menu_items(self) -> list[MenuItem]:
        """Returns music categories"""

        return list(self._main_menu.values())

    @property
    def platforms(self) -> list[str]:
        """Returns available hardware platforms"""

        return list(self._platforms)

    async def game_list(
        self,
        item: BrowsableItem,
        *,
        page: int | None = None,
    ) -> tuple[list[GameEntry], int]:
        """
        Scrapes game list pages.

        Args:
            item: Browsable item.
            page: Page number. First page is `default`.

        Returns:
            Tuple of game entries list and number of available pages.
        """

        url = item.path

        if page and page > 1:
            url = URL.build(
                path=url,
                query_string=f"page={page}",
                encoded=True,
            )

        return parse_gamelistpage(await self._get(url))

    async def game_list_generator(
        self, item: BrowsableItem
    ) -> AsyncIterator[list[GameEntry]]:
        """
        Scrapes game lists page by page.

        Args:
            item: Browsable item.

        Returns:
            Lists of game entries.
        """

        for npage in it.count(1):
            games, pages = await self.game_list(item, page=npage)

            yield games

            if npage >= pages:
                break

    async def game_list_batch(self, item: BrowsableItem) -> list[GameEntry]:
        """
        Scrapes all game list.

        Args:
            item: Browsable item.

        Returns:
            Game entries list.
        """

        games, pages = await self.game_list(item)

        if pages < 2:
            return games

        result = await asyncio.gather(
            *(self.game_list(item, page=x) for x in range(2, pages + 1))
        )

        for x, _ in result:
            games.extend(x)

        return games

    async def info_page(self, item: BrowsableItem) -> list[ChildItem]:
        """
        Scrapes info pages (developers, publishers lists).

        Args:
            item: Browsable item.

        Returns:
            Items list.
        """

        return parse_infopage(await self._get(item.path))

    async def game_info(self, entry: GameEntry) -> GameInfo:
        """
        Scrapes game page.

        Args:
            entry: Game entry from game list.

        Returns:
            Full game information with soundtracks.
        """

        if x := self._games_cache.get(path := entry.path):
            return x

        info = parse_gamepage(await self._get(path), entry)
        self._games_cache[path] = info

        return info

    async def game_info_batch(
        self, entries: Iterable[GameEntry]
    ) -> list[GameInfo]:
        """
        Scrapes games pages.

        Args:
            entry: Game entry from games list.

        Returns:
            Full game information with soundtracks.
        """

        return await asyncio.gather(*map(self.game_info, entries))

    async def search(
        self,
        context: str,
        *,
        platform: str | None = None,
    ) -> list[GameEntry]:
        """
        Search games by context and optionally filtered by platform ID.

        Args:
            context: Game search context.
            platform: Filter by hardware platform (default: All).

        Returns:
            Game entries list.
        """

        if platform is None:
            id = "0"

        elif (id := self._platforms.get(platform)) is None:
            raise ValueError("Unknown platform: '%s'", platform)

        url = URL.build(
            path="search",
            query={
                "search": context,
                "search_consoleid": id,
            },
        )

        result, pages = parse_gamelistpage(await self._get(url))
        assert pages == 1

        return result
