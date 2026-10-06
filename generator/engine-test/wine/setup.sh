#!/usr/bin/env bash
# Prepare Linux to run the engine test under Wine: see ../README.md. Needs mingw-w64 and Wine.
#
#     ./setup.sh [build folder]
#
# The Windows crates name import libraries with capitals (Advapi32) while mingw-w64 ships them in
# lowercase (libadvapi32.a), so this links each one under its capitalized name. It also builds a
# stand-in winsqlite3.dll, which Windows has and Wine doesn't.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
out="$(mkdir -p "${1:-$here/.build}" && cd "${1:-$here/.build}" && pwd)"
mkdir -p "$out/mingw-case"
for lib in /usr/x86_64-w64-mingw32/lib/lib*.a; do
  name="$(basename "$lib" .a)"
  name="${name#lib}"
  ln -sf "$lib" "$out/mingw-case/lib${name^}.a"
done
x86_64-w64-mingw32-gcc -shared -O2 -o "$out/winsqlite3.dll" "$here/winsqlite3.c"
echo "Build with:  RUSTFLAGS=\"-L $out/mingw-case\" cargo test --target x86_64-pc-windows-gnu --no-run"
echo "Then copy $out/winsqlite3.dll next to the test executable in target/x86_64-pc-windows-gnu/debug/deps/."
