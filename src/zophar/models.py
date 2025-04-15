import dataclasses as dc
import datetime as dt
from typing import Literal, Mapping

from yarl import URL

PageType = Literal["infopage", "gamelist", "gamepage"]


@dc.dataclass(slots=True)
class Browsable:
    """Browsable entity. Have `path` property."""

    path: str
    """Identifier"""
    name: str
    """Name"""


@dc.dataclass(slots=True)
class MenuItem(Browsable):
    """Menu item"""

    menu: str
    """Menu top item"""


@dc.dataclass(slots=True, kw_only=True)
class GameEntry(Browsable):
    """Game list entry"""

    cover: URL | None = None
    """URL to cover image"""
    release_date: Browsable | None = None
    """Release date"""
    developer: Browsable | None = None
    """Developer"""


@dc.dataclass(slots=True)
class GameTrack:
    """Game music track"""

    title: str
    """Title"""
    duration: dt.timedelta
    """Duration"""
    url: Mapping[str, URL]
    """Mapping with URLs to audio files by it's extension"""


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
