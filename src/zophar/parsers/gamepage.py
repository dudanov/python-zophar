import datetime as dt
import logging
import re
from typing import Any, Iterator, cast

from bs4 import Tag
from yarl import URL

from .helpers import (
    ParseError,
    get_img_src,
    get_string,
    get_tag,
    get_tag_from_html,
)
from .models import (
    GAMEINFO_FIELDS,
    Browsable,
    GameInfo,
    GameTrack,
)

_LOGGER = logging.getLogger(__name__)


_RE_ARCHIVE = re.compile(r"(?<= \()\w+(?=\)\.zophar\.zip)", re.A)
"""RegExp for getting type of music archive from URL"""


def _tracklist(tracklist: Tag) -> Iterator[GameTrack]:
    for raw in cast(list[Tag], tracklist("tr")):
        title = get_string(raw, class_="name")

        m, s = map(int, get_string(raw, class_="length").split(":", 1))
        length, urls = dt.timedelta(minutes=m, seconds=s), {}

        for a in cast(list[Tag], raw("a")):
            url = URL(str(a["href"]), encoded=True)
            format = url.suffix[1:].lower()
            urls[format] = url

        yield GameTrack(title, length, urls)


def _mass_download(mass_download: Tag) -> Iterator[tuple[str, URL]]:
    for raw in cast(list[Tag], mass_download("a")):
        url = URL(str(raw["href"]), encoded=True)

        if not (m := _RE_ARCHIVE.search(url.name)):
            raise ParseError("Could not find archive type.")

        yield m.group().lower(), url


def _music_info(info: Tag) -> Iterator[tuple[str, Any]]:
    yield "name", get_string(info, name="h2")

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

        yield key, data


def parse_gamepage(html: str) -> GameInfo:
    """Gamepage parser"""

    args: dict[str, Any] = {}
    page = get_tag_from_html(html, "gamepage")

    def _tag(x: str):
        return get_tag(page, id=x)

    # id `music_cover`: [cover]
    tag = _tag("music_cover")
    args["cover"] = get_img_src(tag)

    # id `music_info`: [name, console, etc.]
    tag = _tag("music_info")
    args |= _music_info(tag)

    # id `mass_download`: [archive]
    tag = _tag("mass_download")
    args["archives"] = dict(_mass_download(tag))

    # id `tracklist`: [tracks]
    tag = _tag("tracklist")
    args["tracks"] = list(_tracklist(tag))

    for key in tuple(args):
        if key in GAMEINFO_FIELDS:
            continue

        value = args.pop(key)
        _LOGGER.debug("Field '%s' not exist. Value: '%s'.", key, value)

    return GameInfo(**args)
