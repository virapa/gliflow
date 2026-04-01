# -*- mode: python ; coding: utf-8 -*-
import sys
from pathlib import Path

block_cipher = None

a = Analysis(
    ['src/main.py'],
    pathex=['.'],
    binaries=[],
    datas=[
        ('assets/icon.png', 'assets'),
    ],
    hiddenimports=[
        'pynput.keyboard._win32',
        'pynput.keyboard._darwin',
        'pynput.keyboard._xorg',
        'pynput.mouse._win32',
        'pynput.mouse._darwin',
        'pynput.mouse._xorg',
        'pystray._win32',
        'pystray._darwin',
        'pystray._xorg',
        'PIL._tkinter_finder',
        'keyring.backends.Windows',
        'keyring.backends.macOS',
        'keyring.backends.SecretService',
        'keyring.backends.fail',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='GliFlow',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=False,               # no terminal window
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    # Windows icon
    icon='assets/icon.png' if sys.platform == 'win32' else None,
)

# macOS .app bundle
if sys.platform == 'darwin':
    app = BUNDLE(
        exe,
        name='GliFlow.app',
        icon='assets/icon.png',
        bundle_identifier='com.virapa.gliflow',
        info_plist={
            'NSMicrophoneUsageDescription': 'GliFlow needs microphone access for speech-to-text.',
            'NSAppleEventsUsageDescription': 'GliFlow uses Apple Events for text insertion.',
            'LSUIElement': True,   # hide from Dock (tray-only app)
        },
    )
