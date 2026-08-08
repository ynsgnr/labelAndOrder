"""Generate actual-size nut / screw / wall-plug organisation stickers.

Everything is drawn at nominal ISO size, 1 px per dot, so it comes off the printer
true to size. That needs only two facts about the printer — its head resolution
(DPMM) and its printable area (W, H) — both of which TiMini already knows per
model. There are no calibration fudge factors; if a print measures wrong, the
cause is upstream (see the margin-trimming note in print.py), not here.

Anything bigger than the label runs off the edge and is cut, by design.
"""
from __future__ import annotations
import math
from dataclasses import dataclass
from string import ascii_uppercase
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- geometry ---
# A label is fully described by its printable size in dots and its head
# resolution — both of which TiMini knows per model. Everything else is drawn in
# millimetres and converted, so the same code is correct at any resolution.

BLACK, WHITE = 0, 1


@dataclass(frozen=True)
class Template:
    """A printable label area. `w`/`h` are dots; the drawing is isotropic, so
    which axis is the head and which the feed only matters to the printer."""
    key: str
    w: int
    h: int
    dpi: int = 203
    note: str = ""

    @property
    def dpmm(self) -> float:
        return self.dpi / 25.4

    @property
    def size_mm(self) -> tuple[float, float]:
        return self.w / self.dpmm, self.h / self.dpmm


# Orgstra S001: 12 x 40 mm label. The head is 96 dots but the protocol reserves a
# 6-dot pad, and the label's first ~5 mm is a feed dead zone, so 280 x 90 is
# printable. TiMini rotates it, so here the long axis is the image width.
S001 = Template("s001-12x40mm", 280, 90, 203, "Orgstra S001 / Xinye label")

# The common gap-label sizes for 384-dot 203 dpi heads (Phomemo M110 class and
# friends) — 48 mm printable, so a 50 mm label is clipped to 384 dots.
TEMPLATES = {
    t.key: t for t in (
        S001,
        Template("label-40x30mm", 320, 240, 203, "40 x 30 mm gap label"),
        Template("label-50x30mm", 384, 240, 203, "50 x 30 mm gap label (48 mm printable)"),
    )
}

# The template currently being drawn. Module-level so the drawing helpers stay
# small; use_template() rebinds it and the derived dot values.
TEMPLATE = S001
DPMM = TEMPLATE.dpmm
W, H = TEMPLATE.w, TEMPLATE.h
LEN_MM, HEAD_MM = TEMPLATE.size_mm


def mm(value: float) -> int:
    """Millimetres to whole dots."""
    return round(value * DPMM)


def use_template(template: Template) -> None:
    global TEMPLATE, DPMM, W, H, LEN_MM, HEAD_MM, PAD, BAND_TOP
    TEMPLATE, DPMM = template, template.dpmm
    W, H = template.w, template.h
    LEN_MM, HEAD_MM = template.size_mm
    PAD, BAND_TOP = mm(2.0), mm(3.75)


# Layout, in millimetres, so it holds at any resolution.
PAD = mm(2.0)          # left/right margin
BAND_TOP = mm(3.75)    # top of the drawing band, below the title row
NUT_CENTRE_FRAC = 1 / 3   # nut centre sits this far in from the right edge, as a
                          # fraction of the length: right-aligning put small nuts
                          # on the label's rounded corner

# ------------------------------------------------------------------- sizes ---

# Hex NUT width across flats (mm) — ISO 4032 / DIN 934.
WAF = {1: 2.5, 1.6: 3.2, 2: 4, 2.5: 5, 3: 5.5, 4: 7, 5: 8, 6: 10,
       8: 13, 10: 17, 12: 19, 14: 22, 16: 24, 20: 30}

# Hex BOLT head: width across flats (s) and head height (k), mm — ISO 4017/4014.
HEX_BOLT = {2: (4, 1.4), 2.5: (5, 1.7), 3: (5.5, 2.0), 4: (7, 2.8), 5: (8, 3.5),
            6: (10, 4.0), 8: (13, 5.3), 10: (17, 6.4), 12: (19, 7.5), 16: (24, 10.0)}

# A real nut's corners are chamfered: ISO 4032 gives the across-corners size e as
# ~1.1055 x the flats, where a sharp hexagon would be 1.1547 x. Drawing the
# chamfer (a 12-gon: six flats, six corner cuts) keeps the outline true in both
# directions instead of overhanging by 4% at the corners.
CHAMFER_RADIUS = 1.1088   # vertex distance, in units of half the flats
CHAMFER_ANGLE = 4.407     # vertex offset either side of each corner, degrees


def nut_waf(m: float) -> float:
    """Nut width across flats (mm), extrapolated for sizes outside the table."""
    return WAF.get(m, m * 1.6)


def bolt_head(m: float) -> tuple[float, float]:
    """Bolt head width across flats and height (mm)."""
    return HEX_BOLT.get(m, (m * 1.6, m * 0.7))


# -------------------------------------------------------------------- tags ---
# Tags come after the size, in any order: M5x30:pan:philips, M5:nylon, SX6x30:plug

# Head profile, side view. Alias -> canonical.
HEAD_SHAPES = {"hex": "hex", "bolt": "hex",
               "pan": "pan", "round": "pan", "dome": "pan", "button": "pan",
               "wall": "pan", "wallmount": "pan",
               "flat": "csk", "csk": "csk", "countersunk": "csk", "counter": "csk"}
# Drive recess icon. Alias -> canonical, which is also the draw_drive branch.
DRIVES = {"philips": "cross", "phillips": "cross", "ph": "cross", "cross": "cross",
          "pozi": "pozi", "pozidriv": "pozi", "pz": "pozi",
          "torx": "torx", "star": "torx", "tx": "torx", "t": "torx",
          "slot": "slot", "slotted": "slot", "sl": "slot",
          "square": "square", "robertson": "square", "sq": "square",
          "allen": "hex", "socket": "hex", "hexkey": "hex"}
NUT_TYPES = {"nylon": "nylon", "nyloc": "nylon", "nylock": "nylon",
             "lock": "nylon", "insert": "nylon"}
# Wall plugs aren't threaded, so their size needs no M and they get no drive icon.
PLUG_TYPES = {"plug", "plugs", "wallplug", "anchor", "dowel", "raw", "rawlplug"}


# ---------------------------------------------------------------- drawing ----

def _font(px: int) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "consolab.ttf", "seguisb.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _arc_pts(cx, cy, angles, r):
    """Points at the given angles (degrees) on a circle of radius r px."""
    return [(cx + r * math.cos(math.radians(a)), cy + r * math.sin(math.radians(a)))
            for a in angles]


def draw_nut(d: ImageDraw.ImageDraw, cx, cy, m, nylon=False):
    """Hex nut, face on, at true ISO size."""
    waf = nut_waf(m)
    corners = [60 * k + off for k in range(6)
               for off in (-CHAMFER_ANGLE, CHAMFER_ANGLE)]
    d.polygon(_arc_pts(cx, cy, corners, waf * DPMM / 2 * CHAMFER_RADIUS),
              outline=BLACK, width=2)

    hole_r = m * DPMM / 2
    d.ellipse([cx - hole_r, cy - hole_r, cx + hole_r, cy + hole_r],
              outline=BLACK, width=2)

    if nylon:
        # nyloc insert: a dotted ring between hole and hex, which reads as grey
        for x, y in _arc_pts(cx, cy, range(0, 360, 15), (m + waf) / 4 * DPMM):
            d.ellipse([x - 1, y - 1, x + 1, y + 1], fill=BLACK)


def draw_screw(d: ImageDraw.ImageDraw, x0, cy, m, length_mm, band_h, shape="hex"):
    """Screw side profile. The shaft is true scale (Ø = m, under-head length =
    length_mm) since that's the identifying dimension; the head is capped to the
    drawing band so it fits the tiny label. `shape` picks the head profile:

        hex - flat block (default)
        pan - rounded outer face, flat where the shaft meets it
        csk - flat outer face, tapering into the shaft (countersunk)
    """
    s, k = bolt_head(m)
    head_w = k * DPMM
    head_h = min(s * DPMM, band_h)
    shaft_h = min(m * DPMM, band_h - 4)
    shaft_len = length_mm * DPMM
    ht, hb = cy - head_h / 2, cy + head_h / 2          # head top/bottom
    st, sb = cy - shaft_h / 2, cy + shaft_h / 2        # shaft top/bottom

    if shape == "pan":
        d.rectangle([x0 + head_w / 2, ht, x0 + head_w, hb], fill=BLACK)
        d.pieslice([x0, ht, x0 + head_w, hb], 90, 270, fill=BLACK)
    elif shape == "csk":
        d.polygon([(x0, ht), (x0, hb), (x0 + head_w, sb), (x0 + head_w, st)], fill=BLACK)
    else:
        d.rectangle([x0, ht, x0 + head_w, hb], fill=BLACK)

    sx = x0 + head_w
    d.rectangle([sx, st, sx + shaft_len, sb], outline=BLACK, width=2)
    for x in range(int(sx) + 2, int(sx + shaft_len), 4):      # thread hatching
        d.line([x, st, x - 3, sb], fill=BLACK, width=1)


def draw_plug(d: ImageDraw.ImageDraw, x0, cy, dia_mm, length_mm, band_h):
    """Wall plug side profile: a collar at the wall face, a ribbed expansion
    sleeve and the expansion slot. Drawn like a screw shaft, with no head."""
    body_h = min(dia_mm * DPMM, band_h - 4)
    total = length_mm * DPMM               # the collar is part of it
    collar_w = 1.0 * DPMM                  # 1 mm lip
    collar_h = min(dia_mm * 1.3 * DPMM, band_h)
    top, bot = cy - body_h / 2, cy + body_h / 2

    d.rectangle([x0, cy - collar_h / 2, x0 + collar_w, cy + collar_h / 2], fill=BLACK)
    sx = x0 + collar_w
    d.rectangle([sx, top, x0 + total, bot], outline=BLACK, width=2)
    for x in range(int(sx) + 5, int(x0 + total) - 2, 5):   # anti-rotation ribs
        d.line([x, top + 1, x - 4, top + 4], fill=BLACK, width=1)
        d.line([x, bot - 1, x - 4, bot - 4], fill=BLACK, width=1)
    d.line([x0 + total * 0.35, cy, x0 + total - 3, cy], fill=BLACK, width=2)


def draw_drive(d: ImageDraw.ImageDraw, cx, cy, r, kind):
    """Screw head seen from above, showing its drive recess. An unrecognised
    drive falls through to a plain head circle."""
    icon = DRIVES.get(kind.lower())
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=2)   # rim
    ir = r - 4                                                           # recess

    if icon == "hex":
        d.polygon(_arc_pts(cx, cy, range(30, 360, 60), ir), outline=BLACK, width=2)
    elif icon in ("cross", "pozi"):
        d.line([cx - ir, cy, cx + ir, cy], fill=BLACK, width=3)
        d.line([cx, cy - ir, cx, cy + ir], fill=BLACK, width=3)
        if icon == "pozi":                       # cross plus finer diagonals
            h = ir * 0.7
            d.line([cx - h, cy - h, cx + h, cy + h], fill=BLACK, width=1)
            d.line([cx - h, cy + h, cx + h, cy - h], fill=BLACK, width=1)
    elif icon == "slot":
        d.line([cx - ir, cy, cx + ir, cy], fill=BLACK, width=3)
    elif icon == "torx":                         # solid 6-point star
        pts = [p for i in range(12)
               for p in _arc_pts(cx, cy, [i * 30 - 90], ir if i % 2 == 0 else ir * 0.5)]
        d.polygon(pts, fill=BLACK)
    elif icon == "square":
        h = ir * 0.8
        d.rectangle([cx - h, cy - h, cx + h, cy + h], outline=BLACK, width=2)


# ----------------------------------------------------------------- layout ----

def _fit_font(d: ImageDraw.ImageDraw, text: str, max_w: int, size_mm=5.0):
    """Largest font at or below `size_mm` tall that keeps `text` inside max_w."""
    size = mm(size_mm)
    floor = mm(2.0)
    while size > floor:
        font = _font(size)
        if d.textlength(text, font=font) <= max_w:
            return font
        size -= 1
    return _font(floor)


def _title_row(d: ImageDraw.ImageDraw, title: str, caption: str):
    """Big size followed by a small caption, pinned to the top-left."""
    f_big, f_sub = _font(mm(3.75)), _font(mm(2.25))
    d.text((PAD, -mm(0.25)), title, font=f_big, fill=BLACK)
    d.text((PAD + d.textlength(title, font=f_big) + mm(0.75), mm(0.5)),
           caption, font=f_sub, fill=BLACK)


def make_label(kind: str, m: float, length: float | None = None,
               shape: str = "hex", drive: str | None = None) -> Image.Image:
    img = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(img)

    if kind == "text":
        # a plain caption: same style as the nut title, centred since nothing
        # sits under it. Shrinks to fit rather than running off the label.
        font = _fit_font(d, shape, W - 2 * PAD)
        top, bottom = d.textbbox((0, 0), shape, font=font)[1::2]
        d.text((PAD, (H - (top + bottom)) // 2), shape, font=font, fill=BLACK)
        return img

    if kind == "nut":
        # size and variant stacked tight on the left, hex face on the right
        d.text((PAD, mm(0.125)), f"M{m:g}", font=_font(mm(5.0)), fill=BLACK)
        d.text((PAD, mm(5.375)), "Nylon" if shape == "nylon" else "Nuts",
               font=_font(mm(2.5)), fill=BLACK)
        draw_nut(d, int(W - NUT_CENTRE_FRAC * W), H // 2, m, nylon=(shape == "nylon"))
        return img

    # screws and plugs: title row on top, fastener centred in the band below
    band_cy, band_h = (BAND_TOP + H) // 2, H - BAND_TOP
    if kind == "plug":
        _title_row(d, f"{shape + ' ' if shape else ''}{m:g}x{length:g}", "Plugs")
        draw_plug(d, PAD, band_cy, m, length, band_h)
    else:
        _title_row(d, f"M{m:g}x{length:g}", "Screws")
        if drive:
            r = mm(1.625)
            draw_drive(d, W - PAD - r, mm(1.875), r, drive)   # top-right corner
        draw_screw(d, PAD, band_cy, m, length, band_h, shape)
    return img


def contact_sheet(specs, scale=3, out="preview.png"):
    """Stack the labels at `scale` x with captions, to eyeball a batch."""
    gap, cap_h = 10, 16
    cw, ch = W * scale, H * scale
    sheet = Image.new("RGB", (cw + 2 * gap, (ch + cap_h + gap) * len(specs) + gap), "white")
    dd = ImageDraw.Draw(sheet)
    f = _font(13)
    for i, spec in enumerate(specs):
        y = gap + i * (ch + cap_h + gap)
        big = make_label(*spec).convert("L").resize((cw, ch), Image.NEAREST).convert("RGB")
        sheet.paste(big, (gap, y))
        dd.rectangle([gap, y, gap + cw, y + ch], outline="#bbb")
        if spec[0] == "text":
            what = f"{spec[3]!r} text"
        elif spec[0] == "nut":
            what = f"{spec[1]:g} nut"
        else:
            what = f"{spec[1]:g}x{spec[2]:g} {spec[0]}"
        dd.text((gap, y + ch + 2),
                f"{what}  (printable {LEN_MM:.1f}x{HEAD_MM:.1f}mm @ {scale}x)",
                font=f, fill="black")
    sheet.save(out)
    return out


# ------------------------------------------------------------------ specs ----
# A spec is (kind, size, length, shape, drive). For plugs, `shape` carries the
# optional range prefix ("SX") rather than a head profile.

def parse_spec(token: str):
    """Parse one command-line size into a spec:

        M5                 nut
        M5:nylon           nyloc nut
        M5x30              screw
        M5x30:pan:philips  screw with a head profile and drive icon
        SX6x30:plug        wall plug, the letter prefix kept as the range name
        text:Misc          a plain caption, kept verbatim
    """
    head, sep, rest = token.partition(":")
    if head.strip().lower() == "text":
        return ("text", 0, None, rest.strip() or "Label", None)

    size, *tags = token.split(":")
    tags = [t.strip().lower() for t in tags]
    size = size.strip().upper()
    prefix = size[:len(size) - len(size.lstrip(ascii_uppercase))]    # 'M', 'SX', ''
    size = size[len(prefix):]

    if any(t in PLUG_TYPES for t in tags):
        dia, length = size.split("X", 1)
        return ("plug", float(dia), float(length), "" if prefix == "M" else prefix, None)

    if "X" not in size:
        shape = next((NUT_TYPES[t] for t in tags if t in NUT_TYPES), None)
        return ("nut", float(size), None, shape, None)

    dia, length = size.split("X", 1)
    shape = next((HEAD_SHAPES[t] for t in tags if t in HEAD_SHAPES), "hex")
    drive = next((t for t in tags if t in DRIVES), None)
    return ("screw", float(dia), float(length), shape, drive)


def spec_name(spec) -> str:
    """Output filename stem: lowercase, dash-separated. m4x20-screw-pan-philips"""
    kind, m, length, shape, drive = spec
    if kind == "text":
        slug = "".join(c if c.isalnum() else "-" for c in shape).strip("-")
        return f"{slug}-text".lower()
    if kind == "nut":
        parts = [f"m{m:g}", "nut", shape]
    elif kind == "plug":
        parts = [shape, f"{m:g}x{length:g}", "plug"]
    else:
        parts = [f"m{m:g}x{length:g}", "screw",
                 shape if shape != "hex" else None, drive]
    return "-".join(p for p in parts if p).lower()


def describe(spec) -> str:
    """One-line summary of what a spec draws, for the console readout."""
    kind, m, length, shape, drive = spec
    if kind == "text":
        return f"text label: {shape!r}"
    if kind == "nut":
        variant = " nyloc" if shape == "nylon" else ""
        return f"M{m:g}{variant} nut: hex WAF {nut_waf(m):g} mm, hole Ø{m:g} mm"
    if kind == "plug":
        return (f"{shape + ' ' if shape else ''}{m:g}x{length:g}: "
                f"wall plug, Ø{m:g}x{length:g} mm")
    s, k = bolt_head(m)
    extra = "".join(f", {t}" for t in (shape if shape != "hex" else None,
                                       f"{drive} drive" if drive else None) if t)
    return f"M{m:g}x{length:g}: shaft Ø{m:g}x{length:g} mm, head {s}x{k} mm{extra}"


def main(argv=None):
    import argparse
    import os

    p = argparse.ArgumentParser(
        description="Generate actual-size nut/bolt organisation stickers (PNG per size).")
    p.add_argument("sizes", nargs="*",
                   help="e.g. M3 M5 M8 M5x50 M4x20  (Mx = nut, MxL = screw)")
    p.add_argument("--out", default="out", help="output folder (default: ./out)")
    p.add_argument("--sheet", action="store_true", help="also write a _preview.png contact sheet")
    p.add_argument("--template", default=S001.key, choices=sorted(TEMPLATES),
                   help=f"label template (default: {S001.key})")
    args = p.parse_args(argv)
    use_template(TEMPLATES[args.template])

    tokens = args.sizes or ["M3", "M5", "M5:nylon", "M4x20:pan:philips",
                            "M4x20:csk:pozi", "M5x30:hex"]
    specs = [parse_spec(t) for t in tokens]
    os.makedirs(args.out, exist_ok=True)
    print(f"{TEMPLATE.key}: {TEMPLATE.dpi} dpi = {DPMM:.3f} dot/mm; "
          f"{LEN_MM:.1f}x{HEAD_MM:.1f} mm = {W}x{H} dots (1 px = 1 dot)")
    for spec in specs:
        name = spec_name(spec) + ".png"
        make_label(*spec).save(os.path.join(args.out, name))
        print(f"  {name:24} {describe(spec)}")
    if args.sheet:
        print("sheet:", contact_sheet(specs, out=os.path.join(args.out, "_preview.png")))


if __name__ == "__main__":
    main()
