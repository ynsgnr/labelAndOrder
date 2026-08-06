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
  width-across-flats, screws by real Ø × length. Optional head shapes, drive
  icons, and a nyloc variant. Anything larger than the label runs off the edge
  and gets cut — by design.
- **`print.py`** — prints a folder of stickers on the S001 through the TiMini CLI:
  one test sticker, you approve, then it prints the rest.

The head axis prints at **8 dot/mm**; the S001's paper-advance runs long, so the
generator draws the length axis at a calibrated pitch (`FEED_CAL`, from an 8 mm
feature measuring ~9.5 mm) — fasteners come out **true size** and the unused
length is left white. Set `FEED_CAL = 1.0` in `gen.py` for a printer whose feed
already matches the head.

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
- PNGs are written to `out/` (`M5_nut.png`, `M5x50_screw.png`).
- `--sheet` also writes `_preview.png` so you can eyeball the batch.

**Tags** — add `:tag` after the size (any order) to vary the drawing:

| Tag | Applies to | Effect |
|-----|-----------|--------|
| `nylon` (`nyloc`, `lock`) | nut | dotted insert ring, labelled "Nylon" |
| `pan` (`round`, `dome`, `wall`) | screw | rounded outer head face |
| `csk` (`flat`, `countersunk`) | screw | flat face, countersunk taper into the shaft |
| `hex` (default) | screw | flat hex-bolt head block |
| `philips` `pozi` `torx` `slot` `square` `allen` | screw | drive icon in the top-right |

Examples: `M5:nylon` · `M4x20:pan:philips` · `M5x30:csk:pozi` · `M3x8:torx`

## Print

Printing depends on **[TiMini-Print](https://github.com/ynsgnr/TiMini-Print)**, the
S001 label-printer driver. Clone it, then point `--timini` (or the `TIMINI_DIR`
env var) at your checkout:

```
uv run print.py out --serial COM5 --timini ../TiMini-Print
```

- Prints one sticker, then asks whether to print the rest.
- `--yes` print all without prompting · `--test` first only · `--rest` all but the first.
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

The identifying dimensions — **shaft Ø × length** — print true size; the head is a
visual cue (drawn ISO hex-bolt size, ~5.5 mm across for M3, and varies in reality
by head type). The printable head axis is **11.25 mm** (the S001 head is 12 mm but
the protocol reserves 6 dots), so a nut wider than that clips top/bottom —
intentional. Keep the `tag_90r_90p` preset and, on a new printer, measure your
first sticker and tune `FEED_CAL` in `gen.py` if the length is off.

## Requirements

- Python 3.9+, Pillow — for generation.
- For printing: a [TiMini-Print](https://github.com/ynsgnr/TiMini-Print) checkout
  (brings `pyserial`) and a paired S001 on a COM port.
