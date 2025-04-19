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

        nes = cli.menu.get("consoles")
        print(f"Getting first menu item: {nes}")


asyncio.run(main())
