import asyncio
import datetime as dt
import logging

from .browser import ZopharMusicBrowser

logging.basicConfig(level=logging.DEBUG)


async def main():
    async with ZopharMusicBrowser() as cli:
        print(f"Menu root:  {cli.menu_root}\n")
        print(f"Menu items: {cli.menu_items}\n")
        print(f"Available platforms: {cli.platforms}\n")

        nes = cli.menu_items[0]
        print(f"Getting first menu item: {nes}")

        battle = await cli.search("battle", platform="Arcade")
        print(battle)

        async for x in cli.game_list_generator(nes):
            games = await cli.game_info_batch(x)

            for x in games:
                for x in x.tracks:
                    if x.duration > dt.timedelta(seconds=30):
                        continue
                    print(x)
                print()


asyncio.run(main())
