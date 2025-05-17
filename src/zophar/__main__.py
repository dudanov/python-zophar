import asyncio
import logging

from .browser import ZopharBrowser
from .parsers import ParseError

logging.basicConfig(level=logging.DEBUG)


async def main():
    async with ZopharBrowser() as cli:
        print(f"Available platforms: {cli.consoles}\n")
        print(f"Menu: {cli.menu}\n")

        while link := input(
            "Enter URL (absolute or relative) or empty to exit: "
        ):
            try:
                result = await cli.page(link)

            except ParseError as e:
                result = f"Error occured: {e}"

            print(f"\n{result}\n")


asyncio.run(main())
