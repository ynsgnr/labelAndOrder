"""Print a folder of sticker PNGs on the Orgstra S001 via the TiMini CLI.

Depends on TiMini-Print (the S001 label-printer driver):
    https://github.com/ynsgnr/TiMini-Print
Point --timini (or the TIMINI_DIR env var) at your local TiMini-Print checkout.

Waits for Enter before EACH sticker, so you can check the last one and reposition
the roll instead of the printer running the whole batch non-stop.

    py print.py out                           # Enter prints the next one
    py print.py out --yes                     # print everything, no prompts
    py print.py out --test                    # print only the first, then stop
    py print.py out --rest                    # skip the first, prompt for the rest
    py print.py out --serial COM5 --paper tag_90r_90p --timini ../TiMini-Print

At each prompt: Enter = print it, s = skip it, q = stop.

The generator already draws stickers at the S001's true printed size (including the
paper-advance/length calibration), so this just streams each PNG to TiMini as-is.
"""
from __future__ import annotations
import argparse
import glob
import os
import subprocess
import sys


def print_one(png, serial, model, paper, timini_dir) -> None:
    # TiMini runs with cwd in its own checkout, so pass an absolute sticker path.
    cmd = [sys.executable, "-m", "timiniprint", "--serial", serial,
           "--printer-model", model, "--paper", paper, os.path.abspath(png)]
    print(f"  -> {os.path.basename(png)}")
    subprocess.run(cmd, cwd=timini_dir, check=True)


def main(argv=None):
    p = argparse.ArgumentParser(description="Print sticker PNGs on the S001 via TiMini.")
    p.add_argument("folder", help="folder of .png stickers (from gen.py)")
    p.add_argument("--serial", default="COM5")
    p.add_argument("--model", default="orgstra_s001")
    p.add_argument("--paper", default="tag_90r_90p", help="1:1 preset (render 90 / length 280)")
    p.add_argument("--timini", default=os.environ.get("TIMINI_DIR"),
                   help="path to a TiMini-Print checkout (or set TIMINI_DIR); "
                        "https://github.com/ynsgnr/TiMini-Print")
    g = p.add_mutually_exclusive_group()
    g.add_argument("--yes", action="store_true", help="print all without prompting")
    g.add_argument("--test", action="store_true", help="print only the first, then stop")
    g.add_argument("--rest", action="store_true", help="skip the first, prompt for the rest")
    args = p.parse_args(argv)

    if not args.timini or not os.path.isdir(args.timini):
        sys.exit("set --timini <path> or TIMINI_DIR to your TiMini-Print checkout "
                 "(https://github.com/ynsgnr/TiMini-Print)")

    pngs = sorted(glob.glob(os.path.join(args.folder, "*.png")))
    pngs = [p for p in pngs if not os.path.basename(p).startswith("_")]  # skip _preview.png
    if not pngs:
        sys.exit(f"no .png stickers in {args.folder!r}")

    def run(items):
        for png in items:
            print_one(png, args.serial, args.model, args.paper, args.timini)

    if args.test:
        print(f"test print (1 of {len(pngs)}):")
        run(pngs[:1])
        return
    if args.yes:
        print(f"printing all {len(pngs)}:")
        run(pngs)
        return
    if args.rest:
        pngs = pngs[1:]

    # one at a time: nothing prints until you press Enter for it
    print(f"{len(pngs)} stickers — Enter prints the next, 's' skips it, 'q' stops.")
    total = len(pngs)
    for i, png in enumerate(pngs, 1):
        ans = input(f"[{i}/{total}] {os.path.basename(png)} > ").strip().lower()
        if ans == "q":
            print(f"stopped at {i} of {total}.")
            return
        if ans == "s":
            continue
        print_one(png, args.serial, args.model, args.paper, args.timini)
    print(f"done ({total} stickers).")


if __name__ == "__main__":
    main()
