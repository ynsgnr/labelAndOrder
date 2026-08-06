"""Print a folder of sticker PNGs on the Orgstra S001 via the TiMini CLI.

Depends on TiMini-Print (the S001 label-printer driver):
    https://github.com/ynsgnr/TiMini-Print
Point --timini (or the TIMINI_DIR env var) at your local TiMini-Print checkout.

Prints ONE sticker first, waits for your approval, then prints the rest.

    py print.py out                           # test first, prompt, then the rest
    py print.py out --yes                     # print everything, no prompt
    py print.py out --test                    # print only the first, then stop
    py print.py out --rest                    # print all except the first
    py print.py out --serial COM5 --paper tag_90r_90p --timini ../TiMini-Print
"""
from __future__ import annotations
import argparse
import glob
import os
import subprocess
import sys


def print_one(png: str, serial: str, model: str, paper: str, timini_dir: str) -> None:
    cmd = [sys.executable, "-m", "timiniprint",
           "--serial", serial, "--printer-model", model, "--paper", paper, png]
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
    g.add_argument("--rest", action="store_true", help="print all except the first")
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

    if args.rest:
        run(pngs[1:])
        return
    if args.test:
        print(f"test print (1 of {len(pngs)}):")
        run(pngs[:1])
        return
    if args.yes:
        print(f"printing all {len(pngs)}:")
        run(pngs)
        return

    # interactive: one test print, then confirm the rest
    print(f"test print (1 of {len(pngs)}):")
    run(pngs[:1])
    if len(pngs) == 1:
        return
    ans = input(f"Looks good? print the remaining {len(pngs) - 1}? [y/N] ").strip().lower()
    if ans == "y":
        run(pngs[1:])
    else:
        print("stopped; rerun with --rest to print the remaining stickers.")


if __name__ == "__main__":
    main()
