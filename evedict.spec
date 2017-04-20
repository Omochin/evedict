# -*- mode: python -*-

# Command line to build:
# pyinstaller --clean --noconfirm --upx-dir=.\scripts\upx.exe evedict.spec

# Don't forget to change the path to where your evedict.py and evedict.spec lives
#  pathex=['C:\\works\\evedict'],

block_cipher = None

added_files = [
    ('locales', 'locales'),
    ('static', 'static'),
    ('templates', 'templates'),
    ('evedict.ico', '.'),
    ('config.yaml', '.'),
    ('README.md', '.'),
    ('LICENSE', '.'),
]

import_these = []

a = Analysis(
    ['evedict.py'],
    pathex=['C:\\works\\evedict'],
    binaries=[],
    datas=added_files,
    hiddenimports=import_these,
    hookspath=[],
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
)
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=block_cipher,
)
exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    debug=False,
    console=True,
    strip=False,
    upx=True,
    name='evedict',
    icon='evedict.ico',
    onefile=False,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    onefile=False,
    name='evedict',
    icon='evedict.ico',
)
