# Comprehensive Test Plan — Backend + Edge Agent

## Goal

Test all backend and edge agent features. The backend has ~29 untested endpoints and 3 untested apps. The edge agent has 0 tests across 23 modules.

---

## Part 1: Backend Tests

### 1A. Agents App Tests (HIGH — completely untested)

**File:** `backend/tests/integration/test_api_agents.py`

**Fixtures needed (in `tests/integration/conftest.py`):**
- `sample_agent` — `Agent.objects.create(user=test_user, agent_id="test-agent-01", name="Test Agent", ...)`
- `sample_agent_folder` — `AgentFolder.objects.create(agent=sample_agent, local_path="/docs")`
- `sample_agent_command` — `AgentCommand.objects.create(agent=sample_agent, command_type="sync")`

**Test cases (~20):**

| Test | Endpoint | Asserts |
|------|----------|---------|
| `test_list_agents` | GET `/agents` | 200, returns list |
| `test_list_agents_unauthenticated` | GET `/agents` | 401 |
| `test_create_agent` | POST `/agents` | 201, returns agent + api_key |
| `test_create_agent_missing_fields` | POST `/agents` | 400 |
| `test_retrieve_agent` | GET `/agents/{agent_id}` | 200, correct fields |
| `test_retrieve_nonexistent_agent` | GET `/agents/{agent_id}` | 404 |
| `test_update_agent` | PUT `/agents/{agent_id}` | 200, fields updated |
| `test_delete_agent` | DELETE `/agents/{agent_id}` | 204 |
| `test_heartbeat` | POST `/agents/{agent_id}/heartbeat` | 200, returns pending_commands + config |
| `test_heartbeat_updates_status` | POST `/agents/{agent_id}/heartbeat` | Agent.status changed to "online" |
| `test_heartbeat_syncs_folders` | POST `/agents/{agent_id}/heartbeat` | AgentFolder created for new path |
| `test_commands_get` | GET `/agents/{agent_id}/commands` | 200, pending commands marked delivered |
| `test_commands_post_report_result` | POST `/agents/{agent_id}/commands` | 200, command status updated |
| `test_commands_post_not_found` | POST `/agents/{agent_id}/commands` | 404 |
| `test_create_command` | POST `/agents/{agent_id}/commands/create` | 201, command created |
| `test_create_command_missing_type` | POST `/agents/{agent_id}/commands/create` | 400 |
| `test_sync_single_file` | POST `/agents/{agent_id}/sync` | 200, accepted=1, Document created |
| `test_sync_multiple_files` | POST `/agents/{agent_id}/sync` | 200, accepted=N |
| `test_sync_with_entities` | POST `/agents/{agent_id}/sync` | ExtractedEntity records created |
| `test_sync_empty_files` | POST `/agents/{agent_id}/sync` | 200, accepted=0 |

### 1B. Pipeline Tests (HIGH — critical path)

**File:** `backend/tests/unit/pipelines/__init__.py` + `test_document_pipeline.py`

**Prerequisites:**
- Add `get_by_file_id()` method to `MockDocumentRepository` in `tests/mocks.py`

**Mocking strategy:**
- Use existing mock classes from `tests/mocks.py`
- Patch `asyncio.sleep` to avoid delays
- Patch `apps.documents.models.ExtractedEntity` for `_save_entities` (Django ORM)
- Set `max_retries=1, retry_base_delay=0` for speed

**Test cases (~10):**

| Test | What it verifies |
|------|-----------------|
| `test_process_happy_path` | Full pipeline: load file → create doc → classify → extract → summarize → chunk → embed → completed |
| `test_process_empty_text` | Document with no extracted_text → "other" classification, 0 chunks, still completes |
| `test_process_existing_document` | Pipeline reuses existing Document by file_id instead of creating new |
| `test_classify_returns_correct_type` | `_map_classification_to_type("contract")` → PDF, "email" → EMAIL |
| `test_chunk_text_basic` | `_chunk_text` splits 2500 chars into 3 chunks with overlap |
| `test_chunk_text_empty` | `_chunk_text("")` → `[]` |
| `test_chunk_text_natural_breaks` | Paragraph breaks preferred over mid-word splits |
| `test_embedding_failure_is_non_fatal` | Embedding provider raises → pipeline still completes, embedding_ids empty |
| `test_retry_schedules_retry` | LLM fails 3 times → document gets `schedule_retry()` |
| `test_process_logs_steps` | `result.processing_log` contains all 10 step entries |

### 1C. Reports App Tests (HIGH — completely untested)

**File:** `backend/tests/integration/test_api_reports.py`

**Fixtures needed:**
- `sample_report` — `Report.objects.create(report_type="archive_summary", title="Test Report", status="completed", generated_by=test_user, data={...})`

**Test cases (~10):**

| Test | Endpoint | Asserts |
|------|----------|---------|
| `test_list_reports` | GET `/reports` | 200, returns list |
| `test_list_reports_unauthenticated` | GET `/reports` | 401 |
| `test_create_report` | POST `/reports` | 201 |
| `test_retrieve_report` | GET `/reports/{id}` | 200 |
| `test_retrieve_nonexistent` | GET `/reports/{id}` | 404 |
| `test_delete_report` | DELETE `/reports/{id}` | 204 |
| `test_report_summary` | GET `/reports/summary` | 200, returns counts |
| `test_list_reports_by_type` | GET `/reports?report_type=archive_summary` | Filtered results |
| `test_list_reports_by_status` | GET `/reports?status=completed` | Filtered results |
| `test_report_model_str` | — | `str(report)` returns title |

### 1D. API Keys App Tests (HIGH — completely untested)

**File:** `backend/tests/integration/test_api_apikeys.py`

**Test cases (~10):**

| Test | Endpoint | Asserts |
|------|----------|---------|
| `test_list_keys` | GET `/api-keys` | 200, returns list |
| `test_list_keys_unauthenticated` | GET `/api-keys` | 401 |
| `test_create_key` | POST `/api-keys` | 201, returns raw key (ak_...) |
| `test_create_key_missing_name` | POST `/api-keys` | 400 |
| `test_retrieve_key` | GET `/api-keys/{id}` | 200 (no raw key in response) |
| `test_delete_key` | DELETE `/api-keys/{id}` | 204 |
| `test_delete_nonexistent_key` | DELETE `/api-keys/{id}` | 404 |
| `test_toggle_active` | POST `/api-keys/{id}/toggle-active` | 200, is_active flipped |
| `test_toggle_active_nonexistent` | POST `/api-keys/{id}/toggle-active` | 404 |
| `test_verify_key_valid` | — (model method) | Returns ApiKey |
| `test_verify_key_invalid` | — (model method) | Returns None |

### 1E. Missing Document Endpoint Tests (MEDIUM)

**File:** Add to `backend/tests/integration/test_api_documents.py`

**Test cases (~6):**

| Test | Endpoint | Asserts |
|------|----------|---------|
| `test_update_document` | PATCH `/documents/{id}` | 200, fields updated |
| `test_update_document_partial` | PATCH `/documents/{id}` (only title) | 200, tags unchanged |
| `test_update_nonexistent` | PATCH `/documents/{id}` | 404 |
| `test_delete_document` | DELETE `/documents/{id}` | 204 |
| `test_delete_nonexistent` | DELETE `/documents/{id}` | 404 |
| `test_list_entities` | GET `/documents/{id}/entities` | 200, returns entity list |

### 1F. Missing Search Endpoint Tests (MEDIUM)

**File:** Add to `backend/tests/integration/test_api_search.py`

**Test cases (~8):**

| Test | Endpoint | Asserts |
|------|----------|---------|
| `test_search_history` | GET `/search/history` | 200, returns list |
| `test_search_history_unauthenticated` | GET `/search/history` | 401 |
| `test_search_history_with_limit` | GET `/search/history?limit=5` | Respects limit |
| `test_saved_search_list` | GET `/search/saved` | 200, returns list |
| `test_saved_search_create` | POST `/search/saved` | 201 |
| `test_saved_search_create_missing_fields` | POST `/search/saved` | 400 |
| `test_saved_search_delete` | DELETE `/search/saved` | 204 |
| `test_saved_search_delete_nonexistent` | DELETE `/search/saved` | 404 |

---

## Part 2: Edge Agent Tests

**Location:** `edge_agent/tests/` (new directory)

**Setup:** `edge_agent/pyproject.toml` already has pytest + pytest-asyncio configured.

### 2A. Config Tests

**File:** `edge_agent/tests/test_config.py`

**Test cases (~8):**

| Test | What it verifies |
|------|-----------------|
| `test_load_default_config` | `load_config()` returns defaults when no file exists |
| `test_load_from_yaml` | Creates temp YAML, loads it, verifies values |
| `test_env_overrides` | Sets `EDGE_SERVER_URL` env var, verifies override |
| `test_db_path_property` | `config.db_path` returns `{data_dir}/agent.db` |
| `test_log_file_property` | `config.log_file` returns `{data_dir}/agent.log` |
| `test_sync_config_defaults` | `SyncConfig()` has correct defaults |
| `test_ocr_config_defaults` | `OCRConfig()` has correct defaults |
| `test_load_minimal_yaml` | YAML with only `server.url` set, rest defaults |

### 2B. Core Models Tests

**File:** `edge_agent/tests/test_models.py`

**Test cases (~12):**

| Test | What it verifies |
|------|-----------------|
| `test_language_enum_members` | All 19 Language values exist |
| `test_confidence_valid` | `Confidence(0.5)` works |
| `test_confidence_invalid_low` | `Confidence(-0.1)` raises ValueError |
| `test_confidence_invalid_high` | `Confidence(1.1)` raises ValueError |
| `test_confidence_properties` | `is_high`, `is_medium`, `is_low`, `percentage` |
| `test_content_block_creation` | `ContentBlock(block_type="heading", content="Title")` |
| `test_parsed_table_creation` | `ParsedTable(html=..., rows=..., headers=...)` |
| `test_parsed_image_creation` | `ParsedImage(image_path=..., description=...)` |
| `test_parsed_document_has_tables` | `has_tables` property |
| `test_parsed_document_has_images` | `has_images` property |
| `test_extraction_result_auto_counts` | `word_count` and `char_count` auto-computed from text |
| `test_extraction_result_empty` | Empty text → 0 counts |

### 2C. Scanner Tests

**File:** `edge_agent/tests/test_scanner.py`

**Test cases (~10):**

| Test | What it verifies |
|------|-----------------|
| `test_compute_fingerprint` | SHA-256 hash, magic bytes, MIME type for a known file |
| `test_scan_single_file` | Returns dict with all required fields |
| `test_scan_single_missing_file` | Returns None for non-existent path |
| `test_scan_single_too_large` | Returns None when > max_file_size_mb |
| `test_scan_single_empty_file` | Returns None for 0-byte file |
| `test_scan_folder_recursive` | Finds files in subdirectories |
| `test_scan_folder_ignore_patterns` | `.git`, `__pycache__` files excluded |
| `test_scan_folder_custom_patterns` | Custom ignore patterns respected |
| `test_scan_folder_empty_dir` | Empty directory → no results |
| `test_scan_symlink` | Symlinks handled correctly |

### 2D. Local DB Tests

**File:** `edge_agent/tests/test_local_db.py`

**Test cases (~15):**

| Test | What it verifies |
|------|-----------------|
| `test_schema_creation` | DB file created, tables exist |
| `test_upsert_file_new` | New file inserted, returns UUID |
| `test_upsert_file_existing` | Same content_hash → updates, same ID |
| `test_update_file_fields` | Updates specific fields (extracted_text, status) |
| `test_get_file` | Returns dict with all fields |
| `test_get_file_by_hash` | Lookup by content_hash |
| `test_get_file_by_path` | Lookup by local_path |
| `test_list_files_all` | Returns all files |
| `test_list_files_by_status` | Filter by processing_status |
| `test_list_files_pending_sync` | Filter by synced=0 |
| `test_get_pending_sync_batch` | Returns correct batch size |
| `test_mark_synced` | Sets synced=1 + synced_at |
| `test_get_stats` | Returns total/synced/pending/completed/failed counts |
| `test_delete_file` | Removes file + associated entities |
| `test_save_and_get_entities` | Round-trip entity storage |
| `test_get_entity_stats` | Counts grouped by entity_type |

### 2E. Chunker Tests

**File:** `edge_agent/tests/test_chunker.py`

**Test cases (~6):**

| Test | What it verifies |
|------|-----------------|
| `test_chunk_text_basic` | 2500 chars → multiple chunks with overlap |
| `test_chunk_text_empty` | Empty string → `[]` |
| `test_chunk_text_short` | Text < chunk_size → single chunk |
| `test_chunk_text_natural_breaks` | Prefers `\n\n` > `. ` > ` ` boundaries |
| `test_chunk_size_min` | Returns max(30% of total, 100) |
| `test_chunk_offsets` | start_char/end_char are correct |

### 2F. LLM Client Tests (mocked HTTP)

**File:** `edge_agent/tests/test_llm_client.py`

**Test cases (~10):**

| Test | What it verifies |
|------|-----------------|
| `test_extract_entities_openai` | Mocks httpx, parses OpenAI response format |
| `test_extract_entities_anthropic` | Mocks httpx, parses Anthropic response format |
| `test_extract_entities_ollama` | Mocks httpx, parses Ollama response format |
| `test_parse_entities_json_array` | Direct JSON array parsing |
| `test_parse_entities_wrapped` | `{"entities": [...]}` wrapper parsing |
| `test_parse_entities_regex_fallback` | Regex extraction when JSON fails |
| `test_entity_type_mapping` | "org" → "organization", "person" → "person" |
| `test_text_truncation` | Text > 8000 chars truncated |
| `test_llm_error_handling` | HTTP 500 → returns empty list |
| `test_invalid_json_response` | Garbage response → returns empty list |

### 2G. Sync Manager Tests (mocked HTTP)

**File:** `edge_agent/tests/test_sync_manager.py`

**Test cases (~8):**

| Test | What it verifies |
|------|-----------------|
| `test_register_success` | POST to /agents, returns agent data |
| `test_register_requires_jwt` | No jwt_token → raises ValueError |
| `test_heartbeat` | POST to /agents/{id}/heartbeat, returns pending_commands |
| `test_sync_files` | POST to /agents/{id}/sync, marks files synced |
| `test_sync_empty_batch` | No pending files → returns {"synced": 0} |
| `test_sync_with_retry_success` | First attempt fails, second succeeds |
| `test_sync_with_retry_exhausted` | All attempts fail → raises RuntimeError |
| `test_report_command_result` | POST to /agents/{id}/commands |

### 2H. CLI Tests

**File:** `edge_agent/tests/test_cli.py`

**Test cases (~10):**

| Test | What it verifies |
|------|-----------------|
| `test_build_parser_register` | Parses `register --jwt TOKEN --name agent1` |
| `test_build_parser_scan` | Parses `scan /path --no-recursive` |
| `test_build_parser_run` | Parses `run --folders /a /b` |
| `test_dispatch_scan_command` | `_execute_scan` scans folders |
| `test_dispatch_sync_command` | `_execute_sync` calls sync |
| `test_dispatch_process_command` | `_execute_process` processes file |
| `test_dispatch_config_update` | `_execute_config_update` updates config |
| `test_dispatch_shutdown` | `_execute_shutdown` returns shutting_down |
| `test_dispatch_unknown_command` | Unknown type → error dict |
| `test_save_config_roundtrip` | `_save_config` → `load_config` preserves values |

### 2I. Document Reader Tests (with temp files)

**File:** `edge_agent/tests/test_document_reader.py`

**Test cases (~8):**

| Test | What it verifies |
|------|-----------------|
| `test_read_text_file` | Reads .txt, returns ExtractionResult |
| `test_read_csv_file` | Reads .csv, returns text |
| `test_read_json_file` | Reads .json, returns text |
| `test_read_pdf_file` | Reads .pdf (if pdfplumber available) |
| `test_read_docx_file` | Reads .docx (if python-docx available) |
| `test_read_image_metadata` | Reads image dimensions (if Pillow available) |
| `test_read_unsupported_format` | Returns fallback result |
| `test_read_empty_file` | Returns empty ExtractionResult |

### 2J. OCR Engine Tests (mocked)

**File:** `edge_agent/tests/test_ocr_engine.py`

**Test cases (~6):**

| Test | What it verifies |
|------|-----------------|
| `test_detect_language_arabic` | Arabic Unicode → Language.AR |
| `test_detect_language_english` | English text → Language.EN |
| `test_detect_language_mixed` | Mixed text → dominant language |
| `test_get_confidence_high` | Clean text → high confidence |
| `test_get_confidence_low` | Gibberish → low confidence |
| `test_extract_text_no_engines` | No PaddleOCR/Tesseract → returns "" |

### 2K. Watcher Tests (mocked watchdog)

**File:** `edge_agent/tests/test_watcher.py`

**Test cases (~6):**

| Test | What it verifies |
|------|-----------------|
| `test_watch_starts_observer` | `is_watching(path)` returns True |
| `test_stop_single_path` | `stop(path)` → `is_watching` False |
| `test_stop_all` | `stop_all()` → all paths stopped |
| `test_watched_paths_property` | Returns list of watched paths |
| `test_debounce_suppresses` | Rapid events → single callback |
| `test_no_watchdog_graceful` | Import error → logs warning, doesn't crash |

---

## Execution Order

### Round 1: Backend (parallel with edge agent)
1. Add fixtures to `tests/integration/conftest.py` (agents, reports, apikeys, saved_search)
2. Add `get_by_file_id()` to `MockDocumentRepository`
3. Create `test_api_agents.py` (20 tests)
4. Create `test_api_reports.py` (10 tests)
5. Create `test_api_apikeys.py` (10 tests)
6. Add document PATCH/DELETE/entities tests (6 tests)
7. Add search history/saved tests (8 tests)
8. Create `test_document_pipeline.py` (10 tests)

### Round 2: Edge Agent (parallel with backend)
1. Create `edge_agent/tests/` directory + `conftest.py`
2. Create `test_config.py` (8 tests)
3. Create `test_models.py` (12 tests)
4. Create `test_scanner.py` (10 tests)
5. Create `test_local_db.py` (15 tests)
6. Create `test_chunker.py` (6 tests)
7. Create `test_llm_client.py` (10 tests)
8. Create `test_sync_manager.py` (8 tests)
9. Create `test_cli.py` (10 tests)
10. Create `test_document_reader.py` (8 tests)
11. Create `test_ocr_engine.py` (6 tests)
12. Create `test_watcher.py` (6 tests)

### Round 3: Verify
1. `cd backend && python -m pytest -v`
2. `cd edge_agent && python -m pytest -v`

---

## Total: ~200 test cases

| Area | Tests |
|------|-------|
| Backend: Agents | 20 |
| Backend: Pipeline | 10 |
| Backend: Reports | 10 |
| Backend: API Keys | 10 |
| Backend: Documents (missing) | 6 |
| Backend: Search (missing) | 8 |
| Edge Agent: Config | 8 |
| Edge Agent: Models | 12 |
| Edge Agent: Scanner | 10 |
| Edge Agent: Local DB | 15 |
| Edge Agent: Chunker | 6 |
| Edge Agent: LLM Client | 10 |
| Edge Agent: Sync Manager | 8 |
| Edge Agent: CLI | 10 |
| Edge Agent: Document Reader | 8 |
| Edge Agent: OCR Engine | 6 |
| Edge Agent: Watcher | 6 |
| **Total** | **~163** |

## Files to Create/Modify

### New files (backend):
- `backend/tests/integration/test_api_agents.py`
- `backend/tests/integration/test_api_reports.py`
- `backend/tests/integration/test_api_apikeys.py`
- `backend/tests/unit/pipelines/__init__.py`
- `backend/tests/unit/pipelines/test_document_pipeline.py`

### New files (edge agent):
- `edge_agent/tests/__init__.py`
- `edge_agent/tests/conftest.py`
- `edge_agent/tests/test_config.py`
- `edge_agent/tests/test_models.py`
- `edge_agent/tests/test_scanner.py`
- `edge_agent/tests/test_local_db.py`
- `edge_agent/tests/test_chunker.py`
- `edge_agent/tests/test_llm_client.py`
- `edge_agent/tests/test_sync_manager.py`
- `edge_agent/tests/test_cli.py`
- `edge_agent/tests/test_document_reader.py`
- `edge_agent/tests/test_ocr_engine.py`
- `edge_agent/tests/test_watcher.py`

### Modified files:
- `backend/tests/integration/conftest.py` — add agent/report/apikey/saved_search fixtures
- `backend/tests/mocks.py` — add `get_by_file_id()` to `MockDocumentRepository`
- `backend/tests/integration/test_api_documents.py` — add PATCH/DELETE/entities tests
- `backend/tests/integration/test_api_search.py` — add history/saved tests
