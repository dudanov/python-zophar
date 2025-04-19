from typing import cast

from bs4 import Tag

from .helpers import browsable_from_link, get_tag_from_html
from .models import Container


def parse_infopage(html: str) -> list[Container]:
    """Scrapes child items from `infopage`."""

    page = get_tag_from_html(html, "infopage")

    return [
        x for x in map(browsable_from_link, cast(list[Tag], page("a"))) if x
    ]
