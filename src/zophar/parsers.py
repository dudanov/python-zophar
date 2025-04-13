from __future__ import annotations

import datetime as dt
import logging
import re
from types import MappingProxyType
from typing import cast

from bs4 import BeautifulSoup, Tag
from yarl import URL

from .models import (
    ChildItem,
    GameEntry,
    GameInfo,
    GameTrack,
    MenuItem,
)

_LOGGER = logging.getLogger(__name__)


_BLACKLIST = ["Emulated Files"]


class ParseError(Exception):
    """Scraping error exception"""


class WrongItemError(ParseError):
    """Scraping error exception"""


def _find_tag(root: Tag, **kwargs) -> Tag:
    if x := root.find(**kwargs):
        return cast(Tag, x)

    raise ParseError(f"Could not find tag. Params: {kwargs}.")


def _html_page_id(html: str, id: str) -> Tag:
    try:
        return _find_tag(BeautifulSoup(html, "lxml"), id=id)

    except ParseError:
        raise WrongItemError("This item possibly for another method.")


def _img_url(root: Tag) -> URL | None:
    if img := root.img:
        return URL(str(img["src"]), encoded=True)


def _tag_str(tag: Tag, **kwargs):
    if kwargs:
        tag = _find_tag(tag, **kwargs)

    return " ".join(tag.stripped_strings)


def _parse_link(tag: Tag, **kwargs) -> tuple[str, URL]:
    string = _tag_str(tag)

    if tag.name != "a":
        tag = _find_tag(tag, name="a", **kwargs)

    url = str(tag["href"]).removeprefix("/music/")

    return string, URL(url, encoded=True)


def _item_from_link[T: ChildItem](
    tag: Tag, *, cls: type[T] = ChildItem
) -> T | None:
    """Creates Entity instance from tag"""

    try:
        name, url = _parse_link(tag)

    except ParseError:
        return

    if name and len(x := url.parts) == 2:
        return cls(id=x[1], name=name, parent_id=x[0])


def parse_mainpage(
    html: str,
) -> tuple[MappingProxyType[str, MenuItem], MappingProxyType[str, str]]:
    """Main page parser"""

    menu_items, blacklisted = {}, True
    page = BeautifulSoup(html, "lxml")
    sidebar = _find_tag(page, id="sidebarSearch")

    # available platforms for search engine
    select = _find_tag(page, name="select")
    select = {
        cast(str, x.string): str(x["value"])
        for x in cast(list[Tag], select("option"))
    }

    for tag in cast(list[Tag], sidebar(re.compile(r"^[ah]"), string=True)):
        name = cast(str, tag.string)

        if (path := tag.get("href")) is None:
            # Root menu category
            blacklisted = name in _BLACKLIST

            _LOGGER.debug(
                "Found menu category: '%s', blacklisted: %s.", name, blacklisted
            )

            if not blacklisted:
                menu = name

            continue

        # Link
        if blacklisted:
            continue

        id = str(path).removeprefix("/music").removeprefix("/")

        _LOGGER.debug("Found menu item: '%s', path: '%s'.", name, id)

        menu_items[id] = MenuItem(id=id, name=name, menu=menu)

    return MappingProxyType(menu_items), MappingProxyType(select)


def _parse_npages(page: Tag) -> int:
    """Returns number of available pages"""

    try:
        counter = _tag_str(page, class_="counter")

    except ParseError:
        return 1

    if m := re.match(r"Page \d{1,3} of (\d{1,3})$", counter):
        return int(m.group(1))

    raise ParseError(f"RegExp npages failed. Input: '{counter}'.")


def _parse_gamelist_raw(raw: Tag) -> GameEntry:
    """Scrapes game record from `gamelistpage`."""

    assert raw.name == "tr"
    # tag class must be `regularrow` or `regularrow_image`
    assert any(x.startswith("regularrow") for x in raw["class"])

    def _tag(x: str):
        return _find_tag(raw, class_=x)

    # class `name`: (mandatory)
    assert (game := _item_from_link(_tag("name"), cls=GameEntry))
    # class `image`: (optional)
    game.cover = _img_url(_tag("image"))
    # class `year`: (optional)
    game.release_date = _item_from_link(_tag("year"))
    # class `developer`: (optional)
    game.developer = _item_from_link(_tag("developer"))

    return game


def parse_gamelistpage(html: str) -> tuple[list[GameEntry], int]:
    """Scrapes list of game entries from `gamelistpage`."""

    page = _html_page_id(html, "gamelistpage")

    return list(
        map(
            _parse_gamelist_raw,
            cast(list[Tag], page("tr", class_=re.compile("^regularrow"))),
        )
    ), _parse_npages(page)


def parse_gamepage(html: str, entry: GameEntry) -> GameInfo:
    """Gamepage parser"""

    page = _html_page_id(html, "gamepage")

    def _tag(x: str):
        return _find_tag(page, id=x)

    # id `music_info`: [name, name_alternate, ]
    title = _tag_str(tag := _tag("music_info"), name="h2")

    game = GameInfo(id=entry.id, name=title, parent_id=entry.parent_id)

    _LOGGER.debug("Game: %s", title)

    for tag in cast(list[Tag], tag("p")):
        data = _find_tag(tag, class_="infodata")
        data = _item_from_link(data) or _tag_str(data)
        name = _tag_str(tag, class_="infoname")

        _LOGGER.debug("  %s %s", name, data)

        key = name.removesuffix(":").lower().replace(" ", "_")
        setattr(game, key, data)

    # id `music_cover`: [cover]
    game.cover = _img_url(_tag("music_cover"))

    # id `mass_download`: [mp3_archive, emu_archive]
    for tag in cast(list[Tag], _tag("mass_download")("a")):
        desc, url = _parse_link(tag)

        if desc.rfind(" MP3 ") != -1:
            game.mp3_archive = url

        elif desc.rfind(" original ") != -1:
            game.emu_archive = url

        elif desc.rfind(" FLAC ") != -1:
            game.flac_archive = url

        else:
            _LOGGER.debug("Unknown download link: '%s'.", desc)

    game.tracks = (tracks := [])

    for tag in cast(list[Tag], _tag("tracklist")("tr")):
        assert len(tm := _tag_str(tag, class_="length").split(":")) == 2

        tracks.append(
            GameTrack(
                title=_tag_str(tag, class_="name"),
                duration=dt.timedelta(minutes=int(tm[0]), seconds=int(tm[1])),
                url=_parse_link(tag)[1],
            )
        )

    return game


def parse_infopage(html: str) -> list[ChildItem]:
    """Scrapes child items from `infopage`."""

    page = _html_page_id(html, "infopage")

    return [x for x in map(_item_from_link, cast(list[Tag], page("a"))) if x]
