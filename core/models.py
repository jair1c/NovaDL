from dataclasses import dataclass, field
from typing import Optional


@dataclass
class QueueItem:
    url: str
    format_type: str
    output_dir: str
    add_thumbnail: bool
    quality: str
    download_playlist: bool
    rate_limit: str
    # v0.6.4
    extra_args: list = field(default_factory=list)
    output_template: Optional[str] = None
    retries: int = 0
    # v1.2
    proxy: Optional[str] = None
    subtitle_lang: Optional[str] = None


@dataclass
class HistoryItem:
    url: str
    format_type: str
    output_dir: str
    download_playlist: bool


@dataclass
class ErrorHistoryItem:
    url: str
    format_type: str
    error_message: str
