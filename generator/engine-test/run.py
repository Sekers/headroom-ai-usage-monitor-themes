"""Run the native Windows engine test in an isolated upstream checkout.

    python generator/engine-test/run.py <build folder> <render folder>

Requires Git, Rust 1.95 with the MSVC toolchain, and the Windows C++ build tools.
The build folder's monitor subfolder must not already exist. The checkout and
renders remain available for inspection after the command finishes.
"""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[2]
UPSTREAM = "https://github.com/CodeZeno/Claude-Code-Usage-Monitor.git"
UPSTREAM_TAG = "v2.18.1"
UPSTREAM_COMMIT = "623e8915a4ffc784c341aa2d6fdc71ac37f93e36"
TEST = "theme_engine::pack_tests::theme_pack_validates_and_renders"


def run(command, cwd, **kwargs):
    try:
        return subprocess.run(command, cwd=cwd, check=True, text=True, **kwargs)
    except subprocess.CalledProcessError as error:
        if error.stdout:
            print(error.stdout, file=sys.stderr, end="")
        if error.stderr:
            print(error.stderr, file=sys.stderr, end="")
        raise


def prepare(checkout):
    checkout.parent.mkdir(parents=True, exist_ok=True)
    if checkout.exists():
        raise RuntimeError(f"Use a fresh build folder; {checkout} already exists")
    run(["git", "clone", "--depth", "1", "--branch", UPSTREAM_TAG, UPSTREAM, str(checkout)], ROOT)
    commit = run(["git", "rev-parse", "HEAD"], checkout, capture_output=True).stdout.strip()
    if commit != UPSTREAM_COMMIT:
        raise RuntimeError(f"Upstream {UPSTREAM_TAG} changed: expected {UPSTREAM_COMMIT}, got {commit}")

    # Only the disposable upstream checkout is changed. The renderer stays intact.
    engine = checkout / "src" / "theme_engine.rs"
    source = engine.read_text(encoding="utf-8")
    source += "\n#[cfg(test)]\nmod pack_tests;\n"
    engine.write_text(source, encoding="utf-8")
    shutil.copyfile(Path(__file__).with_name("pack_tests.rs"), checkout / "src" / "theme_engine" / "pack_tests.rs")

    # Exercise both color modes without changing the user's Windows registry.
    theme = checkout / "src" / "theme.rs"
    source = theme.read_text(encoding="utf-8")
    anchor = "pub fn is_dark_mode() -> bool {"
    if source.count(anchor) != 1:
        raise RuntimeError("Cannot install the test color-mode override in upstream theme.rs")
    override = '''
    #[cfg(test)]
    if let Ok(mode) = std::env::var("HEADROOM_TEST_DARK_MODE") {
        return mode == "dark";
    }'''
    theme.write_text(source.replace(anchor, anchor + override), encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("build", type=Path)
    parser.add_argument("renders", type=Path)
    args = parser.parse_args()
    if sys.platform != "win32":
        raise RuntimeError("This runner requires Windows; see README.md for Wine instructions")
    checkout, output = args.build.resolve() / "monitor", args.renders.resolve()
    output.mkdir(parents=True, exist_ok=True)
    prepare(checkout)
    environment = dict(os.environ, THEME_PACK_DIR=str(ROOT / "themes"), THEME_PACK_OUT=str(output))
    built = subprocess.run(
        ["cargo", "test", "--locked", "--no-run", "--bin", "claude-code-usage-monitor", "--message-format=json"],
        cwd=checkout, env=environment, text=True, stdout=subprocess.PIPE,
    )
    executables = []
    for line in built.stdout.splitlines():
        message = json.loads(line)
        if message.get("reason") == "compiler-message":
            rendered = message["message"].get("rendered")
            if rendered:
                print(rendered, file=sys.stderr, end="")
        if (message.get("reason") == "compiler-artifact"
                and message["profile"]["test"] and message.get("executable")):
            executables.append(message["executable"])
    built.check_returncode()
    if len(executables) != 1:
        raise RuntimeError(f"Expected one upstream test executable, got {len(executables)}")
    executable = executables[0]
    listed = run([executable, "--list"], checkout, env=environment, capture_output=True).stdout
    if f"{TEST}: test" not in listed.splitlines():
        raise RuntimeError(f"The upstream test binary does not contain {TEST}")
    for mode in ("dark", "light"):
        print(f"Testing {UPSTREAM_TAG} on Windows in {mode} mode", flush=True)
        # The upstream test executable uses the Windows GUI subsystem. Explicit
        # pipes keep its test results visible when Python has no console.
        result = run([executable, TEST, "--exact", "--nocapture"], checkout,
                     env=dict(environment, HEADROOM_TEST_DARK_MODE=mode), capture_output=True)
        print(result.stdout, end="", flush=True)
        print(result.stderr, file=sys.stderr, end="", flush=True)
    print(f"Windows engine checks passed in both modes; renders: {output}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(error, file=sys.stderr)
        raise SystemExit(1)
