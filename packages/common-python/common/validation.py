"""Pydantic schemas for API contracts.

These schemas use Pydantic BaseModel for server-side validation
in both the Platform and Edge Agent.
"""

from __future__ import annotations

from pydantic import BaseModel


class AgentRegisterRequest(BaseModel):
    name: str
    hostname: str
    platform: str
    agent_version: str
    capabilities: list[str]


class AgentHeartbeatRequest(BaseModel):
    status: str  # online, offline, syncing, error
    platform: str = ""
    hostname: str = ""
    ip_address: str = ""
    agent_version: str = ""
    capabilities: list[str] = []
    files_count: int = 0
    total_size_bytes: int = 0
    uptime_seconds: float = 0.0
    folders_monitored: int = 0


class SyncFilePayload(BaseModel):
    local_path: str
    file_hash: str
    file_size: int
    mime_type: str = ""
    modified_at: str = ""
    metadata: dict = {}
    extracted_text: str = ""
    markdown: str = ""
    content_blocks: list[dict] = []
    tables: list[dict] = []
    images: list[dict] = []
    language: str = "unknown"
    word_count: int = 0
    char_count: int = 0
    page_count: int = 0
    ocr_used: bool = False
    agent_version: str = ""
    processing_version: str = ""
    parser_version: str = ""
    ocr_engine: str = ""


class AgentSyncRequest(BaseModel):
    files: list[SyncFilePayload]
    stats: dict | None = None


class CommandPayload(BaseModel):
    command_type: str  # sync, scan, process, config_update, shutdown
    payload: dict = {}
