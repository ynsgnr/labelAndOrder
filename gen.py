"""Generate M-size nut/bolt organisation stickers for the Orgstra S001 label.

Label: 12 mm x 40 mm printed at 8 dot/mm (96 x 320 px). Fasteners are drawn to
ACTUAL SIZE; anything larger than the sticker runs off the edge and is cut.
"""
from __future__ import annotations
import math
from string import ascii_uppercase
from PIL import Image, ImageDraw, ImageFont

DPMM = 8
# Generate at the S001 PRINTABLE render size so TiMini's scale-to-label is a
# no-op and the fastener prints at true size. Head loses 6 dots to the protocol
# top pad (90 of 96), length loses the ~5 mm leading dead-zone (280 of 320).
W, H = 280, 90                           # length x head, in dots
BLACK, WHITE = 0, 1

# Length-axis (paper advance) pitch relative to the head's 8 dot/mm. Measured on
# an S001 by printing a nut and measuring its hole, which is drawn as a true
# circle: 9.8 mm across the head axis vs 8.4 mm along the feed — i.e. the feed
# also runs at ~8 dot/mm and needs no correction. Lower this if your printer
# feeds long (a feature comes out longer than drawn), raise it if it feeds short.
FEED_CAL = 1.0
FEED_DPMM = DPMM * FEED_CAL               # dots per mm along the label length
LEN_MM, HEAD_MM = W / FEED_DPMM, H / DPMM  # ~41.5 x 11.25 mm printable

LINE_BLEED = 3   # px the 2-px outline + thermal bleed adds to an edge-measured size

# Hex NUT width across flats (mm) — ISO 4032 / DIN 934.
WAF = {1: 2.5, 1.6: 3.2, 2: 4, 2.5: 5, 3: 5.5, 4: 7, 5: 8, 6: 10,
       8: 13, 10: 17, 12: 19, 14: 22, 16: 24, 20: 30}

# Hex BOLT head: width across flats (s) and head height (k), mm — ISO 4017/4014.
HEX_BOLT = {
    2: (4, 1.4), 2.5: (5, 1.7), 3: (5.5, 2.0), 4: (7, 2.8), 5: (8, 3.5),
    6: (10, 4.0), 8: (13, 5.3), 10: (17, 6.4), 12: (19, 7.5), 16: (24, 10.0),
}

# Head profile (side view) and drive icon are given after the size as :tags,
# e.g. M5x30:pan:philips . Names map to a canonical value.
HEAD_SHAPES = {"hex": "hex", "bolt": "hex",
               "pan": "pan", "round": "pan", "dome": "pan", "button": "pan",
               "wall": "pan", "wallmount": "pan",
               "flat": "csk", "csk": "csk", "countersunk": "csk", "counter": "csk"}
DRIVES = {"philips", "phillips", "ph", "cross", "pozi", "pozidriv", "pz",
          "torx", "star", "tx", "t", "slot", "slotted", "sl",
          "square", "robertson", "sq", "allen", "socket", "hexkey"}
# Nut variants (tag after the size, e.g. M5:nylon).
NUT_TYPES = {"nylon": "nylon", "nyloc": "nylon", "nylock": "nylon",
             "lock": "nylon", "insert": "nylon"}
# Wall plugs / anchors (tag after the size, e.g. SX6x30:plug). Not threaded, so
# the size is a plain Ø x length with no M prefix and no drive icon.
PLUG_TYPES = {"plug", "plugs", "wallplug", "anchor", "dowel", "raw", "rawlplug"}


def _font(px: int) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "consolab.ttf", "seguisb.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_points(cx, cy, waf_mm):
    """Hexagon vertices for a given width across flats (mm). Length axis (x) uses
    FEED_DPMM so the print comes out regular; head axis (y) uses DPMM."""
    R = (waf_mm / 2) / math.cos(math.radians(30))   # circumradius, mm
    return [
        (cx + R * math.cos(math.radians(a)) * FEED_DPMM,
         cy + R * math.sin(math.radians(a)) * DPMM)
        for a in range(0, 360, 60)
    ]


NUT_SHRINK_MM = 1.0   # draw the hex 1 mm under WAF so the thin line traces the nut edge
NUT_CENTRE_FRAC = 1 / 3   # nut centre sits this fraction of the length in from the right

def draw_nut(d: ImageDraw.ImageDraw, cx, cy, m, nylon=False):
    waf = WAF.get(m, m * 1.6) - NUT_SHRINK_MM
    d.polygon(_hex_points(cx, cy, waf), outline=BLACK, width=2)
    rx, ry = (m / 2) * FEED_DPMM, (m / 2) * DPMM     # hole (round when printed)
    d.ellipse([cx - rx, cy - ry, cx + rx, cy + ry], outline=BLACK, width=2)
    if nylon:
        # nyloc insert: a dotted ring (reads 'grey' on B/W) between hole and hex
        rmm = (m / 2 + waf / 2) / 2
        nrx, nry = rmm * FEED_DPMM, rmm * DPMM
        for i in range(24):
            a = math.radians(i * 15)
            dx, dy = cx + nrx * math.cos(a), cy + nry * math.sin(a)
            d.ellipse([dx - 1, dy - 1, dx + 1, dy + 1], fill=BLACK)


def draw_screw(d: ImageDraw.ImageDraw, x0, cy, m, length_mm, band_h, shape="hex"):
    """Screw side profile: SHAFT is true scale (Ø = m, under-head length =
    length_mm) since that's the identifying dimension; the head is capped to the
    text-free band so it fits the tiny label. Length past the edge clips (cut).
    Length dims use FEED_DPMM (feed calibration); head dims use DPMM.

    ``shape`` picks the head profile (head grows the OTHER way from the shaft):
      hex  - flat block (default)      pan  - rounded outer face, flat at the shaft
      csk  - flat outer face, angled taper into the shaft (countersunk)
    """
    s, k = HEX_BOLT.get(m, (m * 1.6, m * 0.7))
    head_w = k * FEED_DPMM                      # head height along the (length) axis
    head_h = min(s * DPMM - LINE_BLEED, band_h)  # head across flats (bleed-compensated)
    # Shaft Ø is measured outer-to-outer, so subtract the outline+bleed (~0.4 mm)
    # so the printed diameter equals the true m mm.
    shaft_h = min(m * DPMM - LINE_BLEED, band_h - 4)
    shaft_len = length_mm * FEED_DPMM
    ht, hb = cy - head_h / 2, cy + head_h / 2
    st, sb = cy - shaft_h / 2, cy + shaft_h / 2
    if shape == "pan":
        d.rectangle([x0 + head_w / 2, ht, x0 + head_w, hb], fill=BLACK)   # flat shaft side
        d.pieslice([x0, ht, x0 + head_w, hb], 90, 270, fill=BLACK)        # rounded outer
    elif shape == "csk":
        d.polygon([(x0, ht), (x0, hb), (x0 + head_w, sb), (x0 + head_w, st)], fill=BLACK)
    else:  # hex bolt
        d.rectangle([x0, ht, x0 + head_w, hb], fill=BLACK)
    sx = x0 + head_w
    top, bot = st, sb
    d.rectangle([sx, top, sx + shaft_len, bot], outline=BLACK, width=2)
    for x in range(int(sx) + 2, int(sx + shaft_len), 4):   # thread hatching
        d.line([x, top, x - 3, bot], fill=BLACK, width=1)


def draw_plug(d: ImageDraw.ImageDraw, x0, cy, dia_mm, length_mm, band_h):
    """Wall-plug side profile, drawn like a screw shaft but with no head/drive:
    a collar (wall-face lip), a ribbed expansion sleeve and the expansion slot.
    Ø and length are true scale — length uses FEED_DPMM, the section uses DPMM."""
    body_h = min(dia_mm * DPMM - LINE_BLEED, band_h - 4)
    total = length_mm * FEED_DPMM                    # collar is part of the length
    collar_w = max(3.0, 1.0 * FEED_DPMM)             # ~1 mm lip
    collar_h = min(dia_mm * 1.3 * DPMM - LINE_BLEED, band_h)
    top, bot = cy - body_h / 2, cy + body_h / 2
    d.rectangle([x0, cy - collar_h / 2, x0 + collar_w, cy + collar_h / 2], fill=BLACK)
    sx = x0 + collar_w
    d.rectangle([sx, top, x0 + total, bot], outline=BLACK, width=2)
    # anti-rotation ribs biting back toward the collar, top and bottom edges
    for x in range(int(sx) + 5, int(x0 + total) - 2, 5):
        d.line([x, top + 1, x - 4, top + 4], fill=BLACK, width=1)
        d.line([x, bot - 1, x - 4, bot - 4], fill=BLACK, width=1)
    # expansion slot, open from the deep end
    d.line([x0 + total * 0.35, cy, x0 + total - 3, cy], fill=BLACK, width=2)


def draw_drive(d: ImageDraw.ImageDraw, cx, cy, r, kind):
    """Small screw-head top-view showing the drive type, centred at (cx, cy)."""
    kind = kind.lower()
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=BLACK, width=2)   # head rim
    ir = r - 4                                                            # recess radius

    def poly(angles, rr=ir, w=2):
        d.polygon([(cx + rr * math.cos(math.radians(a)), cy + rr * math.sin(math.radians(a)))
                   for a in angles], outline=BLACK, width=w)

    if kind in ("hex", "allen", "socket"):
        poly(range(30, 360, 60))                       # hexagon recess (point up)
    elif kind in ("phillips", "philips", "ph", "cross"):
        d.line([cx - ir, cy, cx + ir, cy], fill=BLACK, width=3)
        d.line([cx, cy - ir, cx, cy + ir], fill=BLACK, width=3)
    elif kind in ("pozi", "pozidriv", "pz"):
        d.line([cx - ir, cy, cx + ir, cy], fill=BLACK, width=3)
        d.line([cx, cy - ir, cx, cy + ir], fill=BLACK, width=3)
        h = ir * 0.7
        d.line([cx - h, cy - h, cx + h, cy + h], fill=BLACK, width=1)
        d.line([cx - h, cy + h, cx + h, cy - h], fill=BLACK, width=1)
    elif kind in ("slot", "slotted", "flat", "sl"):
        d.line([cx - ir, cy, cx + ir, cy], fill=BLACK, width=3)
    elif kind in ("torx", "star", "tx", "t"):
        pts = [(cx + (ir if i % 2 == 0 else ir * 0.5) * math.cos(math.radians(i * 30 - 90)),
                cy + (ir if i % 2 == 0 else ir * 0.5) * math.sin(math.radians(i * 30 - 90)))
               for i in range(12)]
        d.polygon(pts, fill=BLACK)                      # solid 6-point star
    elif kind in ("square", "robertson", "sq"):
        h = ir * 0.8
        d.rectangle([cx - h, cy - h, cx + h, cy + h], outline=BLACK, width=2)
    # unknown/other -> plain head circle


def make_label(kind: str, m: float, length: float | None = None,
               shape: str = "hex", drive: str | None = None) -> Image.Image:
    img = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    pad = 2 * DPMM

    bot = 8   # keep content off the bottom head edge (the protocol top-pad
              # shifts everything down, so leave breathing room to avoid clipping)
    cy = (H - bot) // 2

    if kind == "nut":
        # title + subtitle stacked tight on the LEFT, hex icon on the RIGHT
        f_big, f_sub = _font(40), _font(20)
        d.text((pad, 1), f"M{m:g}", font=f_big, fill=BLACK)
        d.text((pad, 43), "Nylon" if shape == "nylon" else "Nuts", font=f_sub, fill=BLACK)
        # Nut centred a third of the label length in from the right edge: small
        # nuts sat against the edge when right-aligned, which put them on the
        # sticker's rounded corner and made them awkward to compare against a
        # real nut. Big nuts still overhang symmetrically from here.
        cx = int(W - NUT_CENTRE_FRAC * W)
        draw_nut(d, cx, cy, m, nylon=(shape == "nylon"))
    elif kind == "plug":
        # same layout as a screw; `shape` carries an optional range prefix (SX, UX…)
        f_big, f_sub = _font(30), _font(18)
        title = f"{shape + ' ' if shape else ''}{m:g}x{length:g}"
        d.text((pad, -2), title, font=f_big, fill=BLACK)
        tw = d.textlength(title, font=f_big)
        d.text((pad + tw + 6, 4), "Plugs", font=f_sub, fill=BLACK)
        band_top, band_bot = 30, H - bot
        draw_plug(d, pad, (band_top + band_bot) // 2, m, length, band_bot - band_top)
    else:
        # title + "Screws" pinned to the top; screw centred in the band below it,
        # drive-type icon in the top-right corner
        f_big, f_sub = _font(30), _font(18)
        title = f"M{m:g}x{length:g}"
        d.text((pad, -2), title, font=f_big, fill=BLACK)
        tw = d.textlength(title, font=f_big)
        d.text((pad + tw + 6, 4), "Screws", font=f_sub, fill=BLACK)
        if drive:
            draw_drive(d, W - pad - 13, 15, 13, drive)   # top-right corner
        band_top, band_bot = 30, H - bot
        draw_screw(d, pad, (band_top + band_bot) // 2, m, length, band_bot - band_top, shape)
    return img


def contact_sheet(specs, scale=3, out="preview.png"):
    labels = [(s, make_label(*s)) for s in specs]
    gap = 10
    cap_h = 16
    cw, ch = W * scale, H * scale
    sheet = Image.new("RGB", (cw + 2 * gap, (ch + cap_h + gap) * len(labels) + gap), "white")
    dd = ImageDraw.Draw(sheet)
    f = _font(13)
    y = gap
    for (spec, im) in labels:
        big = im.convert("L").resize((cw, ch), Image.NEAREST).convert("RGB")
        sheet.paste(big, (gap, y))
        dd.rectangle([gap, y, gap + cw, y + ch], outline="#bbb")
        what = "nut" if spec[0] == "nut" else f"x{spec[2]:g} {spec[0]}"
        name = f"{spec[1]:g} {what}  (printable {LEN_MM:g}x{HEAD_MM:g}mm @ {scale}x)"
        dd.text((gap, y + ch + 2), name, font=f, fill="black")
        y += ch + cap_h + gap
    sheet.save(out)
    return out


def parse_spec(token: str):
    """'M5' -> nut; 'M5:nylon' -> nyloc nut; 'M5x30:pan:philips' -> screw with
    head profile + drive icon; 'SX6x30:plug' -> wall plug (any letter prefix is
    kept as the range name). Tags after the size (any order): for screws a head
    shape (pan/csk/hex) and/or drive (philips/pozi/torx/slot/square/allen); for
    nuts a variant (nylon); 'plug' switches the whole label to a wall plug."""
    parts = token.split(":")
    tags = [t.strip().lower() for t in parts[1:]]
    t = parts[0].strip().upper()
    prefix = t[:len(t) - len(t.lstrip(ascii_uppercase))]   # 'M', 'SX', '' …
    t = t[len(prefix):]
    if any(tag in PLUG_TYPES for tag in tags):
        dia, length = t.split("X", 1)
        return ("plug", float(dia), float(length),
                "" if prefix == "M" else prefix, None)
    is_screw = "X" in t
    shape = "hex" if is_screw else None
    drive = None
    for tag in tags:
        if is_screw and tag in HEAD_SHAPES:
            shape = HEAD_SHAPES[tag]
        elif is_screw and tag in DRIVES:
            drive = tag
        elif not is_screw and tag in NUT_TYPES:
            shape = NUT_TYPES[tag]
    if is_screw:
        d, length = t.split("X", 1)
        return ("screw", float(d), float(length), shape, drive)
    return ("nut", float(t), None, shape, None)


def spec_name(spec) -> str:
    kind, m, length, shape, drive = spec
    if kind == "nut":
        return f"M{m:g}_nut" + (f"_{shape}" if shape else "")
    if kind == "plug":
        return f"{shape + '_' if shape else ''}{m:g}x{length:g}_plug"
    tags = "".join(f"_{t}" for t in (shape if shape != "hex" else None, drive) if t)
    return f"M{m:g}x{length:g}_screw{tags}"


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

    tokens = args.sizes or ["M3", "M5", "M5:nylon", "M4x20:pan:philips", "M4x20:csk:pozi", "M5x30:hex"]
    specs = [parse_spec(t) for t in tokens]
    os.makedirs(args.out, exist_ok=True)
    print(f"scale = {DPMM} dot/mm; printable {LEN_MM:g}x{HEAD_MM:g} mm = {W}x{H} dots (1 px = 1 dot)")
    for spec in specs:
        img = make_label(*spec)
        path = os.path.join(args.out, spec_name(spec) + ".png")
        img.save(path)
        kind, m, length, shape, drive = spec
        if kind == "nut":
            variant = " nyloc" if shape == "nylon" else ""
            print(f"  {os.path.basename(path):24} M{m:g}{variant} nut: hex WAF {WAF[m]} mm, hole Ø{m:g} mm")
        elif kind == "plug":
            print(f"  {os.path.basename(path):24} {shape + ' ' if shape else ''}"
                  f"{m:g}x{length:g}: wall plug, Ø{m:g}x{length:g} mm")
        else:
            s, k = HEX_BOLT[m]
            extra = "".join(f", {t}" for t in (shape if shape != 'hex' else None,
                                               f"{drive} drive" if drive else None) if t)
            print(f"  {os.path.basename(path):24} M{m:g}x{length:g}: shaft Ø{m:g}x{length:g} mm, "
                  f"head {s}x{k} mm{extra}")
    if args.sheet:
        print("sheet:", contact_sheet(specs, out=os.path.join(args.out, "_preview.png")))


if __name__ == "__main__":
    main()
