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
pip install -e backend --quiet
pyinstaller packaging/pendulum.spec --distpath packaging/dist --workpath packaging/build --noconfirm

echo "==> Creating launcher and desktop shortcut..."
INSTALL_DIR="$REPO_ROOT/packaging/dist/InvertedPendulumCP"
LAUNCHER="$INSTALL_DIR/launch.sh"
DESKTOP_FILE="$HOME/.local/share/applications/inverted-pendulum-cp.desktop"

# Launcher script: finds an available terminal emulator and runs the app inside it
cat > "$LAUNCHER" <<'LAUNCHER_EOF'
#!/usr/bin/env bash
APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
"$APP_DIR/InvertedPendulumCP"
LAUNCHER_EOF
chmod +x "$LAUNCHER"

cat > "$DESKTOP_FILE" <<EOF
[Desktop Entry]
Name=Inverted Pendulum CP
Comment=Inverted Pendulum Control Panel
Exec=$LAUNCHER
Type=Application
Terminal=false
Categories=Education;Science;
EOF
chmod +x "$DESKTOP_FILE"

echo ""
echo "Done! App is at: $INSTALL_DIR/InvertedPendulumCP"
echo "Desktop shortcut created at: $DESKTOP_FILE"
