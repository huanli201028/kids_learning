# kids_learning

`pip install reportlab`

## Daily run

```bash
python3 worksheet.py --config configs/daily.json
python3 maze.py --difficulty medium --spikes
python3 sudoku.py --size 4 --difficulty easy --count 4 --per-page 4
```

PDFs land in `worksheets/`. Edit `configs/daily.json` to change what's on the sheet.

---

## `worksheet.py`

```bash
# Single section
python3 worksheet.py --type oral    --min 0 --max 20
python3 worksheet.py --type column  --max 100 --regroup-pct 80
python3 worksheet.py --type missing --max 20 --regroup-pct 0

# Multi-section / multi-page
python3 worksheet.py --config configs/daily.json
```

Flags: `--type {oral|missing|column|mixed}` `--min N` `--max N` `--count N` `--pages N` `--op {add|sub|both}` `--regroup-pct N` / `--regroup` / `--no-regroup` `--title STR` `--out PATH` `--seed N`

Config section keys: `type` (required), `min`, `max`, `count`, `op`, `regroup_pct`, `label`, `weight`, `cols`. See `configs/daily.json` / `configs/sampler.json`.

## `maze.py`

```bash
python3 maze.py --difficulty medium --spikes           # daily — Jamie's preference
python3 maze.py --difficulty medium --spikes --spike-density 0.35
python3 maze.py --difficulty easy --count 4 --per-page 4
python3 maze.py --theme random --count 3
```

Spikes are Geometry-Dash-style red triangles sprinkled inside cells (top, bottom, or both). They are decorative — the path through every cell is still walkable; the player mentally slips past the tips.

Flags: `--difficulty {easy|medium|hard|xl}` `--width N --height N` `--count N` `--per-page {1|2|4}` `--spikes` `--spike-density 0.0–1.0` `--theme {mouse|car|rocket|random}` `--title STR` `--out PATH` `--seed N`

## `sudoku.py`

```bash
python3 sudoku.py                                       # 1 easy 4x4 (the gentle default)
python3 sudoku.py --size 4 --difficulty easy --count 4 --per-page 4
python3 sudoku.py --size 4 --symbols --count 2          # colored shapes, not numbers
python3 sudoku.py --size 6 --difficulty medium          # the next step up
python3 sudoku.py --size 9 --difficulty hard --solution # classic, for later
```

Standard 9×9 is too hard for Jamie right now, so this starts at **4×4** (numbers 1–4, 2×2 boxes) — same rules, tiny search space. **6×6** (1–6, 2×3 boxes) is the bridge to the classic **9×9**. Difficulty just sets how many numbers are given; every puzzle has a unique solution. `--symbols` swaps digits for colored shapes (circle/square/triangle/star…) with a key at the top, which takes the "math" feeling out of it for little kids.

Flags: `--size {4|6|9}` `--difficulty {easy|medium|hard}` `--clues N` `--count N` `--per-page {1|2|4|6}` `--symbols` `--solution` `--title STR` `--out PATH` `--seed N`
