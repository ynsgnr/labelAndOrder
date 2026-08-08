"""Generate actual-size nut / screw / wall-plug organisation stickers.

Sized for a 12 x 40 mm thermal label on the Orgstra S001: the printable area is
280 x 90 dots at 8 dot/mm, so a fastener is drawn 1 px per dot and comes off the
printer true to size. Anything bigger than the label runs off the edge and is cut.
"""
from __future__ import annotations
import math
from string import ascii_uppercase
from PIL import Image, ImageDraw, ImageFont

# ---------------------------------------------------------------- geometry ---

DPMM = 8                                 # print head resolution, dots per mm
W, H = 280, 90                           # printable label, length x head, in dots
BLACK, WHITE = 0, 1

# The paper advance runs slightly slower than the head, so the length axis is
# drawn at FEED_CAL x DPMM. Calibrated from two printed features that bracket the
# thermal bleed: a nut hole (inner edge, bleed shrinks it) drawn 67.4 px measured
# 8.4 mm, and a screw shaft (outer edge, bleed grows it) drawn 96 px measured
# 13.0 mm. To recalibrate, print a screw and measure the shaft:
#     FEED_CAL = nominal_mm / (measured_mm - LINE_BLEED / DPMM)
FEED_CAL = 0.95
FEED_DPMM = DPMM * FEED_CAL              # dots per mm along the label length
LEN_MM, HEAD_MM = W / FEED_DPMM, H / DPMM        # 36.8 x 11.25 mm printable

# A 2-px outline plus thermal bleed adds this much to any edge-measured size.
# Outer edges (shaft, hex flats) are drawn smaller by it, inner edges (the nut
# hole) larger, so both measure true on paper.
LINE_BLEED = 3

PAD = 2 * DPMM        # left/right margin
BOT = 8               # bottom breathing room; the protocol top-pad shifts
                      # everything down, so content this close would clip
BAND_TOP = 30         # top of the drawing band, below the title row
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

# A hex drawn to ISO reads larger than the real nut held against it: the outline
# sits outside the shape, thermal bleed thickens it, and the drawn corners are
# sharp where a real nut's are chamfered. Scaled down rather than offset by a
# fixed amount, which at M2 would leave the hex no bigger than its own hole.
# Anchored on M6 measured against real nuts: 10 mm flats drawn as 8.
NUT_SCALE = 0.8


def nut_waf(m: float) -> float:
    """Drawn nut width across flats (mm), extrapolated outside the table."""
    return WAF.get(m, m * 1.6) * NUT_SCALE


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


def _arc_pts(cx, cy, angles, rx, ry):
    """Points at the given angles (degrees) on an ellipse of radii rx, ry px.
    Round features use rx > ry so they print circular despite the slower feed."""
    return [(cx + rx * math.cos(math.radians(a)), cy + ry * math.sin(math.radians(a)))
            for a in angles]


def _mm_arc_pts(cx, cy, angles, r_mm):
    """As _arc_pts, but with the radius given in mm and scaled per axis."""
    return _arc_pts(cx, cy, angles, r_mm * FEED_DPMM, r_mm * DPMM)


def draw_nut(d: ImageDraw.ImageDraw, cx, cy, m, nylon=False):
    """Hex nut, face on. Hex and hole are both scaled by NUT_SCALE so the icon
    stays in proportion. The outline is an outer edge and the hole an inner one,
    so bleed is compensated in opposite directions."""
    waf, hole = nut_waf(m), m * NUT_SCALE
    circumradius = (waf - LINE_BLEED / DPMM) / 2 / math.cos(math.radians(30))
    d.polygon(_mm_arc_pts(cx, cy, range(0, 360, 60), circumradius), outline=BLACK, width=2)

    # Radii keep the FEED_DPMM:DPMM ratio so the hole prints round; the bleed
    # term is a dot-level effect and so is the same on both axes.
    rx = (hole / 2) * FEED_DPMM + LINE_BLEED / 2
    ry = (hole / 2) * DPMM + LINE_BLEED / 2
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=BLACK, width=2)

    if nylon:
        # nyloc insert: a dotted ring between hole and hex, which reads as grey
        for x, y in _mm_arc_pts(cx, cy, range(0, 360, 15), (hole / 2 + waf / 2) / 2):
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
    head_w = k * FEED_DPMM
    head_h = min(s * DPMM - LINE_BLEED, band_h)
    shaft_h = min(m * DPMM - LINE_BLEED, band_h - 4)
    shaft_len = length_mm * FEED_DPMM - LINE_BLEED
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
    body_h = min(dia_mm * DPMM - LINE_BLEED, band_h - 4)
    total = length_mm * FEED_DPMM - LINE_BLEED       # the collar is part of it
    collar_w = max(3.0, 1.0 * FEED_DPMM)             # ~1 mm lip
    collar_h = min(dia_mm * 1.3 * DPMM - LINE_BLEED, band_h)
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
        d.polygon(_arc_pts(cx, cy, range(30, 360, 60), ir, ir), outline=BLACK, width=2)
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
        pts = []
        for i in range(12):
            rr = ir if i % 2 == 0 else ir * 0.5
            pts += _arc_pts(cx, cy, [i * 30 - 90], rr, rr)
        d.polygon(pts, fill=BLACK)
    elif icon == "square":
        h = ir * 0.8
        d.rectangle([cx - h, cy - h, cx + h, cy + h], outline=BLACK, width=2)


# ----------------------------------------------------------------- layout ----

def _title_row(d: ImageDraw.ImageDraw, title: str, caption: str):
    """Big size followed by a small caption, pinned to the top-left."""
    f_big, f_sub = _font(30), _font(18)
    d.text((PAD, -2), title, font=f_big, fill=BLACK)
    d.text((PAD + d.textlength(title, font=f_big) + 6, 4), caption, font=f_sub, fill=BLACK)


def make_label(kind: str, m: float, length: float | None = None,
               shape: str = "hex", drive: str | None = None) -> Image.Image:
    img = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    cy = (H - BOT) // 2

    if kind == "nut":
        # size and variant stacked tight on the left, hex face on the right
        d.text((PAD, 1), f"M{m:g}", font=_font(40), fill=BLACK)
        d.text((PAD, 43), "Nylon" if shape == "nylon" else "Nuts",
               font=_font(20), fill=BLACK)
        draw_nut(d, int(W - NUT_CENTRE_FRAC * W), cy, m, nylon=(shape == "nylon"))
        return img

    # screws and plugs: title row on top, fastener centred in the band below
    band_cy, band_h = (BAND_TOP + H - BOT) // 2, H - BOT - BAND_TOP
    if kind == "plug":
        _title_row(d, f"{shape + ' ' if shape else ''}{m:g}x{length:g}", "Plugs")
        draw_plug(d, PAD, band_cy, m, length, band_h)
    else:
        _title_row(d, f"M{m:g}x{length:g}", "Screws")
        if drive:
            draw_drive(d, W - PAD - 13, 15, 13, drive)     # top-right corner
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
        what = "nut" if spec[0] == "nut" else f"x{spec[2]:g} {spec[0]}"
        dd.text((gap, y + ch + 2),
                f"{spec[1]:g} {what}  (printable {LEN_MM:g}x{HEAD_MM:g}mm @ {scale}x)",
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
    """
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
    """Output filename stem for a spec."""
    kind, m, length, shape, drive = spec
    if kind == "nut":
        return f"M{m:g}_nut" + (f"_{shape}" if shape else "")
    if kind == "plug":
        return f"{shape + '_' if shape else ''}{m:g}x{length:g}_plug"
    tags = "".join(f"_{t}" for t in (shape if shape != "hex" else None, drive) if t)
    return f"M{m:g}x{length:g}_screw{tags}"


def describe(spec) -> str:
    """One-line summary of what a spec draws, for the console readout."""
    kind, m, length, shape, drive = spec
    if kind == "nut":
        variant = " nyloc" if shape == "nylon" else ""
        # the real nut being labelled, not the NUT_SCALE-reduced drawing
        return (f"M{m:g}{variant} nut: hex WAF {WAF.get(m, m * 1.6):g} mm, "
                f"hole Ø{m:g} mm, drawn at {NUT_SCALE:g}x")
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
    args = p.parse_args(argv)

    tokens = args.sizes or ["M3", "M5", "M5:nylon", "M4x20:pan:philips",
                            "M4x20:csk:pozi", "M5x30:hex"]
    specs = [parse_spec(t) for t in tokens]
    os.makedirs(args.out, exist_ok=True)
    print(f"scale = {DPMM} dot/mm; printable {LEN_MM:g}x{HEAD_MM:g} mm = "
          f"{W}x{H} dots (1 px = 1 dot)")
    for spec in specs:
        name = spec_name(spec) + ".png"
        make_label(*spec).save(os.path.join(args.out, name))
        print(f"  {name:24} {describe(spec)}")
    if args.sheet:
        print("sheet:", contact_sheet(specs, out=os.path.join(args.out, "_preview.png")))


if __name__ == "__main__":
    main()
