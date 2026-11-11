"""Run one AutoCAD Core Console job with a bounded lifetime."""

import argparse
import os
from pathlib import Path
import signal
import subprocess


DEFAULT_CONSOLE = Path(
    "/Applications/Autodesk/AutoCAD 2027/AutoCAD 2027.app/Contents/Helpers/"
    "AcCoreConsole.app/Contents/MacOS/AcCoreConsole"
)


def signal_job(process, sig):
    try:
        os.killpg(process.pid, sig)
    except ProcessLookupError:
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--console", type=Path, default=DEFAULT_CONSOLE)
    parser.add_argument("--timeout", type=float, default=120, help="seconds")
    parser.add_argument("--log", type=Path, required=True)
    parser.add_argument("drawing", type=Path, help="unique writable working copy")
    parser.add_argument("script", type=Path)
    args = parser.parse_args()
    if args.timeout <= 0:
        parser.error("--timeout must be positive")
    drawing, script = (path.resolve() for path in (args.drawing, args.script))
    for path in (drawing, script, args.console):
        if not path.is_file():
            parser.error(f"file missing: {path}")
    with args.log.open("xb") as log:
        with subprocess.Popen(
            [str(args.console.resolve()), "-i", str(drawing), "-s", str(script)],
            cwd=drawing.parent,
            stdin=subprocess.DEVNULL,
            stdout=log,
            stderr=subprocess.STDOUT,
            start_new_session=True,
        ) as process:
            try:
                return process.wait(timeout=args.timeout)
            except (subprocess.TimeoutExpired, KeyboardInterrupt) as exc:
                signal_job(process, signal.SIGTERM)
                try:
                    process.wait(timeout=3)
                except subprocess.TimeoutExpired:
                    pass
                signal_job(process, signal.SIGKILL)
                process.wait()
                log.write(f"\nCore Console stopped: {type(exc).__name__}\n".encode())
                return 124 if isinstance(exc, subprocess.TimeoutExpired) else 130


if __name__ == "__main__":
    raise SystemExit(main())
