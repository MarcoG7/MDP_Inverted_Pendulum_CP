# PyInstaller spec file for Inverted Pendulum CP
# Run from the repo root: pyinstaller packaging/pendulum.spec

import os
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

block_cipher = None

# Collect all submodules from the backend package
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all("numpy")

hidden_imports = (
    collect_submodules("pendulum_cp")
    + collect_submodules("uvicorn")
    + collect_submodules("fastapi")
    + collect_submodules("anyio")
    + collect_submodules("starlette")
    + numpy_hiddenimports
    + [
        "uvicorn.logging",
        "uvicorn.loops.auto",
        "uvicorn.protocols.http.auto",
        "uvicorn.protocols.websockets.auto",
        "uvicorn.lifespan.on",
        # matlab.engine is NOT bundled — it is loaded from the MATLAB
        # installation at runtime by run.py's _inject_matlab_path()
    ]
)

# All paths are relative to the repo root, not the spec file location
repo_root = os.path.abspath(os.path.join(SPECPATH, ".."))

angular_dist = os.path.join(
    repo_root, "frontend", "pendulum-cp-ui", "dist", "pendulum-cp-ui", "browser"
)
simulations_dir = os.path.join(repo_root, "simulations")
datas = [
    (angular_dist, "static"),
    (simulations_dir, "simulations"),
]

a = Analysis(
    [os.path.join(repo_root, "backend", "run.py")],
    pathex=[os.path.join(repo_root, "backend", "src")],
    binaries=numpy_binaries,
    datas=datas + numpy_datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["matlab", "matlab.engine"],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="InvertedPendulumCP",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="InvertedPendulumCP",
)
