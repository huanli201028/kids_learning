# kids_learning

`pip install reportlab`

## Daily run

```bash
python3 worksheet.py --config configs/daily.json
python3 maze.py --theme mouse
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
python3 maze.py                                       # 1 medium maze
python3 maze.py --difficulty easy --count 4 --per-page 4
python3 maze.py --difficulty hard --solution
python3 maze.py --theme random --count 3
```

Flags: `--difficulty {easy|medium|hard|xl}` `--width N --height N` `--count N` `--per-page {1|2|4}` `--solution` `--theme {mouse|car|rocket|random}` `--title STR` `--out PATH` `--seed N`
