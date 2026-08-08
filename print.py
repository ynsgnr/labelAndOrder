"""Print a folder of sticker PNGs on the Orgstra S001 via the TiMini CLI.

Needs a checkout of TiMini-Print, the S001 driver, pointed at by --timini or the
TIMINI_DIR env var: https://github.com/ynsgnr/TiMini-Print

Nothing prints until you ask for it, so you can check the last label and
reposition the roll between stickers:

    py print.py out                    # Enter prints the next one
    py print.py out --count 2          # 2 copies of every sticker
    py print.py out --yes              # print everything, no prompts
    py print.py out --test             # print only the first, then stop
    py print.py out --rest             # skip the first, prompt for the rest

At each prompt: Enter prints --count copies, a number prints that many copies of
just that sticker, 's' skips it, 'q' stops.

gen.py already draws stickers at the S001's true printed size, so each PNG is
streamed to TiMini as-is.
"""
from __future__ import annotations
import argparse
import glob
import os
import subprocess
import sys
import time
from dataclasses import dataclass, field


class Stop(Exception):
    """Abandon the batch — the user asked, or a job failed unattended."""


@dataclass
class Printer:
    """One S001 on a serial port, printing PNGs through the TiMini CLI.

    The printer closes its SPP port at the end of a job and needs a moment before
    it will accept another, so jobs are spaced by `delay` seconds.
    """
    serial: str
    model: str
    paper: str
    timini: str
    delay: float = 2.0
    _last_job: float = field(default=0.0, repr=False)

    def send(self, png: str) -> bool:
        """Run one TiMini job, waiting out the gap first. True if it printed."""
        idle = self.delay - (time.monotonic() - self._last_job)
        if idle > 0:
            time.sleep(idle)
        # TiMini runs with cwd in its own checkout, so pass an absolute path.
        cmd = [sys.executable, "-m", "timiniprint", "--serial", self.serial,
               "--printer-model", self.model, "--paper", self.paper,
               os.path.abspath(png)]
        try:
            return subprocess.run(cmd, cwd=self.timini).returncode == 0
        finally:
            self._last_job = time.monotonic()

    def copies(self, png: str, count: int, interactive: bool = True) -> None:
        """Print `count` copies. A failed job is offered for retry rather than
        losing the rest of the batch."""
        name = os.path.basename(png)
        done = 0
        while done < count:
            print(f"  -> {name}" + (f"  (copy {done + 1}/{count})" if count > 1 else ""))
            if self.send(png):
                done += 1
                continue
            print(f"  !! {name} failed to print — printer asleep or COM port dropped.")
            if not interactive:
                raise Stop(f"{name} failed (non-interactive)")
            answer = input("     [Enter] retry · 's' skip this copy · 'q' stop > ")
            answer = answer.strip().lower()
            if answer == "q":
                raise Stop(f"{name} failed")
            if answer == "s":
                done += 1


def prompt_each(printer: Printer, pngs: list[str], count: int) -> None:
    """Walk the batch, printing only what's asked for at each prompt."""
    total = len(pngs)
    print(f"{total} stickers{f' x{count}' if count > 1 else ''} — Enter prints the "
          f"next, a number prints that many copies, 's' skips it, 'q' stops.")
    for i, png in enumerate(pngs, 1):
        answer = input(f"[{i}/{total}] {os.path.basename(png)} > ").strip().lower()
        if answer == "q":
            print(f"stopped at {i} of {total}.")
            return
        wanted = int(answer) if answer.isdigit() else (0 if answer == "s" else count)
        if wanted > 0:
            printer.copies(png, wanted)
    print(f"done ({total} stickers).")


def main(argv=None):
    p = argparse.ArgumentParser(description="Print sticker PNGs on the S001 via TiMini.")
    p.add_argument("folder", help="folder of .png stickers (from gen.py)")
    p.add_argument("--serial", default="COM5")
    p.add_argument("--model", default="orgstra_s001")
    p.add_argument("--paper", default="tag_90r_90p", help="1:1 preset (render 90 / length 280)")
    p.add_argument("--count", type=int, default=1, metavar="N",
                   help="copies of each sticker (default: 1)")
    p.add_argument("--delay", type=float, default=2.0, metavar="S",
                   help="seconds between jobs, so the S001's SPP port comes back "
                        "(default: 2)")
    p.add_argument("--timini", default=os.environ.get("TIMINI_DIR"),
                   help="path to a TiMini-Print checkout (or set TIMINI_DIR); "
                        "https://github.com/ynsgnr/TiMini-Print")
    mode = p.add_mutually_exclusive_group()
    mode.add_argument("--yes", action="store_true", help="print all without prompting")
    mode.add_argument("--test", action="store_true", help="print only the first, then stop")
    mode.add_argument("--rest", action="store_true", help="skip the first, prompt for the rest")
    args = p.parse_args(argv)

    if not args.timini or not os.path.isdir(args.timini):
        sys.exit("set --timini <path> or TIMINI_DIR to your TiMini-Print checkout "
                 "(https://github.com/ynsgnr/TiMini-Print)")
    if args.count < 1:
        sys.exit("--count must be 1 or more")

    pngs = sorted(glob.glob(os.path.join(args.folder, "*.png")))
    pngs = [f for f in pngs if not os.path.basename(f).startswith("_")]  # skip _preview
    if not pngs:
        sys.exit(f"no .png stickers in {args.folder!r}")

    printer = Printer(args.serial, args.model, args.paper, args.timini, args.delay)
    each = f" x{args.count}" if args.count > 1 else ""
    try:
        if args.test:
            print(f"test print (1 of {len(pngs)}){each}:")
            printer.copies(pngs[0], args.count)
        elif args.yes:
            print(f"printing all {len(pngs)}{each}:")
            for png in pngs:
                printer.copies(png, args.count, interactive=False)
        else:
            prompt_each(printer, pngs[1:] if args.rest else pngs, args.count)
    except Stop as e:
        sys.exit(f"stopped: {e}. Check the printer is awake, then rerun — the folder "
                 f"is safe to re-run, just skip what already printed.")


if __name__ == "__main__":
    main()
