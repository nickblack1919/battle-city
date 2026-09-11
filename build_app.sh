#!/bin/sh
# Build Mac app dist/Battle City.app (PYINSTALLER can point to another pyinstaller)
cd "$(dirname "$0")" || exit 1
PYINSTALLER="${PYINSTALLER:-venv/bin/pyinstaller}"
exec "$PYINSTALLER" --noconfirm --clean battle_city.spec
