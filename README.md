# Label & Order

Actual-size nut & bolt organisation labels for thermal label printers.

Generate crisp **M-size fastener stickers** where the nut/screw is drawn to **true
scale** — hold a real M5 nut against the "M5 Nuts" label and it matches. Print them
on an Orgstra **S001** (Xinye) label printer via
[TiMini-Print](https://github.com/ynsgnr/TiMini-Print).

![examples](examples/preview.png)

> **Note:** the sizing (dot pitch, feed calibration, bleed compensation, printable
> area) is tuned for the **Orgstra S001**. On other printers the fasteners may come
> out slightly off — adjust `FEED_CAL`, `DPMM`, `LINE_BLEED`, and the `W`/`H`
> printable size at the top of `gen.py`, and measure your first sticker.

## What it does

- **`gen.py`** — generates one PNG per size. Nuts are drawn by ISO hex
  width-across-flats, screws and wall plugs by real Ø × length. Optional head
  shapes, drive icons, a nyloc variant and a plug kind. Anything larger than the
  label runs off the edge and gets cut — by design.
- **`print.py`** — prints a folder of stickers on the S001 through the TiMini CLI:
  one test sticker, you approve, then it prints the rest.

Both axes print at **8 dot/mm** on the S001, so `FEED_CAL = 1.0`. If your printer's
paper advance doesn't match its head, print a nut and measure the hole — it's drawn
as a true circle, so any difference between its two diameters is the feed error.
Set `FEED_CAL` in `gen.py` to (feed diameter ÷ head diameter) and the length axis
is redrawn to compensate; the unused label length stays white.

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
uv run print.py out --serial COM5 --timini ../TiMini-Print
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
| Bolt head (WAF × height) | ISO 4017 |
| Shaft Ø | nominal M-size (edge-measured, bleed-compensated) |
| Shaft length | the mm value you give (`M5x50` → 50 mm) |
| Wall plug Ø × length | the values you give (`SX6x30` → Ø6 × 30 mm, collar included) |

The identifying dimensions — **shaft Ø × length** — print true size; the head is a
visual cue (drawn ISO hex-bolt size, ~5.5 mm across for M3, and varies in reality
by head type). The printable area is **35 × 11.25 mm** (the S001 head is 12 mm but
the protocol reserves 6 dots; the label's first ~5 mm is a dead zone), so a nut
wider than 11.25 mm or a screw longer than ~33 mm runs off the edge — intentional.
Keep the `tag_90r_90p` preset and, on a new printer, measure your first sticker and
tune `FEED_CAL` in `gen.py` if the length is off.

## Requirements

- Python 3.9+, Pillow — for generation.
- For printing: a [TiMini-Print](https://github.com/ynsgnr/TiMini-Print) checkout
  (brings `pyserial`) and a paired S001 on a COM port.
