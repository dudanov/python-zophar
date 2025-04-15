from yarl import URL

BASE_URL = URL("https://www.zophar.net/music/")
"""Base URL"""

KNOWN_INFOPAGES = {
    "developer",
    "publisher",
    "year",
}
"""Known paths of pages with class `infopage`"""
