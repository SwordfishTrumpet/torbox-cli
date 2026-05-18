"""Pydantic models for all TorBox API request/response schemas."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field


class TorBoxResponse(BaseModel):
    """Standard wrapper for all TorBox API responses."""

    success: bool
    error: str | None = None
    detail: str | None = None
    data: Any = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class User(BaseModel):
    """User account model."""

    id: int
    email: str | None = None
    plan: str | None = None
    api_key: str | None = Field(default=None, alias="apiKey")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UserSettings(BaseModel):
    """User settings model."""

    id: int | None = None
    email: str | None = None
    plan: str | None = None
    settings: dict[str, Any] | None = None
    email_notifications: bool | None = None
    web_notifications: bool | None = None
    rss_notifications: bool | None = None
    discord_id: str | None = None
    discord_notifications: bool | None = None
    telegram_id: str | None = None
    webhook_url: str | None = None
    seed_torrents: bool | None = None
    allow_zipped: bool | None = None
    google_drive_folder_id: str | None = None
    mega_email: str | None = None
    mega_password: str | None = None
    cdn_selection: str | None = None
    append_filename_to_links: bool | None = None
    stremio_quality: list[str] | None = None
    stremio_resolution: list[str] | None = None
    stremio_language: list[str] | None = None
    stremio_cache: list[str] | None = None
    dashboard_filter: dict[str, Any] | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Torrent(BaseModel):
    """Torrent download model."""

    id: int
    hash: str
    name: str | None = None
    size: int | None = None
    status: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TorrentList(BaseModel):
    """Paginated torrent list response."""

    data: list[Torrent] = []
    total: int | None = None
    offset: int | None = None
    limit: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UsenetDownload(BaseModel):
    """Usenet download model."""

    id: int
    name: str | None = None
    size: int | None = None
    status: str | None = None
    nzb_url: str | None = Field(default=None, alias="nzbUrl")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class UsenetDownloadList(BaseModel):
    """Paginated usenet download list response."""

    data: list[UsenetDownload] = []
    total: int | None = None
    offset: int | None = None
    limit: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WebDownload(BaseModel):
    """Web download model."""

    id: int
    link: str | None = None
    name: str | None = None
    size: int | None = None
    status: str | None = None
    hoster: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class WebDownloadList(BaseModel):
    """Paginated web download list response."""

    data: list[WebDownload] = []
    total: int | None = None
    offset: int | None = None
    limit: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Hoster(BaseModel):
    """Supported hoster model."""

    id: int | None = None
    name: str | None = None
    enabled: bool | None = None
    domains: list[str] | None = None
    url: str | None = None
    icon: str | None = None
    status: bool | None = None
    type: str | None = None
    note: str | None = None
    nsfw: bool | None = None
    daily_link_limit: int | None = None
    daily_link_used: int | None = None
    daily_bandwidth_limit: int | None = None
    daily_bandwidth_used: int | None = None
    per_link_size_limit: int | None = None
    regex: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class HosterList(BaseModel):
    """Hoster list response."""

    data: list[Hoster] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SearchEngine(BaseModel):
    """Search engine model."""

    id: int | None = None
    name: str | None = None
    enabled: bool | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    auth_id: int | None = None
    type: str | None = None
    url: str | None = None
    apikey: str | None = None
    active: bool | None = None
    valid: bool | None = None
    download_type: str | None = None
    indexers: list[str] | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class SearchEngineList(BaseModel):
    """Search engine list response."""

    data: list[SearchEngine] = []

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class Transaction(BaseModel):
    """User transaction model."""

    id: int
    type: str | None = None
    amount: float | None = None
    currency: str | None = None
    status: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class TransactionList(BaseModel):
    """Paginated transaction list response."""

    data: list[Transaction] = []
    total: int | None = None
    offset: int | None = None
    limit: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RSSFeed(BaseModel):
    """RSS feed model."""

    id: int
    url: str | None = None
    name: str | None = None
    enabled: bool | None = None
    last_updated: str | None = Field(default=None, alias="lastUpdated")
    created_at: str | None = Field(default=None, alias="createdAt")
    last_checked: str | None = Field(default=None, alias="lastChecked")
    auth_id: int | None = None
    source: str | None = None
    source_name: str | None = None
    do_regex: str | None = None
    dont_regex: str | None = None
    status: int | None = None
    scan_interval: int | None = None
    dont_older_than: int | None = None
    status_message: str | None = None
    type: str | None = None
    torrent_seeding: int | None = None
    state: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RSSFeedItem(BaseModel):
    """RSS feed item model."""

    id: int | None = None
    title: str | None = None
    link: str | None = None
    published: str | None = None
    feed_id: int | None = None
    created_at: str | None = Field(default=None, alias="createdAt")
    rss_name: str | None = None
    rss_url: str | None = None
    ignored: bool | None = None
    downloaded: bool | None = None
    name: str | None = None
    status: str | None = None
    status_message: str | None = None
    seed_torrents: bool | None = None
    type: str | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class RSSFeedList(BaseModel):
    """Paginated RSS feed list response."""

    data: list[RSSFeed] = []
    total: int | None = None
    offset: int | None = None
    limit: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class QueuedDownload(BaseModel):
    """Queued download model."""

    id: int
    type: str | None = None
    name: str | None = None
    status: str | None = None
    created_at: str | None = Field(default=None, alias="createdAt")

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class QueuedDownloadList(BaseModel):
    """Paginated queued download list response."""

    data: list[QueuedDownload] = []
    total: int | None = None
    offset: int | None = None
    limit: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class StreamMetadata(BaseModel):
    """Stream metadata model."""

    token: str | None = None
    type: str | None = None
    id: int | None = None
    file_id: int | None = Field(default=None, alias="fileId")
    urls: list[str] | None = None
    hls_url: str | None = None
    domain: str | None = None
    presigned_token: str | None = None
    subtitle_index: int | None = None
    audio_index: int | None = None
    resolution_index: int | None = None
    file_token: str | None = None
    is_transcoding: bool | None = None
    needs_transcoding: bool | None = None
    video: dict[str, Any] | None = None
    audios: list[dict[str, Any]] | None = None
    subtitles: list[dict[str, Any]] | None = None
    thumbnail: str | None = None
    chapters: list[dict[str, Any]] | None = None
    search_metadata: dict[str, Any] | None = None
    intro_information: dict[str, Any] | None = None
    scrobbling_enabled: bool | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class StreamData(BaseModel):
    """Stream data model."""

    token: str | None = None
    streams: list[dict[str, Any]] | None = None
    subtitles: list[dict[str, Any]] | None = None
    audio_tracks: list[dict[str, Any]] | None = None
    resolutions: list[dict[str, Any]] | None = None
    hls_url: str | None = None
    domain: str | None = None
    presigned_token: str | None = None
    subtitle_index: int | None = None
    audio_index: int | None = None
    resolution_index: int | None = None
    file_token: str | None = None
    is_transcoding: bool | None = None
    needs_transcoding: bool | None = None
    metadata: StreamMetadata | None = None
    search_metadata: dict[str, Any] | None = None
    intro_information: dict[str, Any] | None = None
    scrobbling_enabled: bool | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class DeviceCodeAuth(BaseModel):
    """Device code authentication flow model."""

    device_code: str | None = None
    code: str | None = None
    verification_url: str | None = None
    friendly_verification_url: str | None = None
    expires_at: str | None = None
    interval: int | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class CacheStatus(BaseModel):
    """Torrent cache status model."""

    hash: str | None = None
    cached: bool | None = None
    files: list[dict[str, Any]] | None = None

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)


class JSONEnvelope(BaseModel):
    """Normalized CLI JSON envelope per TRD section 7.2."""

    success: bool
    command: str
    data: Any = None
    error: str | None = None
    detail: str | None = None
    exit_code: int | None = None
    meta: dict[str, Any] = Field(default_factory=dict)

    model_config = ConfigDict(from_attributes=True, populate_by_name=True)
