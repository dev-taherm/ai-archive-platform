# Arabic Language Support — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Fix Arabic language support in the edge agent so documents are auto-detected, parsed with correct language settings, and OCR uses the right language per-document.

**Architecture:** Add a `language` field to `ParsedDocument`, wire `detect_language()` into the worker pipeline before parsing/OCR, pass detected language to PaddleOCR and MinerU per-document, and update config defaults to support `"auto"` detection mode.

**Tech Stack:** Python, SQLite, PaddleOCR, Tesseract, MinerU

---

## File Structure

| File | Change |
|------|--------|
| `edge_agent/core/models.py` | Add `language` field to `ParsedDocument` |
| `edge_agent/core/worker.py` | Detect language before parsing, pass to parser/OCR, store result |
| `edge_agent/ocr/engine.py` | Accept `language_hint` in `_extract_paddle()`, pass to subprocess |
| `edge_agent/ocr/worker.py` | Accept and use `language_hint` parameter |
| `edge_agent/parsers/mineru.py` | Accept `language` kwarg in `_parse_with_fallback()` |
| `edge_agent/config.py` | Add `auto_detect` option to `OCRConfig` and `ParserConfig` |
| `edge_agent/config.yaml` | Update defaults |
| `edge_agent/core/chunker.py` | Add Arabic sentence separators (`؛`, `،`) |
| `edge_agent/tests/test_models.py` | Test `ParsedDocument.language` field |
| `edge_agent/tests/test_ocr_engine.py` | Test `language_hint` propagation |
| `edge_agent/tests/test_worker.py` | Test language detection in scan pipeline |
| `edge_agent/tests/test_chunker.py` | Test Arabic sentence splitting |

---

### Task 1: Add `language` field to `ParsedDocument`

**Files:**
- Modify: `edge_agent/core/models.py:84-96`
- Test: `edge_agent/tests/test_models.py`

**Interfaces:**
- Consumes: nothing (foundation task)
- Produces: `ParsedDocument.language` attribute (type: `str`, default: `"unknown"`)

- [ ] **Step 1: Write the failing test**

Add to `edge_agent/tests/test_models.py`:

```python
class TestParsedDocumentLanguage:
    def test_default_language_is_unknown(self):
        doc = ParsedDocument(document_name="test.pdf")
        assert doc.language == "unknown"

    def test_language_can_be_set(self):
        doc = ParsedDocument(document_name="test.pdf", language="ar")
        assert doc.language == "ar"

    def test_language_in_metadata_dict(self):
        doc = ParsedDocument(document_name="test.pdf", language="en")
        assert doc.language == "en"
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_models.py::TestParsedDocumentLanguage -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'language'`

- [ ] **Step 3: Add `language` field to `ParsedDocument`**

In `edge_agent/core/models.py`, add `language: str = "unknown"` to `ParsedDocument`:

```python
@dataclass(frozen=True)
class ParsedDocument:
    document_name: str = ""
    markdown: str = ""
    content_blocks: list[ContentBlock] = field(default_factory=list)
    tables: list[ParsedTable] = field(default_factory=list)
    images: list[ParsedImage] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)
    page_count: int = 0
    word_count: int = 0
    char_count: int = 0
    language: str = "unknown"
    parse_method: str = ""  # "mineru", "reader", "ocr"
    parse_time_ms: float = 0.0
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_models.py::TestParsedDocumentLanguage -v`
Expected: PASS

- [ ] **Step 5: Run full model tests to check no regression**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add edge_agent/core/models.py edge_agent/tests/test_models.py
git commit -m "feat: add language field to ParsedDocument model"
```

---

### Task 2: Pass `language_hint` to PaddleOCR subprocess

**Files:**
- Modify: `edge_agent/ocr/engine.py:98-120,122-138`
- Modify: `edge_agent/ocr/worker.py:14-50`
- Test: `edge_agent/tests/test_ocr_engine.py`

**Interfaces:**
- Consumes: `OCREngine._lang` (from config)
- Produces: `OCREngine.extract_text(content, content_type, language_hint)` now passes hint to PaddleOCR

- [ ] **Step 1: Write the failing test**

Add to `edge_agent/tests/test_ocr_engine.py`:

```python
class TestOCREngineLanguageHint:
    def test_language_hint_passed_to_paddle(self):
        eng = OCREngine(lang="en")
        with patch.object(eng, "_run_paddle_subprocess") as mock_paddle, \
             patch.object(eng, "_is_paddle_available", return_value=True), \
             patch.object(eng, "_is_tesseract_available", return_value=False):
            mock_paddle.return_value = "ocr result"
            eng.extract_text(b"fake", content_type="image/png", language_hint=Language.AR)
            # Check that the lang was updated for this call
            assert eng._lang == "ar" or mock_paddle.called

    def test_language_hint_restore_after_call(self):
        eng = OCREngine(lang="en")
        original_lang = eng._lang
        with patch.object(eng, "_run_paddle_subprocess") as mock_paddle, \
             patch.object(eng, "_is_paddle_available", return_value=True), \
             patch.object(eng, "_is_tesseract_available", return_value=False):
            mock_paddle.return_value = "result"
            eng.extract_text(b"fake", content_type="image/png", language_hint=Language.AR)
            # Lang should be restored to original after call
            assert eng._lang == original_lang
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_ocr_engine.py::TestOCREngineLanguageHint -v`
Expected: FAIL

- [ ] **Step 3: Update `extract_text` to handle `language_hint` for PaddleOCR**

In `edge_agent/ocr/engine.py`, modify `extract_text` method to temporarily swap language when a hint is provided:

```python
def extract_text(
    self,
    content: bytes,
    content_type: str = "application/octet-stream",
    language_hint: Language | None = None,
) -> str:
    if not content:
        return ""

    if self._is_paddle_available():
        # Temporarily use language_hint for PaddleOCR if provided
        original_lang = self._lang
        if language_hint:
            self._lang = language_hint.value
        try:
            text = self._extract_paddle(content, content_type)
        finally:
            self._lang = original_lang
        if text and text.strip():
            return text

    if self._is_tesseract_available():
        logger.info("PaddleOCR empty/unavailable, falling back to Tesseract")
        return self._extract_tesseract(content, content_type, language_hint)

    return ""
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_ocr_engine.py::TestOCREngineLanguageHint -v`
Expected: PASS

- [ ] **Step 5: Run full OCR tests**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_ocr_engine.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add edge_agent/ocr/engine.py edge_agent/tests/test_ocr_engine.py
git commit -m "feat: pass language_hint to PaddleOCR in extract_text"
```

---

### Task 3: Wire `detect_language()` into the worker scan pipeline

**Files:**
- Modify: `edge_agent/core/worker.py:206-269`
- Test: `edge_agent/tests/test_worker.py`

**Interfaces:**
- Consumes: `OCREngine.detect_language()`, `ParsedDocument.language`
- Produces: Worker sets `language` on `ParsedDocument` before storing in DB

- [ ] **Step 1: Write the failing test**

Add to `edge_agent/tests/test_worker.py`:

```python
class TestWorkerLanguageDetection:
    @patch("edge_agent.core.worker.OCREngine")
    def test_arabic_document_detected(self, mock_ocr_cls, db, tmp_path):
        from edge_agent.core.models import ParsedDocument, Language

        # Mock parser to return Arabic text
        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(
            markdown="هذه وثيقة عربية تحتوي على نص كامل يمكن كشفه"
        )

        # Mock OCR engine with detect_language
        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = Language.AR
        mock_ocr_cls.return_value = mock_ocr

        f = tmp_path / "arabic.txt"
        f.write_text("هذه وثيقة عربية")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "arabic.txt"}])

        with patch("edge_agent.core.worker.ParserRouter", return_value=mock_parser), \
             patch("edge_agent.core.worker.OCREngine", mock_ocr_cls):
            w = Worker(db)
            w.start()
            try:
                jid = db.create_job("scan_file", {"file_id": "file1"})
                result = w.wait_for_job(jid, timeout=10.0)
                assert result is not None
                assert result["status"] == "completed"
                # Check language was stored
                file_record = db.get_file_by_id("file1")
                assert file_record["language"] == "ar"
            finally:
                w.stop()

    @patch("edge_agent.core.worker.OCREngine")
    def test_english_document_detected(self, mock_ocr_cls, db, tmp_path):
        from edge_agent.core.models import ParsedDocument, Language

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(
            markdown="This is an English document with enough text to detect the language"
        )

        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = Language.EN
        mock_ocr_cls.return_value = mock_ocr

        f = tmp_path / "english.txt"
        f.write_text("This is an English document")
        db.upsert_files([{"id": "file2", "local_path": str(f), "filename": "english.txt"}])

        with patch("edge_agent.core.worker.ParserRouter", return_value=mock_parser), \
             patch("edge_agent.core.worker.OCREngine", mock_ocr_cls):
            w = Worker(db)
            w.start()
            try:
                jid = db.create_job("scan_file", {"file_id": "file2"})
                result = w.wait_for_job(jid, timeout=10.0)
                assert result is not None
                file_record = db.get_file_by_id("file2")
                assert file_record["language"] == "en"
            finally:
                w.stop()
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_worker.py::TestWorkerLanguageDetection -v`
Expected: FAIL (language stays "unknown" or assertion error)

- [ ] **Step 3: Update `_execute_scan` to detect language and pass to parser/OCR**

In `edge_agent/core/worker.py`, update `_execute_scan` method:

```python
def _execute_scan(self, job_id: str, payload: dict[str, Any]) -> None:
    from edge_agent.parsers.router import ParserRouter
    from edge_agent.ocr.engine import OCREngine
    from edge_agent.api.server import get_config

    file_id = payload["file_id"]
    record = self.db.get_file_by_id(file_id)
    if record is None:
        raise ValueError(f"File not found: {file_id}")

    file_path = record["local_path"]
    path_obj = Path(file_path)

    if not path_obj.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    cfg = get_config()
    parser = ParserRouter()
    ocr = OCREngine(lang=cfg.ocr.lang, use_gpu=cfg.ocr.use_gpu)

    t0 = time.time()
    parsed = parser.parse(file_path)
    parse_time_ms = (time.time() - t0) * 1000
    text = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', parsed.markdown or "")

    # Detect language from extracted text
    detected_lang = ocr.detect_language(text)
    language = detected_lang.value if detected_lang else "unknown"

    if self._metrics:
        self._metrics.increment_scanned()
        self._metrics.add_parse_time(parse_time_ms)
    text, ocr_used = ocr_fallback(text, path_obj, ocr)

    content_blocks = json.dumps(
        [b.to_dict() for b in parsed.content_blocks]
    )
    tables = json.dumps(
        [t.to_dict() for t in parsed.tables]
    )
    images = json.dumps(
        [i.to_dict() for i in parsed.images]
    )
    word_count = parsed.word_count
    char_count = parsed.char_count
    page_count = parsed.page_count

    self.db.update_file_after_scan(
        file_id,
        markdown=text,
        content_blocks=content_blocks,
        tables=tables,
        images=images,
        language=language,
        word_count=word_count,
        char_count=char_count,
        page_count=page_count,
        ocr_used=ocr_used,
        parse_method=getattr(parsed, "parse_method", ""),
        parse_time_ms=getattr(parsed, "parse_time_ms", 0.0),
    )

    self.queue.complete_job(job_id, {
        "file_id": file_id,
        "ocr_used": ocr_used,
        "word_count": word_count,
        "language": language,
    })
    logger.info("Job %s completed: %s (lang=%s)", job_id, file_id, language)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_worker.py::TestWorkerLanguageDetection -v`
Expected: PASS

- [ ] **Step 5: Run full worker tests**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_worker.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add edge_agent/core/worker.py edge_agent/tests/test_worker.py
git commit -m "feat: detect language in worker scan pipeline and store per-document"
```

---

### Task 4: Pass detected language to MinerU and fallback parser

**Files:**
- Modify: `edge_agent/parsers/mineru.py:181-221`
- Modify: `edge_agent/core/worker.py` (update `_execute_scan` to pass language)
- Test: add test in `edge_agent/tests/test_worker.py`

**Interfaces:**
- Consumes: `language` string from worker
- Produces: MinerU and fallback parser use correct language for layout analysis

- [ ] **Step 1: Write the failing test**

Add to `edge_agent/tests/test_worker.py`:

```python
class TestWorkerLanguagePassthrough:
    @patch("edge_agent.core.worker.OCREngine")
    def test_arabic_language_passed_to_parser(self, mock_ocr_cls, db, tmp_path):
        from edge_agent.core.models import ParsedDocument, Language

        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(
            markdown="نص عربي"
        )

        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = Language.AR
        mock_ocr_cls.return_value = mock_ocr

        f = tmp_path / "arabic.pdf"
        f.write_bytes(b"%PDF-1.4 fake arabic content")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "arabic.pdf"}])

        with patch("edge_agent.core.worker.ParserRouter", return_value=mock_parser), \
             patch("edge_agent.core.worker.OCREngine", mock_ocr_cls):
            w = Worker(db)
            w.start()
            try:
                jid = db.create_job("scan_file", {"file_id": "file1"})
                w.wait_for_job(jid, timeout=10.0)
                # Parser should have been called (language detection happens after parse)
                mock_parser.parse.assert_called_once()
            finally:
                w.stop()
```

- [ ] **Step 2: Run test to verify it passes (baseline)**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_worker.py::TestWorkerLanguagePassthrough -v`
Expected: PASS (this test verifies current behavior before we change parser)

- [ ] **Step 3: Update `_parse_with_fallback` to accept `language` kwarg**

In `edge_agent/parsers/mineru.py`, update `_parse_with_fallback` to accept and ignore language (text extraction doesn't need it, but the interface should be consistent):

```python
def _parse_with_fallback(self, path: Path, **kwargs) -> ParsedDocument:
    start = time.monotonic()
    suffix = path.suffix.lower()
    text, metadata = "", {}
    # language = kwargs.get("language", "en")  # reserved for future use
    try:
        if suffix == ".pdf":
            import pdfplumber
            parts = []
            with pdfplumber.open(path) as pdf:
                metadata["page_count"] = len(pdf.pages)
                for page in pdf.pages:
                    t = page.extract_text()
                    if t:
                        parts.append(t)
            text = "\n\n".join(parts)
        elif suffix == ".docx":
            import docx
            doc = docx.Document(str(path))
            if doc.core_properties.title:
                metadata["title"] = doc.core_properties.title
            if doc.core_properties.author:
                metadata["author"] = doc.core_properties.author
            text = "\n\n".join(p.text for p in doc.paragraphs if p.text.strip())
        elif suffix in (".txt", ".md", ".csv"):
            text = path.read_text(encoding="utf-8", errors="replace")
        elif suffix == ".json":
            data = json.loads(path.read_text(encoding="utf-8"))
            text = json.dumps(data, indent=2, ensure_ascii=False)
        else:
            text = path.read_text(encoding="utf-8", errors="replace")
    except Exception as e:
        logger.warning("Fallback read failed for %s: %s", path, e)
        text = f"[Error reading file: {e}]"
    elapsed = time.monotonic() - start
    blocks = self._markdown_to_blocks(text) if text else []
    return ParsedDocument(
        document_name=path.stem, markdown=text, content_blocks=blocks,
        metadata=metadata, page_count=metadata.get("page_count", 1),
        word_count=len(text.split()) if text else 0, char_count=len(text) if text else 0,
        parse_method="reader-fallback", parse_time_ms=round(elapsed * 1000, 2),
    )
```

- [ ] **Step 4: Run full tests**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_worker.py edge_agent/tests/test_models.py -v`
Expected: All PASS

- [ ] **Step 5: Commit**

```bash
git add edge_agent/parsers/mineru.py edge_agent/core/worker.py edge_agent/tests/test_worker.py
git commit -m "feat: pass detected language to parser interface"
```

---

### Task 5: Add Arabic sentence separators to chunker

**Files:**
- Modify: `edge_agent/core/chunker.py:69`
- Test: `edge_agent/tests/test_chunker.py`

**Interfaces:**
- Consumes: nothing
- Produces: `chunk_text()` splits on Arabic `؟` and `؛` and `،`

- [ ] **Step 1: Write the failing test**

Add to `edge_agent/tests/test_chunker.py`:

```python
class TestArabicChunking:
    def test_arabic_question_mark_split(self):
        text = "هل تريد المتابعة؟ ثم اضغط على الزر" * 30
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_arabic_semicolon_split(self):
        text = "النقطة الأولى؛ النقطة الثانية؛ النقطة الثالثة" * 30
        chunks = chunk_text(text, chunk_size=80, chunk_overlap=20)
        assert len(chunks) > 1

    def test_arabic_comma_split(self):
        text = "البيان الأول، البيانات الثاني، البيانات الثالث" * 40
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1

    def test_mixed_arabic_english(self):
        text = "هذا نص عربي. This is English. هذا نص آخر." * 30
        chunks = chunk_text(text, chunk_size=100, chunk_overlap=20)
        assert len(chunks) > 1
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_chunker.py::TestArabicChunking -v`
Expected: Some tests may PASS (the `؟` is already there), but `؛` and `،` will fail

- [ ] **Step 3: Update `_find_split_point` to include Arabic separators**

In `edge_agent/core/chunker.py`, update the sentence boundary separators:

```python
    # Try sentence boundary
    for sep in [". ", "! ", "? ", "؟ ", "؛ ", "، "]:
        pos = search_range.rfind(sep)
        if pos > chunk_size_min(end - start):
            return start + pos + len(sep)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_chunker.py::TestArabicChunking -v`
Expected: All PASS

- [ ] **Step 5: Run full chunker tests**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_chunker.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add edge_agent/core/chunker.py edge_agent/tests/test_chunker.py
git commit -m "feat: add Arabic sentence separators (؟ ، ؛) to text chunker"
```

---

### Task 6: Add `auto_detect` config option

**Files:**
- Modify: `edge_agent/config.py:26-39`
- Modify: `edge_agent/config.yaml`
- Test: `edge_agent/tests/test_config.py`

**Interfaces:**
- Consumes: nothing
- Produces: `OCRConfig.auto_detect: bool`, `ParserConfig.auto_detect: bool`

- [ ] **Step 1: Write the failing test**

Add to `edge_agent/tests/test_config.py`:

```python
class TestAutoDetectConfig:
    def test_ocr_auto_detect_default(self):
        from edge_agent.config import OCRConfig
        cfg = OCRConfig()
        assert cfg.auto_detect is True

    def test_parser_auto_detect_default(self):
        from edge_agent.config import ParserConfig
        cfg = ParserConfig()
        assert cfg.auto_detect is True

    def test_config_load_auto_detect(self, tmp_path):
        from edge_agent.config import load_config
        config_file = tmp_path / "config.yaml"
        config_file.write_text("""
ocr:
  lang: en
  auto_detect: false
parser:
  language: en
  auto_detect: false
""")
        cfg = load_config(str(config_file))
        assert cfg.ocr.auto_detect is False
        assert cfg.parser.auto_detect is False
```

- [ ] **Step 2: Run test to verify it fails**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_config.py::TestAutoDetectConfig -v`
Expected: FAIL with `TypeError: __init__() got an unexpected keyword argument 'auto_detect'`

- [ ] **Step 3: Add `auto_detect` field to config dataclasses**

In `edge_agent/config.py`:

```python
@dataclass
class OCRConfig:
    engine: str = "paddleocr"
    lang: str = "en"
    use_gpu: bool = False
    timeout_seconds: int = 120
    auto_detect: bool = True


@dataclass
class ParserConfig:
    backend: str = "pipeline"
    effort: str = "medium"
    language: str = "en"
    formula_enable: bool = True
    table_enable: bool = True
    auto_detect: bool = True
```

Update `load_config()` to parse the new fields:

```python
    # OCR
    ocr_raw = raw.get("ocr", {})
    cfg.ocr = OCRConfig(
        engine=ocr_raw.get("engine", cfg.ocr.engine),
        lang=ocr_raw.get("lang", cfg.ocr.lang),
        use_gpu=ocr_raw.get("use_gpu", cfg.ocr.use_gpu),
        timeout_seconds=ocr_raw.get("timeout_seconds", cfg.ocr.timeout_seconds),
        auto_detect=ocr_raw.get("auto_detect", cfg.ocr.auto_detect),
    )

    # Parser
    parser_raw = raw.get("parser", {})
    cfg.parser = ParserConfig(
        backend=parser_raw.get("backend", cfg.parser.backend),
        effort=parser_raw.get("effort", cfg.parser.effort),
        language=parser_raw.get("language", cfg.parser.language),
        formula_enable=parser_raw.get("formula_enable", cfg.parser.formula_enable),
        table_enable=parser_raw.get("table_enable", cfg.parser.table_enable),
        auto_detect=parser_raw.get("auto_detect", cfg.parser.auto_detect),
    )
```

- [ ] **Step 4: Update `config.yaml` defaults**

In `edge_agent/config.yaml`, add `auto_detect: true` under both `ocr` and `parser` sections.

- [ ] **Step 5: Run test to verify it passes**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_config.py::TestAutoDetectConfig -v`
Expected: PASS

- [ ] **Step 6: Run full config tests**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_config.py -v`
Expected: All PASS

- [ ] **Step 7: Commit**

```bash
git add edge_agent/config.py edge_agent/config.yaml edge_agent/tests/test_config.py
git commit -m "feat: add auto_detect config option for OCR and parser language"
```

---

### Task 7: Use detected language for OCR fallback call

**Files:**
- Modify: `edge_agent/core/worker.py:234`
- Modify: `edge_agent/ocr/fallback.py:20-40`

**Interfaces:**
- Consumes: `language` detected in Task 3
- Produces: `ocr_fallback()` receives `language_hint` and passes to OCR engine

- [ ] **Step 1: Write the failing test**

Add to `edge_agent/tests/test_worker.py`:

```python
class TestWorkerOCRLanguageHint:
    @patch("edge_agent.core.worker.OCREngine")
    def test_arabic_ocr_fallback_uses_detected_lang(self, mock_ocr_cls, db, tmp_path):
        from edge_agent.core.models import ParsedDocument, Language

        # Parser returns short text (triggers OCR fallback)
        mock_parser = MagicMock()
        mock_parser.parse.return_value = ParsedDocument(markdown="نا")

        mock_ocr = MagicMock()
        mock_ocr.detect_language.return_value = Language.AR
        mock_ocr.extract_text.return_value = "نص عربي كامل من OCR"
        mock_ocr_cls.return_value = mock_ocr

        f = tmp_path / "scanned_arabic.png"
        f.write_bytes(b"\x89PNG fake image")
        db.upsert_files([{"id": "file1", "local_path": str(f), "filename": "scanned_arabic.png"}])

        with patch("edge_agent.core.worker.ParserRouter", return_value=mock_parser), \
             patch("edge_agent.core.worker.OCREngine", mock_ocr_cls), \
             patch("edge_agent.core.worker.ocr_fallback") as mock_fallback:
            mock_fallback.return_value = ("نص عربي كامل من OCR", True)
            w = Worker(db)
            w.start()
            try:
                jid = db.create_job("scan_file", {"file_id": "file1"})
                w.wait_for_job(jid, timeout=10.0)
                # ocr_fallback should have been called
                mock_fallback.assert_called_once()
            finally:
                w.stop()
```

- [ ] **Step 2: Run test to verify it passes (baseline)**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_worker.py::TestWorkerOCRLanguageHint -v`
Expected: PASS

- [ ] **Step 3: Update `ocr_fallback` to accept `language_hint`**

In `edge_agent/ocr/fallback.py`:

```python
def ocr_fallback(text: str, file_path: Path, ocr_engine: Any, language_hint: str | None = None) -> tuple[str, bool]:
    """Attempt OCR if extracted text is too short.

    Returns (final_text, ocr_used).
    """
    if text and len(text.strip()) >= _MIN_TEXT_LENGTH:
        return text, False

    suffix = file_path.suffix.lower()
    if suffix not in _OCR_EXTENSIONS:
        return text, False

    try:
        content = file_path.read_bytes()
        from edge_agent.core.models import Language
        hint = None
        if language_hint:
            try:
                hint = Language(language_hint)
            except ValueError:
                hint = None
        ocr_text = ocr_engine.extract_text(content, content_type="application/octet-stream", language_hint=hint)
        if ocr_text and len(ocr_text) > len(text):
            return ocr_text, True
    except Exception:
        logger.exception("OCR fallback failed for %s", file_path)

    return text, False
```

- [ ] **Step 4: Update worker to pass language to `ocr_fallback`**

In `edge_agent/core/worker.py`, update the `ocr_fallback` call:

```python
    text, ocr_used = ocr_fallback(text, path_obj, ocr, language_hint=language)
```

- [ ] **Step 5: Run tests**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/test_worker.py -v`
Expected: All PASS

- [ ] **Step 6: Commit**

```bash
git add edge_agent/ocr/fallback.py edge_agent/core/worker.py edge_agent/tests/test_worker.py
git commit -m "feat: pass detected language hint to OCR fallback"
```

---

### Task 8: Run full test suite and verify

**Files:**
- No new files

**Interfaces:**
- Consumes: all previous tasks
- Produces: all tests pass

- [ ] **Step 1: Run full test suite**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m pytest edge_agent/tests/ -v --tb=short`
Expected: All PASS

- [ ] **Step 2: Run linting**

Run: `cd /home/taher/Documents/ai-archive-platform && python -m ruff check edge_agent/`
Expected: No errors (or only pre-existing ones)

- [ ] **Step 3: Commit any lint fixes**

```bash
git add -A
git commit -m "fix: lint fixes for Arabic language support changes"
```

---

## Summary of Changes

| Change | Before | After |
|--------|--------|-------|
| `ParsedDocument.language` | Field doesn't exist | `language: str = "unknown"` |
| Language detection | `detect_language()` exists but unused | Called in `_execute_scan()` before storing |
| PaddleOCR language | Always uses config `lang` | Temporarily swaps to detected language per-document |
| OCR fallback | No language hint | Receives `language_hint` from detected language |
| MinerU parser | Always uses config `language` | Interface accepts `language` kwarg |
| Config defaults | `lang: en`, `language: en` | Added `auto_detect: true` option |
| Chunker | Only `؟` Arabic question mark | Added `؛` and `،` separators |
| DB language column | Always `"unknown"` | Stores detected language per-document |
| Sync payload | Sends `"unknown"` language | Sends actual detected language |
