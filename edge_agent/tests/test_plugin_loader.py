"""Tests for edge_agent.core.plugin_loader — plugin discovery and registration."""
import tempfile
from pathlib import Path

import pytest

from edge_agent.core.plugin_loader import PluginRegistry


class TestPluginRegistry:
    def test_empty_registry(self):
        r = PluginRegistry()
        assert r.parsers == {}
        assert r.ocr_providers == {}

    def test_discover_empty_directory(self, tmp_path):
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert r.parsers == {}

    def test_discover_nonexistent(self):
        r = PluginRegistry()
        r.discover_plugins("/nonexistent/plugins")
        assert r.parsers == {}

    def test_discover_valid_plugin(self, tmp_path):
        plugin = tmp_path / "my_parser.py"
        plugin.write_text("""
from edge_agent.core.providers.base import ParserProvider
from edge_agent.core.models import ParsedDocument

class MyParser(ParserProvider):
    provider_name = "my_parser"
    def parse(self, file_path):
        return ParsedDocument(markdown="from plugin")
""")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert "my_parser" in r.parsers
        provider = r.parsers["my_parser"]()
        assert provider.parse("test.md").markdown == "from plugin"

    def test_discover_ocr_plugin(self, tmp_path):
        plugin = tmp_path / "my_ocr.py"
        plugin.write_text("""
from edge_agent.core.providers.base import OCRProvider

class MyOCR(OCRProvider):
    provider_name = "my_ocr"
    def extract_text(self, content, content_type=""):
        return "extracted"
""")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert "my_ocr" in r.ocr_providers

    def test_discover_package_plugin(self, tmp_path):
        pkg = tmp_path / "my_pkg"
        pkg.mkdir()
        (pkg / "__init__.py").write_text("""
from edge_agent.core.providers.base import ParserProvider
from edge_agent.core.models import ParsedDocument

class PkgParser(ParserProvider):
    provider_name = "pkg_parser"
    def parse(self, file_path):
        return ParsedDocument(markdown="pkg")
""")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert "pkg_parser" in r.parsers

    def test_discover_skips_non_provider(self, tmp_path):
        plugin = tmp_path / "not_provider.py"
        plugin.write_text("""
class NotAProvider:
    pass
""")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert r.parsers == {}

    def test_discover_skips_hidden_files(self, tmp_path):
        (tmp_path / ".hidden.py").write_text("")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert r.parsers == {}

    def test_list_capabilities_empty(self):
        r = PluginRegistry()
        caps = r.list_capabilities()
        assert caps == {"parsers": [], "ocr": [], "llm": [], "embeddings": []}

    def test_list_capabilities(self, tmp_path):
        plugin = tmp_path / "a.py"
        plugin.write_text("""
from edge_agent.core.providers.base import ParserProvider, OCRProvider
from edge_agent.core.models import ParsedDocument

class P1(ParserProvider):
    provider_name = "p1"
    def parse(self, fp): return ParsedDocument(markdown="")

class O1(OCRProvider):
    provider_name = "o1"
    def extract_text(self, c, ct=""): return ""
""")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        caps = r.list_capabilities()
        assert "p1" in caps["parsers"]
        assert "o1" in caps["ocr"]

    def test_import_error_plugin_skipped(self, tmp_path):
        plugin = tmp_path / "broken.py"
        plugin.write_text("import nonexistent_module\n")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert r.parsers == {}

    def test_duplicate_provider_name_overwrites(self, tmp_path):
        a = tmp_path / "a.py"
        a.write_text("""
from edge_agent.core.providers.base import ParserProvider
from edge_agent.core.models import ParsedDocument

class P1(ParserProvider):
    provider_name = "dup"
    def parse(self, fp): return ParsedDocument(markdown="a")
""")
        b = tmp_path / "b.py"
        b.write_text("""
from edge_agent.core.providers.base import ParserProvider
from edge_agent.core.models import ParsedDocument

class P2(ParserProvider):
    provider_name = "dup"
    def parse(self, fp): return ParsedDocument(markdown="b")
""")
        r = PluginRegistry()
        r.discover_plugins(str(tmp_path))
        assert "dup" in r.parsers
