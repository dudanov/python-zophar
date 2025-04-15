from __future__ import annotations

import datetime as dt
import logging
import re
from types import MappingProxyType
from typing import Any, cast

from bs4 import BeautifulSoup, Tag
from yarl import URL

from .models import (
    GAMEINFO_FIELDS,
    Browsable,
    GameEntry,
    GameInfo,
    GameTrack,
    MenuItem,
)

_LOGGER = logging.getLogger(__name__)


_BLACKLIST = ["Emulated Files"]
_RE_ARCHIVE = re.compile(r"(?<= \()\w+(?=\)\.zophar\.zip)", re.A)


class ParseError(Exception):
    """Scraping error exception"""


class WrongItemError(ParseError):
    """Scraping error exception"""


def get_tag(root: Tag, **kwargs: Any) -> Tag:
    if x := root.find(**kwargs):
        return cast(Tag, x)

    raise ParseError(f"Tag not found. Params: {kwargs}.")


def get_tag_from_html(html: str, id: str) -> Tag:
    soup = BeautifulSoup(html, "lxml")

    try:
        return get_tag(soup, id=id)

    except ParseError:
        raise WrongItemError("This item possibly for another method.")


def get_img_src(root: Tag) -> URL | None:
    if img := root.img:
        return URL(str(img["src"]), encoded=True)


def get_string(tag: Tag, **kwargs):
    if kwargs:
        tag = get_tag(tag, **kwargs)

    return " ".join(tag.stripped_strings)


def parse_link(root: Tag, **kwargs) -> tuple[str, URL]:
    string = get_string(root)

    if root.name != "a":
        root = get_tag(root, name="a", **kwargs)

    path = str(root["href"]).removeprefix("/music/")

    return string, URL(path, encoded=True)


def _item_from_link[T: Browsable](
    tag: Tag, *, cls: type[T] = Browsable
) -> T | None:
    """Creates Entity instance from tag"""

    try:
        name, url = parse_link(tag)

    except ParseError:
        return

    if name and (path := url.raw_path):
        return cls(path, name)


def parse_mainpage(
    html: str,
) -> tuple[MappingProxyType[str, MenuItem], MappingProxyType[str, str]]:
    """Main page parser"""

    menu_items, blacklisted = {}, True
    page = BeautifulSoup(html, "lxml")
    sidebar = get_tag(page, id="sidebarSearch")

    for tag in cast(list[Tag], sidebar(re.compile(r"^[ah]"), string=True)):
        name = cast(str, tag.string)

        if (path := tag.get("href")) is None:
            # Root menu category
            blacklisted = name in _BLACKLIST

            _LOGGER.debug(
                "Found top menu entry: '%s', blacklisted: %s.",
                name,
                blacklisted,
            )

            if not blacklisted:
                menu = name

            continue

        # Link
        if blacklisted:
            continue

        path = str(path)

        if not path.startswith("/music/"):
            continue

        path = path[7:]  # remove prefix `/music/`

        _LOGGER.debug("Found menu entry: '%s', path: '%s'.", name, path)

        menu_items[path] = MenuItem(path, name, menu)

    # parsing available platforms for search engine
    select_options = cast(list[Tag], get_tag(page, name="select")("option"))
    platforms = {cast(str, x.string): str(x["value"]) for x in select_options}

    return MappingProxyType(menu_items), MappingProxyType(platforms)


def _parse_npages(page: Tag) -> int:
    """Returns number of available pages"""

    try:
        counter = get_string(page, class_="counter")

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
        return get_tag(raw, class_=x)

    # class `name`: (mandatory)
    assert (game := _item_from_link(_tag("name"), cls=GameEntry))
    # class `image`: (optional)
    game.cover = get_img_src(_tag("image"))
    # class `year`: (optional)
    game.release_date = _item_from_link(_tag("year"))
    # class `developer`: (optional)
    game.developer = _item_from_link(_tag("developer"))

    return game


def parse_gamelistpage(html: str) -> tuple[list[GameEntry], int]:
    """Scrapes list of game entries from `gamelistpage`."""

    page = get_tag_from_html(html, "gamelistpage")

    return list(
        map(
            _parse_gamelist_raw,
            cast(list[Tag], page("tr", class_=re.compile("^regularrow"))),
        )
    ), _parse_npages(page)


def parse_gamepage(html: str, path: str) -> GameInfo:
    """Gamepage parser"""

    args: dict[str, Any] = {"path": path}
    page = get_tag_from_html(html, "gamepage")

    def _tag(x: str):
        return get_tag(page, id=x)

    # id `music_cover`: [cover]
    cover = _tag("music_cover")
    args["cover"] = get_img_src(cover)

    # id `music_info`: [name, console, etc.]
    info = _tag("music_info")
    args["name"] = get_string(info, name="h2")

    for raw in cast(list[Tag], info("p")):
        # reading name and make key
        name = get_string(raw, class_="infoname")
        key = name.removesuffix(":").lower().replace(" ", "_")

        # reading data. if data have link make it `Browsable`.
        tag = get_tag(raw, class_="infodata")
        data = get_string(tag)

        if a := tag.a:
            path = str(a["href"]).removeprefix("/music/")
            data = Browsable(path, data)

        args[key] = data

    # id `mass_download`: [archive]
    download, archives = _tag("mass_download"), {}

    for raw in cast(list[Tag], download("a")):
        url = URL(str(raw["href"]), encoded=True)

        if not (m := _RE_ARCHIVE.search(url.name)):
            raise ParseError("Could not find archive type.")

        archives[m.group().lower()] = url

    args["archives"] = archives

    # id `tracklist`: [tracks]
    tracklist, tracks = _tag("tracklist"), []

    for raw in cast(list[Tag], tracklist("tr")):
        title = get_string(raw, class_="name")

        m, s = map(int, get_string(raw, class_="length").split(":", 1))
        duration, urls = dt.timedelta(minutes=m, seconds=s), {}

        for a in cast(list[Tag], raw("a")):
            url = URL(str(a["href"]), encoded=True)
            format = url.suffix[1:].lower()
            urls[format] = url

        tracks.append(GameTrack(title, duration, urls))

    args["tracks"] = tracks

    for key in tuple(args):
        if key not in GAMEINFO_FIELDS:
            value = args.pop(key)
            _LOGGER.debug("Field '%s' not exist. Value: '%s'.", key, value)

    return GameInfo(**args)


def parse_infopage(html: str) -> list[Browsable]:
    """Scrapes child items from `infopage`."""

    page = get_tag_from_html(html, "infopage")

    return [x for x in map(_item_from_link, cast(list[Tag], page("a"))) if x]
