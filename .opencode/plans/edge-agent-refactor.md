# Edge Agent Refactoring Plan — v2

## Goal

Refactor the architecture to enforce a clean **Executor vs Brain** boundary: the SaaS backend never directly accesses a customer's local filesystem. All file-system operations (scanning, reading, OCR, parsing) happen exclusively in the Edge Agent. The Edge Agent is a pure text extractor: it reads files, processes them, and sends only extracted text/metadata to the SaaS. The SaaS receives pre-processed text/metadata and handles AI orchestration, embeddings, chunking, search, and business logic. The SaaS never stores or accesses original files.

---

## Architecture Principle: Executor vs Brain

| Component | Role | Responsibilities |
|-----------|------|-----------------|
| **Edge Agent** | Executor | Filesystem access, folder monitoring, file reading, OCR (PaddleOCR/Tesseract), MinerU parsing, metadata extraction, sending extracted text/metadata to SaaS |
| **Platform (SaaS)** | Brain | Receives extracted text/metadata, LLM classification, entity extraction, relationship detection, knowledge graph, summaries, recommendations, business workflows, search, RAG, **chunking**, **embeddings**, **vector indexing** |

### Data Flow

```
Edge Agent                          SaaS Platform
--------                          ------------
File -> Parse -> OCR -> Extract ->   Receive text/metadata
                                      |
                                      +- Create Document
                                      +- Chunk text (SaaS)
                                      +- Generate embeddings (SaaS)
                                      +- Vector index (SaaS)
                                      +- LLM classify (SaaS)
                                      +- Extract entities (SaaS)
                                      +- Generate summary (SaaS)
```

## File Ingestion Flow

**Edge Agent is the only way to ingest files into the system.** The SaaS has no file upload capability.

1. User registers an Edge Agent and configures folders to monitor
2. Edge Agent reads files from local filesystem
3. Edge Agent processes files (parse, OCR, extract text/metadata)
4. Edge Agent sends extracted content to SaaS (text + metadata only, no file binaries)
5. SaaS creates Document, chunks text, generates embeddings, runs LLM classification

The SaaS never stores or accesses original files. It only receives and processes extracted text and metadata.

---

## Phase 1: Create Shared Packages

### 1a. packages/common-python/ -- Shared Python DTOs and Contracts

**[Added]** New shared package for both Platform and Edge Agent.

**New files:**

| File | Purpose |
|------|---------|
| `packages/common-python/pyproject.toml` | Package config, deps: pydantic>=2.0 |
| `packages/common-python/common/__init__.py` | Package init, version |
| `packages/common-python/common/models.py` | Shared DTOs (dataclasses/pydantic) |
| `packages/common-python/common/constants.py` | Shared constants |
| `packages/common-python/common/validation.py` | Pydantic API contract schemas |
| `packages/common-python/common/config.py` | Shared config constants |
| `packages/common-python/common/utils.py` | Shared utilities |

Key models in `common/models.py`:
- `FileMetadata` (path, hash, size, mime_type, magic_bytes, modified_at)
- `ContentBlock` (block_type, content, metadata, bbox, level)
- `ParsedTable` (html, rows, headers, caption, bbox)
- `ParsedImage` (image_path, description, bbox, width, height)
- `ExtractionResult` (text, metadata, page_count, word_count, char_count, tables)
- `DocumentProcessedEvent` -- event-oriented DTO for future message broker migration (RabbitMQ/Kafka/NATS). Contains: tenant_id, agent_id, file_id, checksum, metadata, extracted_text, markdown, content_blocks, tables, images, agent_version, processing_version, parser_version, ocr_engine, ocr_used, language, word_count, char_count, page_count.
- `DocumentProcessedResponse` (accepted, rejected, errors, pending_commands, document_ids)

Key constants in `common/constants.py`:
- `DOCUMENT_CATEGORIES` list
- `IMAGE_EXTENSIONS` frozenset
- `LIGHTWEIGHT_EXTENSIONS` set
- `DEFAULT_CHUNK_SIZE = 1000`, `DEFAULT_CHUNK_OVERLAP = 200`
  - **SaaS-only**: These constants are used exclusively by the SaaS platform for chunking. The edge agent must NOT use or depend on them -- the edge agent never chunks documents; chunking is a SaaS responsibility.
- `PROCESSING_VERSION = "edge-document-pipeline-v2"`

Key schemas in `common/validation.py`:
- `AgentRegisterRequest` (name, hostname, platform, agent_version, capabilities)
- `AgentHeartbeatRequest` (status, platform, hostname, ip_address, agent_version, capabilities, files_count, total_size_bytes, uptime_seconds, folders_monitored)
- `SyncFilePayload` -- per-file payload with all pre-processed fields + versioning
- `AgentSyncRequest` (files, stats)
- `CommandPayload` (command_type, payload)

### 1b. packages/common-types/ -- Shared TypeScript API Types

**[Added]** New shared package for frontend and future apps.

**New files:**

| File | Purpose |
|------|---------|
| `packages/common-types/package.json` | npm package config |
| `packages/common-types/tsconfig.json` | TypeScript config |
| `packages/common-types/src/index.ts` | Re-exports |
| `packages/common-types/src/agent.ts` | Agent types with versioning + capabilities |
| `packages/common-types/src/file.ts` | File types |
| `packages/common-types/src/document.ts` | Document types |
| `packages/common-types/src/search.ts` | Search types |
| `packages/common-types/src/pipeline.ts` | Pipeline types |
| `packages/common-types/src/auth.ts` | Auth types |
| `packages/common-types/src/dashboard.ts` | Dashboard types |
| `packages/common-types/src/provider.ts` | Provider types |
| `packages/common-types/src/common.ts` | Shared enums |

Key types in `agent.ts`:
- `Agent` -- with agent_version, capabilities, all tracking fields
- `AgentFolder` -- local_path, label, is_active, file_count
- `AgentCommand` -- command_type, payload, status, result
- `SyncFilePayload` -- all pre-processed fields + versioning (agent_version, processing_version, parser_version, ocr_engine)
- `ContentBlock`, `ParsedTable`, `ParsedImage`

**Modify:**
- `frontend/package.json` -- Add dependency: `"@ai-archive/common-types": "workspace:*"`
- `frontend/src/types/api.ts` -- Gradually re-export from `@ai-archive/common-types`
- `pnpm-workspace.yaml` -- Already includes `packages/*` (verify only)

---

## Phase 2: Enhance Sync Protocol

### 2a. Backend: Accept Pre-Processed Results on Sync

**[Modified]** The existing `POST /api/v1/agents/{agent_id}/sync/` endpoint is enhanced to accept full pre-processed data.

**Modify `backend/apps/agents/serializers.py`:**

Update `SyncFileSerializer`:
- [Added] content_blocks, tables, images (ListField of DictField)
- [Added] language, word_count, char_count, page_count
- [Added] ocr_used (BooleanField)
- [Added] agent_version, processing_version, parser_version, ocr_engine (CharFields)
- [Modified] Remove chunk_count -- SaaS creates chunks
- [Modified] Remove embeddings -- SaaS generates embeddings

**Modify `backend/apps/agents/views.py` -- `sync()` action:**
1. Create/update FileRecord with `source="agent"`
2. [Added] Create Document with pre-populated fields (markdown, content_blocks, tables, images, versioning)
3. [Modified] Queue only LLM operations (classify_document_task) -- NOT chunking/embedding

### 2b. Edge Agent: Send Pre-Processed Results

**[Modified]** Update edge agent to send full processing results. Do NOT send chunks or embeddings.

**Modify `edge_agent/sync/manager.py`:**
- Send: extracted_text, markdown, content_blocks, tables, images
- Send: language, word_count, char_count, page_count, ocr_used
- Send: agent_version, processing_version, parser_version, ocr_engine

**Modify `edge_agent/cli.py` -- `_process_file()`:**
- Collect all processing results (parse, OCR, metadata)
- [Modified] Do NOT chunk -- SaaS creates chunks
- Include all versioning fields in sync payload

### 2c. Backend: Process Agent-Synced Documents

**[Modified]** The pipeline has a single code path: agent-synced files. No file reading or OCR on the SaaS side.

**Modify `backend/core/infrastructure/pipelines/document_pipeline.py`:**
- `process()`: Use pre-existing text from Document (sent by edge agent)
- SaaS creates chunks + embeddings + LLM classification from extracted text
- Remove all file reading, OCR, and parsing logic from the pipeline

---

## Phase 3: Remove Backend Filesystem Access

**[Modified]** Remove all backend FS/OCR/parser implementations. Since there is no file upload path, these services are no longer needed. The Edge Agent is the sole executor for all file processing.

### 3a. Delete Backend FS Implementations

**Delete files:**

| File | Reason |
|------|--------|
| `backend/core/infrastructure/services/file_scanner.py` | FS scanning -> edge agent |
| `backend/core/infrastructure/services/ocr_engine.py` | Local OCR -> edge agent |
| `backend/core/infrastructure/services/ocr_worker.py` | OCR subprocess -> edge agent |
| `backend/core/infrastructure/services/paddle_ocr_provider.py` | PaddleOCR -> edge agent |
| `backend/core/infrastructure/services/parser_router.py` | Local parsing -> edge agent |
| `backend/core/infrastructure/services/mineru_parser.py` | MinerU -> edge agent |
| `backend/core/infrastructure/services/document_reader.py` | Local file reading -> edge agent |

**[Added] Keep ABC interfaces:**

| File | Action |
|------|--------|
| `backend/core/application/interfaces/services.py` | **Keep** OCRProvider ABC (for future remote OCR / edge agent OCR provider) |
| `backend/core/application/interfaces/services.py` | **Remove** StorageBackend ABC (no file storage in SaaS) |
| `backend/core/application/interfaces/services.py` | **Remove** FileScanner ABC |

### 3b. Remove FS-Dependent Celery Tasks

**Modify:**
- `backend/core/infrastructure/messaging/celery_tasks.py`: Delete scan_folder_task. Keep process_document_task, generate_embedding_task, classify_document_task.
- `backend/apps/files/tasks.py`: Delete scan_folder_task. Keep delete_file_task.
- `backend/apps/ocr/tasks.py`: Delete process_image_task and process_pdf_task.

### 3c. Remove FS-Dependent API Endpoints

**Modify `backend/interfaces/api/v1/views/file_views.py`:**
- [Delete] scan() action
- [Delete] scan_stream() action
- [Delete] download() action (SaaS does not serve files)

### 3d. Update Application Interfaces

**Modify `backend/core/application/interfaces/services.py`:**
- [Delete] FileScanner ABC
- [Delete] StorageBackend ABC (no file storage in SaaS)
- [Keep] OCRProvider, LLMProvider, EmbeddingProvider ABCs

### 3e. Update FileService

**Modify `backend/core/application/services/file_service.py`:**
- [Delete] scan_folder() method
- [Keep] get_file, list_files, delete_file, rename_file, move_file, copy_file (metadata-only operations)

### 3f. Update DocumentProcessingPipeline

**Modify `backend/core/infrastructure/pipelines/document_pipeline.py`:**
- Single code path: use pre-existing text from Document (sent by edge agent)
- Remove `_read_content()`, `_run_ocr()`, `_needs_ocr()` methods
- Remove DocumentReader() and PaddleOCREngine() instantiation
- Pipeline only does: chunking, embeddings, LLM classification

---

## Phase 5: Frontend -- Agent Management Page

### 5a. New Agents Page

**[Added]** Replace /scan with /agents management page.

**New files:**
- `frontend/src/app/(dashboard)/agents/page.tsx` -- Agent management:
  - List all agents with status indicators
  - Show agent details: name, hostname, IP, platform, version, capabilities
  - Show monitored folders with file counts
  - Push commands to agents (scan, sync, process, config_update, shutdown)
  - Show command history
  - Agent registration instructions

### 5b. Update Sidebar

**Modify `frontend/src/components/layout/sidebar.tsx`:**
- Replace "Scan Folder" with "Agents" (icon: Bot)

### 5c. Delete Old Scan Page

**Delete:** `frontend/src/app/(dashboard)/scan/page.tsx`

### 5d. Update Files Page

**Modify `frontend/src/app/(dashboard)/files/page.tsx`:**
- Remove "Scan Folder" button
- Remove "Upload" button (no file uploads to SaaS)
- Show message: "Files are ingested via Edge Agents. [Set up an edge agent →](/agents)"
- List documents with metadata only (no file download links)

---

## Phase 6: Document Processing Versioning

**[Added]** Track all processing metadata for debugging, reprocessing, and migration.

**Modify `backend/apps/documents/models.py` -- add fields:**
- agent_version (CharField)
- processing_version (CharField)
- parser_version (CharField)
- ocr_engine (CharField)
- ocr_used (BooleanField)
- markdown (TextField)
- content_blocks (JSONField)
- tables (JSONField)
- images (JSONField)

**Modify `backend/apps/agents/models.py` -- add fields:**
- parser_version (CharField)
- ocr_engine (CharField)

**New migration:** `python manage.py makemigrations documents agents`

---

## Phase 7: Migration Strategy

**[Modified]** Since there is no file upload path, no feature flags are needed for backward compatibility. Services are deleted in Phase 3.

### 7a. Verify Edge Agent Coverage

Before deleting backend services, verify:
- All existing users have registered edge agents
- Edge agents are processing all file types correctly
- No users depend on the old scan/upload workflow

### 7b. Cleanup

- Remove any remaining references to StorageProvider in the SaaS
- Remove any file upload UI components
- Update documentation to reflect agent-only architecture

---

## Phase 8: Recommended Future Improvements

**[Added]** Schema-first contracts for drift prevention.

**Recommendation:** In future, generate shared types from OpenAPI/JSON Schema contracts:
- Python Pydantic models: `datamodel-codegen --input contract.yaml`
- TypeScript types: `openapi-typescript contract.yaml`

This prevents frontend/backend contract drift.

---

## File Change Summary

### New Files (~12)
| File | Purpose |
|------|---------|
| `packages/common-python/pyproject.toml` | Shared Python package config |
| `packages/common-python/common/__init__.py` | Package init |
| `packages/common-python/common/models.py` | Shared DTOs + event DTOs |
| `packages/common-python/common/constants.py` | Shared constants |
| `packages/common-python/common/validation.py` | Pydantic API schemas |
| `packages/common-python/common/config.py` | Shared config |
| `packages/common-python/common/utils.py` | Shared utilities |
| `packages/common-types/package.json` | Shared TS package config |
| `packages/common-types/src/*.ts` | Shared API types (8+ files) |
| `frontend/src/app/(dashboard)/agents/page.tsx` | Agent management page |

### Modified Files (~15)
| File | Change |
|------|--------|
| `backend/apps/agents/serializers.py` | Add pre-processed + versioning fields |
| `backend/apps/agents/views.py` | Update sync() for pre-processed data |
| `backend/apps/agents/models.py` | Add parser_version, ocr_engine fields |
| `backend/apps/documents/models.py` | Add markdown, content_blocks, tables, images, versioning fields |
| `backend/core/infrastructure/pipelines/document_pipeline.py` | Single path: use pre-existing text from edge agent |
| `backend/core/infrastructure/messaging/celery_tasks.py` | Remove scan_folder_task, keep LLM tasks |
| `backend/apps/files/tasks.py` | Remove scan_folder_task |
| `backend/core/application/interfaces/services.py` | Remove FileScanner, StorageBackend ABCs |
| `backend/core/application/services/file_service.py` | Remove scan_folder method |
| `backend/interfaces/api/v1/views/file_views.py` | Remove scan/scan_stream/download |
| `frontend/src/components/layout/sidebar.tsx` | Replace Scan with Agents link |
| `frontend/src/app/(dashboard)/files/page.tsx` | Remove upload UI, add edge agent guidance |
| `frontend/src/types/api.ts` | Re-export from @ai-archive/common-types |
| `frontend/package.json` | Add @ai-archive/common-types dependency |
| `edge_agent/sync/manager.py` | Send pre-processed + versioning data |
| `edge_agent/cli.py` | Collect all processing results, remove chunking |

### Deleted Files (~10)
| File | Reason |
|------|--------|
| `backend/core/infrastructure/services/file_scanner.py` | FS scanning -> edge agent |
| `backend/core/infrastructure/services/ocr_engine.py` | OCR -> edge agent |
| `backend/core/infrastructure/services/ocr_worker.py` | OCR subprocess -> edge agent |
| `backend/core/infrastructure/services/paddle_ocr_provider.py` | PaddleOCR -> edge agent |
| `backend/core/infrastructure/services/parser_router.py` | Parsing -> edge agent |
| `backend/core/infrastructure/services/mineru_parser.py` | MinerU -> edge agent |
| `backend/core/infrastructure/services/document_reader.py` | Reading -> edge agent |
| `backend/apps/ocr/tasks.py` | OCR tasks -> edge agent |
| `frontend/src/app/(dashboard)/scan/page.tsx` | Replaced by agents page |

---

## Execution Order

```
Phase 1: Shared Packages
Phase 2: Sync Protocol Enhancement (depends on Phase 1)
Phase 3: Remove Backend FS (depends on Phase 2)
Phase 3 (tests): Pipeline tests (depends on Phase 3)
Phase 5: Frontend Agents Page (can run parallel with 3)
Phase 6: Versioning (can run with Phase 2)
Phase 7: Migration & Cleanup (after all phases)
Phase 8: Future Improvements (recommended, not blocking)
```

**Critical path:** Phase 2 must complete before Phase 3. Phase 7 (cleanup) should only execute after edge agent is proven stable in production.

## Risk Mitigation

1. **Phase 2 is the critical bridge** -- sync protocol must be fully working before removing any backend FS services
2. **Edge agent adoption** -- Phase 7 cleanup should only proceed after all users have registered edge agents
3. **Test agent sync end-to-end** -- verify agent -> sync -> pipeline -> classification works before removing backend services
4. **Database migration** -- ensure Document model can store all pre-processed fields from agent
5. **Backward compatibility** -- existing agents using old sync format should still work (graceful degradation with defaults)
6. **No file storage** -- SaaS never stores or accesses original files; all processing is text-based

---

## Estimated Effort

| Phase | Hours | Dependencies |
|-------|-------|-------------|
| Phase 1: Shared Packages | 2-3h | None |
| Phase 2: Sync Protocol | 3-4h | Phase 1 |
| Phase 3: Remove Backend FS | 2-3h | Phase 2 |
| Phase 3 (tests): Pipeline tests | 1-2h | Phase 3 |
| Phase 5: Frontend | 2-3h | Phase 1 (types) |
| Phase 6: Versioning | 1-2h | Phase 2 |
| Phase 7: Migration & Cleanup | 1h | All phases |
| **Total** | **~12-18h** | |

**Note on Phase 3 tests**: The agent-synced pipeline (`document_pipeline.py`) is the riskiest part of the refactor. Tests should cover:
- Agent-synced file: pre-existing text used for chunking
- All chunking, embedding, and LLM classification paths
- FileSource string used correctly in pipeline logic
