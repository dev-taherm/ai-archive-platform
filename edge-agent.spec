# -*- mode: python ; coding: utf-8 -*-


a = Analysis(
    ['edge_agent/__main__.py'],
    pathex=[],
    binaries=[],
    datas=[('edge_agent/config.yaml', 'edge_agent')],
    hiddenimports=['edge_agent', 'edge_agent.cli', 'edge_agent.config', 'edge_agent.core.scanner', 'edge_agent.core.chunker', 'edge_agent.core.models', 'edge_agent.db.local_db', 'edge_agent.parsers.document_reader', 'edge_agent.parsers.mineru', 'edge_agent.parsers.router', 'edge_agent.ocr.engine', 'edge_agent.ocr.worker', 'edge_agent.sync.manager', 'edge_agent.watcher.monitor', 'httpx', 'yaml'],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['paddleocr', 'paddlepaddle', 'torch', 'numpy', 'scipy', 'pandas', 'matplotlib', 'tkinter', 'unittest', 'pytest', 'watchdog', 'pdfplumber', 'docx', 'openpyxl', 'PIL', 'fitz', 'cv2', 'pytesseract', 'mineru'],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='edge-agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
