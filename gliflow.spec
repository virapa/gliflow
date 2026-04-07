# -*- mode: python ; coding: utf-8 -*-
import sys
from PyInstaller.utils.hooks import collect_all, collect_data_files

block_cipher = None

# Collect all binaries + data for packages that need it
numpy_datas,    numpy_binaries,    numpy_hidden    = collect_all('numpy')
sounddevice_datas, sounddevice_binaries, sounddevice_hidden = collect_all('sounddevice')
pynput_datas,   pynput_binaries,   pynput_hidden   = collect_all('pynput')
pystray_datas,  pystray_binaries,  pystray_hidden  = collect_all('pystray')
keyring_datas,  keyring_binaries,  keyring_hidden  = collect_all('keyring')

a = Analysis(
    ['run.py'],
    pathex=['.'],
    binaries=[
        *numpy_binaries,
        *sounddevice_binaries,
        *pynput_binaries,
        *pystray_binaries,
        *keyring_binaries,
    ],
    datas=[
        ('assets/icon.png', 'assets'),
        *numpy_datas,
        *sounddevice_datas,
        *pynput_datas,
        *pystray_datas,
        *keyring_datas,
    ],
    hiddenimports=[
        *numpy_hidden,
        *sounddevice_hidden,
        *pynput_hidden,
        *pystray_hidden,
        *keyring_hidden,
        'numpy.core._multiarray_umath',
        'numpy.core._multiarray_tests',
        'numpy.core.multiarray',
        'numpy.core.numeric',
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
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
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
            'LSUIElement': True,
        },
    )
