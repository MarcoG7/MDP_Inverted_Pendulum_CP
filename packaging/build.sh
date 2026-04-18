#!/usr/bin/env bash
# Build script for Linux
# Run from the repo root: bash packaging/build.sh
set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$REPO_ROOT"

echo "==> Building Angular frontend..."
cd frontend/pendulum-cp-ui
npm run build -- --configuration production
cd "$REPO_ROOT"

echo "==> Running PyInstaller..."
source backend/.venv/bin/activate
pip install pyinstaller --quiet
pyinstaller packaging/pendulum.spec --distpath packaging/dist --workpath packaging/build --noconfirm

echo "==> Creating desktop shortcut..."
DESKTOP_FILE="$HOME/.local/share/applications/inverted-pendulum-cp.desktop"
INSTALL_DIR="$REPO_ROOT/packaging/dist/InvertedPendulumCP"
cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Inverted Pendulum CP
Comment=Inverted Pendulum Control Panel
Exec=$INSTALL_DIR/InvertedPendulumCP
Type=Application
Terminal=true
Categories=Education;Science;
EOF
chmod +x "$DESKTOP_FILE"

echo ""
echo "Done! App is at: $INSTALL_DIR/InvertedPendulumCP"
echo "Desktop shortcut created at: $DESKTOP_FILE"
