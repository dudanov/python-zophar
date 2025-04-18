from __future__ import annotations

import dataclasses as dc
import datetime as dt
from typing import Literal, Mapping

from slugify import slugify
from yarl import URL

type PageType = Literal["infopage", "gamelist", "gamepage"]

type MenuItems = Mapping[str, Folder]
"""Menu items: path - name"""

type Menu = Mapping[str, MenuItems]
"""Menu: `Root name` - `Menu item`"""

type Platforms = Mapping[str, str]


@dc.dataclass(slots=True)
class GameTrack:
    """Game music track"""

    title: str
    """Title"""
    length: dt.timedelta
    """Duration"""
    url: Mapping[str, URL]
    """Mapping with URLs to audio files by it's extension"""


@dc.dataclass(slots=True)
class Browsable:
    """Browsable entity. Have `path` property."""

    path: str
    """Request path"""
    name: str
    """Name"""

    @property
    def parts(self) -> tuple[str, str]:
        """Parts of the path: parent and identifier"""

        parent, _, id = self.path.rpartition("/")
        return parent, id


@dc.dataclass(slots=True)
class Folder(Browsable):
    """Browsable entity. Have `path` property."""

    children: dict[str, Folder] = dc.field(default_factory=dict)
    """Children"""

    @property
    def id(self):
        """"""

        return self.path.rsplit("/", 1)[-1]

    def get(self, path: str) -> Folder:
        """"""

        if not path:
            return self

        if path.startswith("/"):
            raise KeyError("Absolute paths not supported")

        id, _, path = path.partition("/")

        if x := self.children.get(id):
            return x.get(path)

        raise KeyError("Could not get child")

    def add(self, *items: Folder) -> None:
        """"""

        for x in items:
            if not (id := x.id):
                id = slugify(x.name)

            self.children[id] = x


@dc.dataclass(slots=True, kw_only=True)
class GameEntry(Browsable):
    """Game list entry"""

    cover: URL | None = None
    """URL to cover image"""
    release_date: Browsable | None = None
    """Release date"""
    developer: Browsable | None = None
    """Developer"""


@dc.dataclass(slots=True, kw_only=True)
class GameInfo(GameEntry):
    """"""

    console: str
    """Console"""
    publisher: Browsable | None = None
    """Publisher"""
    archives: Mapping[str, URL]
    """Mapping with URLs to music archives by it's type"""
    tracks: list[GameTrack]
    """Soundtrack"""

    def _first_track(self) -> Mapping[str, URL]:
        if track := next(iter(self.tracks), None):
            return track.url

        return {}

    def has_format(self, format: str) -> bool:
        return format in self._first_track()

    @property
    def formats(self) -> list[str]:
        return list(self._first_track())


GAMEINFO_FIELDS = {x.name for x in dc.fields(GameInfo)}
