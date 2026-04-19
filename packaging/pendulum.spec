# PyInstaller spec file for Inverted Pendulum CP
# Run from the repo root: pyinstaller packaging/pendulum.spec

import glob
import os
import sys
from PyInstaller.utils.hooks import collect_submodules, collect_data_files, collect_all

block_cipher = None

# Collect all submodules from the backend package
numpy_datas, numpy_binaries, numpy_hiddenimports = collect_all("numpy")

# pydantic_core ships a compiled extension (_pydantic_core.cpXXX-win_amd64.pyd)
# that collect_all misses; find and bundle it explicitly.
import pydantic_core as _pc
_pc_dir = os.path.dirname(_pc.__file__)
pydantic_core_binaries = [
    (f, "pydantic_core") for f in glob.glob(os.path.join(_pc_dir, "_pydantic_core*.pyd"))
]
pydantic_core_datas, _, pydantic_core_hiddenimports = collect_all("pydantic_core")

# MATLAB's matlabmultidimarrayforpython.pyd is built against Python's stable ABI
# and imports from python3.dll (not python3XX.dll). PyInstaller bundles python3XX.dll
# but not the ABI3 forwarder, so we add it explicitly.
extra_binaries = []
if sys.platform == "win32":
    # In a venv, sys.executable is in venv/Scripts (no DLLs); python3.dll lives
    # next to the base interpreter. base_prefix falls back to prefix when not in a venv.
    for candidate_dir in (sys.base_prefix, os.path.dirname(sys.executable)):
        python3_dll = os.path.join(candidate_dir, "python3.dll")
        if os.path.isfile(python3_dll):
            extra_binaries.append((python3_dll, "."))
            break
    else:
        raise FileNotFoundError(
            "python3.dll not found — required at runtime by MATLAB's ABI3 pyd. "
            "Looked in sys.base_prefix and the executable dir."
        )

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
    binaries=numpy_binaries + pydantic_core_binaries + extra_binaries,
    datas=datas + numpy_datas + pydantic_core_datas,
    hiddenimports=hidden_imports + pydantic_core_hiddenimports,
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
