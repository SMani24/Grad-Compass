"""Generate a desktop entry for this checkout without installing it."""
import argparse
from pathlib import Path

APP_ROOT = Path(__file__).resolve().parents[1]


def quoted(value):
    # Exec uses desktop-entry quoting, then string-value escaping (not a shell).
    value = str(value).replace("%", "%%")
    escaped = "".join("\\" + char if char in '\\"`$' else char for char in value)
    return '"' + escaped.replace("\\", "\\\\") + '"'


def string_value(value):
    return str(value).replace("\\", "\\\\").replace("\n", "\\n").replace("\r", "\\r")


def entry_text():
    interpreter = APP_ROOT / "envGradCompass" / "bin" / "python"
    if not interpreter.is_file():
        raise ValueError("Install the application's virtual environment before creating its desktop entry")
    return "\n".join([
        "[Desktop Entry]",
        "Type=Application",
        "Name=Grad Compass",
        "GenericName=Graduate Application Workspace",
        "Comment=Explore saved countries and review local graduate research",
        f"Exec={quoted(interpreter)} -B {quoted(APP_ROOT / 'scripts' / 'launch_preview.py')}",
        f"Path={string_value(APP_ROOT.parent)}",
        f"Icon={string_value(APP_ROOT / 'ui' / 'assets' / 'grad-compass.svg')}",
        "Terminal=false",
        "Categories=Education;",
        "Keywords=university;graduate;phd;masters;applications;compass;",
        "StartupNotify=false",
        "",
    ])


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    args.output.write_text(entry_text(), encoding="utf-8")
    print(args.output)


if __name__ == "__main__":
    main()
