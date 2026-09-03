from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass(frozen=True)
class Folder:
    uuid: str
    name: str


@dataclass(frozen=True)
class Document:
    uuid: str
    name: str
    download_url: Optional[str] = None


@dataclass
class Statistics:
    folders: int = 0
    pages: int = 0
    documents: int = 0
    downloaded: int = 0
    cached: int = 0
    skipped: int = 0
    errors: int = 0

    def add(self, other: "Statistics"):
        self.pages += other.pages
        self.documents += other.documents
        self.downloaded += other.downloaded
        self.cached += other.cached
        self.skipped += other.skipped
        self.errors += other.errors