"""Pre-generate the whole sticker catalogue, one folder per label template.

    py build_catalog.py                # writes ./<template-key>/*.png
    py build_catalog.py --clean        # remove the folders first

So people can clone the repo and print, without generating anything:

    stickers/s001-12x40mm/m4x20-screw-pan-philips.png
    stickers/label-40x30mm/m5-nut-nylon.png

Each folder also gets a preview.png contact sheet, like the one in the README.
"""
from __future__ import annotations
import argparse
import os
import shutil

import gen

# Nut sizes worth stocking, plain and nyloc.
NUT_SIZES = [1.6, 2, 2.5, 3, 4, 5, 6, 8, 10, 12]

# Screw lengths that actually exist per diameter (DIN/ISO stock lengths).
SCREW_LENGTHS = {
    2: [4, 6, 8, 10, 12, 16, 20],
    2.5: [4, 6, 8, 10, 12, 16, 20],
    3: [4, 6, 8, 10, 12, 16, 18, 20, 25, 30, 35, 40],
    4: [6, 8, 10, 12, 16, 18, 20, 25, 30, 35, 40, 45, 50],
    5: [8, 10, 12, 16, 18, 20, 25, 30, 35, 40, 45, 50],
    6: [8, 10, 12, 16, 18, 20, 25, 30, 35, 40, 45, 50, 60],
    8: [10, 12, 16, 18, 20, 25, 30, 35, 40, 45, 50, 60, 70],
}
HEAD_SHAPES = ["hex", "pan", "csk"]          # the three profiles gen.py draws
DRIVES = ["philips", "allen", "torx", "slot"]   # the drives people actually meet

# Wall plugs, in the sizes the common drill bits give you.
PLUGS = [("SX", 5, 25), ("SX", 6, 30), ("SX", 6, 40),
         ("SX", 8, 40), ("SX", 8, 50), ("SX", 10, 50)]

# Plain captions. Generate your own with: gen.py "text:Washers"
TEXTS = ["Misc"]


def specs() -> list[tuple]:
    out = [("nut", m, None, variant, None)
           for m in NUT_SIZES for variant in (None, "nylon")]
    out += [("screw", m, length, shape, drive)
            for m, lengths in SCREW_LENGTHS.items()
            for length in lengths
            for shape in HEAD_SHAPES
            for drive in DRIVES]
    out += [("plug", dia, length, prefix, None) for prefix, dia, length in PLUGS]
    out += [("text", 0, None, caption, None) for caption in TEXTS]
    return out


def preview_specs() -> list[tuple]:
    """A handful of representative stickers for the folder's contact sheet."""
    return [gen.parse_spec(t) for t in
            ("M5", "M5:nylon", "M4x20:pan:philips", "M5x30:csk:pozi",
             "M6x40:hex:torx", "M3x10", "SX6x30:plug")]


def build(template: gen.Template, all_specs: list[tuple], root: str) -> int:
    gen.use_template(template)
    folder = os.path.join(root, template.key)
    os.makedirs(folder, exist_ok=True)
    for spec in all_specs:
        gen.make_label(*spec).save(os.path.join(folder, gen.spec_name(spec) + ".png"))
    gen.contact_sheet(preview_specs(), out=os.path.join(folder, "preview.png"))
    w_mm, h_mm = template.size_mm
    print(f"  {template.key:18} {template.w:>4}x{template.h:<4} dots  "
          f"{w_mm:5.1f}x{h_mm:<5.1f} mm  {template.dpi} dpi  "
          f"{len(all_specs)} stickers")
    return len(all_specs)


def main(argv=None):
    p = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    p.add_argument("--out", default=".", help="root folder (default: the repo root)")
    p.add_argument("--clean", action="store_true", help="delete each template folder first")
    p.add_argument("--template", action="append", choices=sorted(gen.TEMPLATES),
                   help="only this template (repeatable); default is all")
    args = p.parse_args(argv)

    keys = args.template or sorted(gen.TEMPLATES)
    all_specs = specs()
    print(f"{len(all_specs)} stickers x {len(keys)} templates "
          f"= {len(all_specs) * len(keys)} files")
    total = 0
    for key in keys:
        if args.clean:
            shutil.rmtree(os.path.join(args.out, key), ignore_errors=True)
        total += build(gen.TEMPLATES[key], all_specs, args.out)
    print(f"done: {total} PNGs")


if __name__ == "__main__":
    main()
