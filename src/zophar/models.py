import dataclasses as dc
import datetime as dt

from yarl import URL


@dc.dataclass(slots=True, kw_only=True)
class BrowsableItem:
    """Browsable entity. Have `path` property."""

    id: str
    """Identifier"""
    name: str
    """Name"""

    @property
    def path(self) -> str:
        """Relative path to object"""

        return self.id


@dc.dataclass(slots=True, kw_only=True)
class MenuItem(BrowsableItem):
    """Menu item"""

    menu: str
    """Menu top item"""


@dc.dataclass(slots=True, kw_only=True)
class ChildItem(BrowsableItem):
    """Browsable item that have parent"""

    parent_id: str
    """Parent identifier"""

    @property
    def path(self) -> str:
        """Relative path to object"""

        return f"{self.parent_id}/{self.id}"


@dc.dataclass(slots=True)
class GameEntry(ChildItem):
    """Game list entry"""

    cover: URL | None = None
    """URL to cover image"""
    release_date: ChildItem | None = None
    """Release date"""
    developer: ChildItem | None = None
    """Developer"""


@dc.dataclass(slots=True, kw_only=True)
class GameTrack:
    """Game music track"""

    title: str
    """Title"""
    duration: dt.timedelta
    """Duration"""
    url: URL
    """URL to MP3 file"""


@dc.dataclass(slots=True)
class GameInfo(GameEntry):
    """"""

    console: str = dc.field(init=False)
    """Console"""
    composer: str | None = None
    """Composer"""
    publisher: ChildItem | None = None
    """Publisher"""
    alternative_name: str | None = None
    """Alternative name"""
    ripped_by: str | None = None
    """Ripped by"""
    mp3s_by: str | None = None
    """MP3s by"""
    tagged_by: str | None = None
    """Tagged by"""
    emu_archive: URL | None = None
    """URL to ZIP with original music files"""
    mp3_archive: URL | None = None
    """URL to ZIP with MP3 music files"""
    flac_archive: URL | None = None
    """URL to ZIP with FLAC music files"""
    tracks: list[GameTrack] = dc.field(init=False)
    """Soundtrack"""
