# kids_learning — Math Worksheet Generator

A small Python tool that generates **printable math practice PDFs** (no answer key) for early-grade addition / subtraction drills. Built for daily home practice.

Three problem types:

| Type      | What it looks like                       |
|-----------|------------------------------------------|
| `oral`    | Horizontal mental math: `5 + 3 = ___`    |
| `missing` | Find the missing number: `7 + ___ = 12`  |
| `column`  | Vertical (column) form with carry/borrow |

One PDF can mix any number of types — full page, half page, quarter page, whatever.

---

## Requirements

- Python 3.8+
- [`reportlab`](https://pypi.org/project/reportlab/)

```bash
pip install reportlab
```

---

## Quick start

### Single-type CLI (one-shot)

```bash
# 40 mental-math problems within 20 (default)
python3 worksheet.py --type oral --max 20

# 100-range mental math, 3 pages
python3 worksheet.py --type oral --max 100 --pages 3

# Missing-number drill
python3 worksheet.py --type missing --max 20

# Column addition/subtraction within 100, with carry/borrow
python3 worksheet.py --type column --max 100 --carry

# Mixed — cycles oral / missing / column across pages
python3 worksheet.py --type mixed --pages 3 --max 20

# Only addition (or only subtraction)
python3 worksheet.py --type oral --op add
python3 worksheet.py --type oral --op sub

# No carrying/borrowing (good for very early practice)
python3 worksheet.py --type oral --max 20 --no-carry

# Override count and output path
python3 worksheet.py --type oral --count 60 --out today.pdf

# Reproducible output (same problems every time for a given seed)
python3 worksheet.py --type oral --seed 42
```

PDFs land in `worksheets/<YYYY-MM-DD>_<type>.pdf` by default.

### Config-driven mode (multi-section PDFs)

For richer worksheets — multiple sections per page, half-page splits, mixed difficulty — drive it with a JSON config:

```bash
python3 worksheet.py --config configs/daily.json
python3 worksheet.py --config configs/sampler.json
```

A config is a list of pages, each holding a list of sections. The page is divided **vertically** between sections — proportional to each section's problem count by default (override with `weight`).

---

## Config reference

Minimal shape:

```json
{
  "title": "Jamie's Daily Math",
  "pages": [
    { "sections": [ { "type": "oral", "max": 20, "count": 30 } ] }
  ]
}
```

### Section keys (all optional except `type`)

| Key     | Type            | Default            | Notes                                                  |
|---------|-----------------|--------------------|--------------------------------------------------------|
| `type`  | `"oral"` / `"missing"` / `"column"` | (required) |                                                        |
| `max`   | int             | `20`               | Upper bound for operands / results                     |
| `count` | int             | 40 / 24 / 16       | Number of problems in this section                     |
| `op`    | `"add"` / `"sub"` / `"both"` | `"both"` | Restrict to addition or subtraction only               |
| `carry` | bool            | `true` if `max>10` | Allow carrying (add) / borrowing (sub)                 |
| `label` | string          | auto-generated     | Section heading text                                   |
| `weight`| number          | `= count`          | Vertical share of the page (relative to other sections)|
| `cols`  | int             | 4 / 3 / 4          | Override grid column count                             |

### Top-level keys

| Key     | Notes                                              |
|---------|----------------------------------------------------|
| `title` | Page title (printed at the top of every page)      |
| `out`   | Output PDF path (optional; CLI `--out` overrides)  |
| `pages` | List of page specs, each `{ "sections": [...] }`   |

### Config shortcuts

The loader accepts a few simplified shapes:

```jsonc
// just sections → one page
{ "title": "Practice", "sections": [ { "type": "oral", "max": 20 } ] }

// bare list of sections → one page
[ { "type": "oral", "max": 20 } ]

// single section dict → one section, one page
{ "type": "oral", "max": 20, "count": 30 }
```

---

## Example configs

`configs/daily.json` — two pages, two sections each:

```json
{
  "title": "Jamie's Daily Math",
  "pages": [
    {
      "sections": [
        { "type": "oral",   "max": 20,  "count": 30 },
        { "type": "column", "max": 100, "count": 6, "carry": true }
      ]
    },
    {
      "sections": [
        { "type": "missing", "max": 20, "count": 18 },
        { "type": "oral",    "max": 20, "count": 20, "op": "sub",
          "label": "Subtraction Drill (within 20)" }
      ]
    }
  ]
}
```

`configs/sampler.json` — three sections on page 1, two on page 2, one full-page column on page 3.

Run them:

```bash
python3 worksheet.py --config configs/daily.json
python3 worksheet.py --config configs/sampler.json
```

---

## CLI reference

```text
--config PATH        JSON config file (multi-section / multi-page)
--type TYPE          oral | missing | column | mixed
--count N            Problems per section
--pages N            Number of pages (CLI mode only)
--max N              Upper bound for numbers (default 20)
--op WHICH           add | sub | both (default both)
--carry              Allow carry/borrow
--no-carry           Disallow carry/borrow
--title STR          Page title
--out PATH           Output PDF path
--seed N             Random seed (reproducible)
```

---

## Tips

- **Daily routine.** Build a `configs/daily.json` you like, then `python3 worksheet.py --config configs/daily.json` is the one command you run each morning.
- **Stage difficulty.** Start with `--no-carry --max 10`, graduate to `--max 20`, then `--max 100 --carry`. With configs you can keep all three stages on the same page for a warm-up → main → stretch flow.
- **Reproducibility.** Pass `--seed N` if you want to re-print the exact same sheet (e.g., to compare today's time against yesterday's).
- **Page count auto-fit.** Section heights divide the page proportionally to `count`. If a section feels cramped, bump its `weight` or split it across pages.
- **No answer key.** By design — problems are simple enough to eyeball-check, and skipping the answer page keeps the printout to a single sheet most days.
