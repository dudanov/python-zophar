import asyncio
import datetime as dt
import logging

from .browser import ZopharMusicBrowser

logging.basicConfig(level=logging.DEBUG)


async def main():
    async with ZopharMusicBrowser() as cli:
        print(f"Menu root:  {cli.menu_root}\n")
        print(f"Menu items: {cli.menu}\n")
        print(f"Available platforms: {cli.platforms}\n")

        nes = cli.menu_name()
        print(f"Getting first menu item: {nes}")

        battle = await cli.search("battle", platform="Arcade")
        print(battle)

        async for x in cli.game_list_generator(nes):
            games = await cli.game_info_batch(x)

            for g in games:
                print(g)


asyncio.run(main())
