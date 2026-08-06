"""Generate M-size nut/bolt organisation stickers for the Orgstra S001 label.

Label: 12 mm x 40 mm printed at 8 dot/mm (96 x 320 px). Fasteners are drawn to
ACTUAL SIZE; anything larger than the sticker runs off the edge and is cut.
"""
from __future__ import annotations
import math
from PIL import Image, ImageDraw, ImageFont

DPMM = 8
# Generate at the S001 PRINTABLE render size so TiMini's scale-to-label is a
# no-op and the fastener prints at true size. Head loses 6 dots to the protocol
# top pad (90 of 96), length loses the ~5 mm leading dead-zone (280 of 320).
W, H = 280, 90                           # length x head, in dots @ 8 dot/mm
LEN_MM, HEAD_MM = W / DPMM, H / DPMM      # 35.0 x 11.25 mm printable
BLACK, WHITE = 0, 1

# Hex NUT width across flats (mm) — ISO 4032 / DIN 934.
WAF = {1: 2.5, 1.6: 3.2, 2: 4, 2.5: 5, 3: 5.5, 4: 7, 5: 8, 6: 10,
       8: 13, 10: 17, 12: 19, 14: 22, 16: 24, 20: 30}

# Hex BOLT head: width across flats (s) and head height (k), mm — ISO 4017/4014.
HEX_BOLT = {
    2: (4, 1.4), 2.5: (5, 1.7), 3: (5.5, 2.0), 4: (7, 2.8), 5: (8, 3.5),
    6: (10, 4.0), 8: (13, 5.3), 10: (17, 6.4), 12: (19, 7.5), 16: (24, 10.0),
}


def _font(px: int) -> ImageFont.FreeTypeFont:
    for name in ("arialbd.ttf", "consolab.ttf", "seguisb.ttf", "arial.ttf"):
        try:
            return ImageFont.truetype(name, px)
        except OSError:
            continue
    return ImageFont.load_default()


def _hex_points(cx, cy, waf_mm):
    """Flat-top hexagon vertices for a given width across flats (mm)."""
    circum = (waf_mm / 2) / math.cos(math.radians(30)) * DPMM
    return [
        (cx + circum * math.cos(math.radians(a)), cy + circum * math.sin(math.radians(a)))
        for a in range(0, 360, 60)
    ]


def draw_nut(d: ImageDraw.ImageDraw, cx, cy, m):
    waf = WAF.get(m, m * 1.6)
    d.polygon(_hex_points(cx, cy, waf), outline=BLACK, width=3)
    hr = (m / 2) * DPMM
    d.ellipse([cx - hr, cy - hr, cx + hr, cy + hr], outline=BLACK, width=2)


def draw_screw(d: ImageDraw.ImageDraw, x0, cy, m, length_mm):
    """Hex-bolt side profile at TRUE scale (8 dot/mm): head height k x width s,
    threaded shaft diameter d = m, under-head length = length_mm. Nothing is
    scaled to fit — anything past the label edge simply clips (cut)."""
    s, k = HEX_BOLT.get(m, (m * 1.6, m * 0.7))
    head_w = k * DPMM                       # head height along the axis
    head_h = s * DPMM                        # head width across flats
    shaft_h = m * DPMM                       # thread major diameter
    shaft_len = length_mm * DPMM
    d.rectangle([x0, cy - head_h / 2, x0 + head_w, cy + head_h / 2], fill=BLACK)
    sx = x0 + head_w
    top, bot = cy - shaft_h / 2, cy + shaft_h / 2
    d.rectangle([sx, top, sx + shaft_len, bot], outline=BLACK, width=2)
    for x in range(int(sx) + 2, int(sx + shaft_len), 4):   # thread hatching
        d.line([x, top, x - 3, bot], fill=BLACK, width=1)


def make_label(kind: str, m: float, length: float | None = None) -> Image.Image:
    img = Image.new("1", (W, H), WHITE)
    d = ImageDraw.Draw(img)
    pad = 2 * DPMM

    if kind == "nut":
        # big title + subtitle on the left, hex icon actual-size on the right
        f_big, f_sub = _font(42), _font(22)
        title, sub = f"M{m:g}", "Nuts"
        d.text((pad, 2), title, font=f_big, fill=BLACK)
        d.text((pad, 58), sub, font=f_sub, fill=BLACK)
        text_w = int(max(d.textlength(title, font=f_big), d.textlength(sub, font=f_sub)))
        waf = WAF.get(m, m * 1.6)
        draw_nut(d, pad + text_w + 3 * DPMM + int(waf / 2 * DPMM), H // 2, m)
    else:
        # text row on top, to-scale screw drawn from the left edge below it
        f_big, f_sub = _font(32), _font(18)
        title = f"M{m:g}x{length:g}"
        d.text((pad, -2), title, font=f_big, fill=BLACK)
        tw = d.textlength(title, font=f_big)
        d.text((pad + tw + 6, 6), "Screws", font=f_sub, fill=BLACK)
        # screw centred low so the (true-scale) head clears the text for common sizes
        draw_screw(d, pad, 62, m, length)
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
        name = f"{spec[1]} {'nut' if spec[0]=='nut' else 'x'+str(spec[2])+' screw'}  (printable {LEN_MM:g}x{HEAD_MM:g}mm @ {scale}x)"
        dd.text((gap, y + ch + 2), name, font=f, fill="black")
        y += ch + cap_h + gap
    sheet.save(out)
    return out


def parse_spec(token: str):
    """'M5' -> ('nut', 5, None); 'M5x50' -> ('screw', 5, 50)."""
    t = token.strip().upper().lstrip("M")
    if "X" in t:
        d, length = t.split("X", 1)
        return ("screw", float(d), float(length))
    return ("nut", float(t), None)


def spec_name(spec) -> str:
    kind, m, length = spec
    return f"M{m:g}_nut" if kind == "nut" else f"M{m:g}x{length:g}_screw"


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

    tokens = args.sizes or ["M3", "M5", "M8", "M3x10", "M4x20", "M5x50"]
    specs = [parse_spec(t) for t in tokens]
    os.makedirs(args.out, exist_ok=True)
    print(f"scale = {DPMM} dot/mm; printable {LEN_MM:g}x{HEAD_MM:g} mm = {W}x{H} dots (1 px = 1 dot)")
    for spec in specs:
        img = make_label(*spec)
        path = os.path.join(args.out, spec_name(spec) + ".png")
        img.save(path)
        kind, m, length = spec
        if kind == "nut":
            print(f"  {os.path.basename(path):16} M{m:g} nut: hex WAF {WAF[m]} mm, hole Ø{m:g} mm")
        else:
            s, k = HEX_BOLT[m]
            print(f"  {os.path.basename(path):16} M{m:g}x{length:g}: shaft Ø{m:g}x{length:g} mm, head {s}x{k} mm")
    if args.sheet:
        print("sheet:", contact_sheet(specs, out=os.path.join(args.out, "_preview.png")))


if __name__ == "__main__":
    main()
