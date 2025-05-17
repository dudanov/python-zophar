from __future__ import annotations

import dataclasses as dc
import datetime as dt
import logging
from enum import STRICT, StrEnum, auto
from typing import Final, Iterator, Mapping

from yarl import URL

_LOGGER: Final = logging.getLogger(__name__)


class ParseError(Exception):
    """Parsing error exception"""


class PageType(StrEnum, boundary=STRICT):
    """Enum of supported page classes"""

    GameListPage = auto()
    """List of games entries"""
    GamePage = auto()
    """Game info page with soundtrack"""
    InfoPage = auto()
    """Simple page with links"""


class AudioFormat(StrEnum, boundary=STRICT):
    """Enum with used audio formats"""

    MP3 = auto()
    """MPEG Layer-3 lossy format"""
    FLAC = auto()
    """FLAC lossless format"""

    @property
    def mime(self) -> str:
        """MIME media type"""

        if self is AudioFormat.MP3:
            return "audio/mpeg"

        return f"audio/{self.value}"


@dc.dataclass(slots=True, frozen=True)
class Browsable:
    """Browsable entity. Have `path` property."""

    name: str
    """Name"""
    path: str
    """Encoded relative request path to webserver"""


@dc.dataclass(slots=True, kw_only=True, frozen=True)
class GameEntry(Browsable):
    """Game list entry"""

    cover: URL | None
    """URL to cover image"""


@dc.dataclass(slots=True, frozen=True)
class AudioTrack:
    """Audiotrack. Part of media playlist."""

    title: str
    """Title"""
    length: dt.timedelta
    """Duration"""
    mp3url: URL
    """URL to MP3 stream"""

    def url(self, format: AudioFormat) -> URL:
        """Returns URL to audio in specified format"""

        if format is AudioFormat.MP3:
            return self.mp3url

        return self.mp3url.with_suffix(f".{format.value}")


@dc.dataclass(slots=True, kw_only=True, frozen=True)
class GamePage:
    """Represents page of game description"""

    name: str
    """Name"""
    console: str
    """Console"""
    cover: URL | None
    """URL to cover image"""
    release_date: str | None = None
    """Release date"""
    developer: str | None = None
    """Developer"""
    publisher: str | None = None
    """Publisher"""
    originals: URL | None
    """Original platform (emulator) files"""
    archives: Mapping[AudioFormat, URL]
    """Media archives by audioformat"""
    tracks: tuple[AudioTrack, ...]
    """Playlist of MP3 audio"""

    def has_format(self, format: AudioFormat) -> bool:
        return format in self.archives

    def _m3u_lines(self, format: AudioFormat) -> Iterator[str]:
        yield "#EXTM3U"
        for track in self.tracks:
            yield f"#EXTINF:{track.length.seconds},{track.title}"
            yield track.url(format).human_repr()

    def m3u(self, format: AudioFormat = AudioFormat.MP3) -> str:
        """Returns M3U playlist string of specified format"""

        if self.has_format(format):
            return "\n".join(self._m3u_lines(format))

        raise FileNotFoundError


@dc.dataclass(slots=True, kw_only=True, frozen=True)
class GameListPage:
    """Represents one page of gamelist"""

    entries: list[GameEntry]
    """Game entries list"""
    title: str
    """Title"""
    description: str
    """Found statistics or any description"""
    page: int
    """Current page number"""
    total_pages: int
    """Total pages in this list"""


@dc.dataclass(slots=True, kw_only=True, frozen=True)
class InfoPage:
    """Represents simple list of links"""

    entries: list[Browsable]
    description: str
