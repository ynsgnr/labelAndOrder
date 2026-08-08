# Label & Order

Actual-size nut & bolt organisation labels for thermal label printers.

Generate crisp **M-size fastener stickers** where the nut/screw is drawn to **true
scale** — hold a real M5 nut against the "M5 Nuts" label and it matches. Print them
on an Orgstra **S001** (Xinye) label printer via
[TiMini-Print](https://github.com/ynsgnr/TiMini-Print).

![examples](examples/preview.png)

> **Other printers:** the only printer-specific values are the head resolution
> (`DPMM`) and the printable area (`W`, `H`) at the top of `gen.py` — both of which
> TiMini already knows per model. Set those and the drawings are correct; there are
> no calibration constants to tune. The layout and font sizes are eyeballed for a
> 90-dot-tall label, so a very different label shape would want those adjusted too.

## Just print them

The whole catalogue is **pre-generated and committed** — clone and print, no Python
needed. One folder per label template, 674 stickers each:

| Folder | Label | Dots | Printers |
|---|---|---|---|
| `s001-12x40mm/` | 12 × 40 mm | 280 × 90 @ 203 dpi | Orgstra S001 / Xinye |
| `label-40x30mm/` | 40 × 30 mm | 320 × 240 @ 203 dpi | Phomemo M110 class and friends |
| `label-50x30mm/` | 50 × 30 mm | 384 × 240 @ 203 dpi | same, 48 mm printable |

```
s001-12x40mm/m4x20-screw-pan-philips.png
label-40x30mm/m5-nut-nylon.png
label-50x30mm/sx-6x30-plug.png
```

Each folder has a `preview.png` contact sheet of the same examples shown above.
Rebuild the lot with `uv run build_catalog.py --clean`.

## What it does

- **`gen.py`** — generates one PNG per size. Nuts are drawn by ISO hex
  width-across-flats, screws and wall plugs by real Ø × length. Optional head
  shapes, drive icons, a nyloc variant and a plug kind. Anything larger than the
  label runs off the edge and gets cut — by design. `--template` picks the label.
- **`build_catalog.py`** — regenerates every folder above.
- **`print.py`** — prints a folder of stickers on the S001 through the TiMini CLI,
  one at a time, waiting for you between each.

Both axes print at **8 dot/mm**, so a sticker is drawn 1 px per dot at nominal ISO
size and the unused label length is left white. No scaling, no fudge factors — if a
print measures wrong, something upstream is rescaling it:

> **Margin trimming must be off.** TiMini trims white margins by default and scales
> what's left to fill the label — a different factor for every sticker, since each
> has a different amount of white. That silently destroys true-size printing.
> `print.py` passes `--no-trim-side-margins --no-trim-top-bottom-margins`; if you
> print these PNGs by any other route, pass them yourself.

## Install

Using [uv](https://docs.astral.sh/uv/):

```
uv sync
```

or plain pip:

```
python -m venv .venv
.venv\Scripts\activate        # Windows  (source .venv/bin/activate on macOS/Linux)
pip install -r requirements.txt
```

## Generate stickers

```
uv run gen.py M3 M5 M8 M5x50 M4x20 --out out --sheet
```

- `M5` → nut, `M5x50` → screw (Ø5 × 50 mm). Decimals are fine: `M2.5`.
- `SX6x30:plug` → wall plug (Ø6 × 30 mm). Plugs aren't threaded, so the size
  needs no `M`; any letter prefix is kept as the range name (`SX 6x30`).
- PNGs are written to `out/` (`M5_nut.png`, `M5x50_screw.png`, `SX_6x30_plug.png`).
- `--sheet` also writes `_preview.png` so you can eyeball the batch.
- `--template label-40x30mm` draws for a different label (default is the S001).

**Tags** — add `:tag` after the size (any order) to vary the drawing:

| Tag | Applies to | Effect |
|-----|-----------|--------|
| `nylon` (`nyloc`, `lock`) | nut | dotted insert ring, labelled "Nylon" |
| `pan` (`round`, `dome`, `wall`) | screw | rounded outer head face |
| `csk` (`flat`, `countersunk`) | screw | flat face, countersunk taper into the shaft |
| `hex` (default) | screw | flat hex-bolt head block |
| `philips` `pozi` `torx` `slot` `square` `allen` | screw | drive icon in the top-right |
| `plug` (`anchor`, `dowel`, `wallplug`) | — | draws a wall plug instead: collar, ribbed sleeve, expansion slot, no drive icon |

Examples: `M5:nylon` · `M4x20:pan:philips` · `M5x30:csk:pozi` · `M3x8:torx` · `SX6x30:plug`

## Print

Printing depends on **[TiMini-Print](https://github.com/ynsgnr/TiMini-Print)**, the
S001 label-printer driver. Clone it, then point `--timini` (or the `TIMINI_DIR`
env var) at your checkout:

```
uv run print.py s001-12x40mm --serial COM5 --timini ../TiMini-Print
```

- Prompts before **each** sticker: Enter prints it, a number prints that many
  copies of it, `s` skips it, `q` stops — so you can check the last label and
  reposition the roll between prints.
- `--count N` prints N copies of every sticker (default 1) — `--count 3` for a
  drawer that needs three of each.
- The S001 drops its SPP port after every job and needs a moment before it accepts
  the next, so consecutive prints are spaced by `--delay` seconds (default 2).
  A job that still fails is offered for retry — it won't abort the batch.
- `--yes` print all without prompting · `--test` first only · `--rest` skip the first.
- `--paper tag_90r_90p` is the **1:1 preset** (render 90 / length 280) — keep it so
  the fastener prints at true size.

The S001 must be paired and exposed as a serial/SPP COM port (see the TiMini-Print
README for pairing).

## Accuracy

| Item | Standard |
|------|----------|
| Nut hex width-across-flats | ISO 4032 (M3 = 5.5, M4 = 7, M5 = 8, M6 = 10, M8 = 13 mm …) |
| Nut across-corners | ISO 4032 `e` — the corners are chamfered, not sharp |
| Bolt head (WAF × height) | ISO 4017 |
| Shaft Ø | nominal M-size |
| Shaft length | the mm value you give (`M5x50` → 50 mm) |
| Wall plug Ø × length | the values you give (`SX6x30` → Ø6 × 30 mm, collar included) |

Everything is drawn at nominal size, with no compensation of any kind. Note that nut
tolerance is one-sided — ISO 4032 allows 9.78–10.00 mm across the flats for M6 — so a
real nut measures a little under the drawing. Scale `WAF` in `gen.py` if you'd rather
match your own stock.

For screws the identifying dimensions — **shaft Ø × length** — print true size; the
head is a visual cue (drawn ISO hex-bolt size, ~5.5 mm across for M3, and varies in
reality by head type). The printable area is **35 × 11.25 mm** (the S001 head is
12 mm but the protocol reserves 6 dots; the label's first ~5 mm is a dead zone), so
a nut wider than 11.25 mm or a screw longer than ~34 mm runs off the edge —
intentional. Keep the `tag_90r_90p` preset, and keep margin trimming off.

## Requirements

- Python 3.9+, Pillow — for generation.
- For printing: a [TiMini-Print](https://github.com/ynsgnr/TiMini-Print) checkout
  (brings `pyserial`) and a paired S001 on a COM port.
