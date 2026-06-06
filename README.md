# kids_learning

`pip install reportlab`

## Daily run

```bash
python3 worksheet.py --config configs/daily.json
python3 maze.py --difficulty medium --spikes
python3 sudoku.py --size 4 --difficulty easy --count 4 --per-page 4
python3 nonogram.py --size 5 --count 4 --per-page 4 --solution
python3 color_by_sum.py --max 10 --op add --solution
python3 flow.py --size 5 --count 4 --per-page 4 --solution
python3 dot_to_dot.py --count 4 --per-page 4 --solution
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

## `maze.py` — 迷宫

**玩法**：从入口（左上角的老鼠/小车/火箭图标）出发，一笔画走到出口（右下角的奶酪/旗子/星星），不能穿墙。`--spikes` 的红三角是装饰，可以无视——每个格子都走得通。

```bash
python3 maze.py --difficulty medium --spikes           # daily — Jamie's preference
python3 maze.py --difficulty medium --spikes --spike-density 0.35
python3 maze.py --difficulty easy --count 4 --per-page 4
python3 maze.py --theme random --count 3
```

Spikes are Geometry-Dash-style red triangles sprinkled inside cells (top, bottom, or both). They are decorative — the path through every cell is still walkable; the player mentally slips past the tips.

Flags: `--difficulty {easy|medium|hard|xl}` `--width N --height N` `--count N` `--per-page {1|2|4}` `--spikes` `--spike-density 0.0–1.0` `--theme {mouse|car|rocket|random}` `--title STR` `--out PATH` `--seed N`

## `sudoku.py` — 数独

**玩法**：把数字填进空格，让 **每一行、每一列、每个粗线围起来的宫格** 里，1 到 N 各出现一次、不重复（4×4 用 1–4，6×6 用 1–6，9×9 用 1–9）。`--symbols` 模式则是每行/列/宫里每种形状各出现一次。

```bash
python3 sudoku.py                                       # 1 easy 4x4 (the gentle default)
python3 sudoku.py --size 4 --difficulty easy --count 4 --per-page 4
python3 sudoku.py --size 4 --symbols --count 2          # colored shapes, not numbers
python3 sudoku.py --size 6 --difficulty medium          # the next step up
python3 sudoku.py --size 9 --difficulty hard --solution # classic, for later
```

Standard 9×9 is too hard for Jamie right now, so this starts at **4×4** (numbers 1–4, 2×2 boxes) — same rules, tiny search space. **6×6** (1–6, 2×3 boxes) is the bridge to the classic **9×9**. Difficulty just sets how many numbers are given; every puzzle has a unique solution. `--symbols` swaps digits for colored shapes (circle/square/triangle/star…) with a key at the top, which takes the "math" feeling out of it for little kids.

Flags: `--size {4|6|9}` `--difficulty {easy|medium|hard}` `--clues N` `--count N` `--per-page {1|2|4|6}` `--symbols` `--solution` `--title STR` `--out PATH` `--seed N`

## `nonogram.py` — 数织 / Picross

**玩法**：每行左侧、每列上方的数字，表示那一行/列里要涂黑的连续格子段的长度——一个数字就是一段连续的黑格，多个数字就是多段，段与段之间至少空一格（例：`2 3` = 先 2 个黑格，空开，再 3 个黑格）。靠行列提示互相推理，决定每格涂黑还是留白，全部涂完就显出一幅图。

```bash
python3 nonogram.py                                     # 1 easy 5x5
python3 nonogram.py --size 5 --count 4 --per-page 4 --solution
python3 nonogram.py --size 10 --count 2 --solution
python3 nonogram.py --picture heart --solution
```

Fill squares from the row/column number clues and a picture appears (same deductive feel as sudoku, with a picture as the reward). Pictures are curated pixel art; every puzzle is verified to have a **unique solution** before printing. Pics: 5×5 `heart/face/tree/boat/cup/fish/duck/house`, 10×10 `heart/cat/rocket/fish`.

Flags: `--size {5|10}` `--picture NAME` `--count N` `--per-page {1|2|4}` `--solution` `--title STR` `--out PATH` `--seed N`

## `color_by_sum.py` — 算式填色

**玩法**：每个格子里有一道加减算式，先算出得数；对照页面顶部的图例（得数 → 颜色），把这个格子涂成对应的颜色。空白格不涂。所有格子涂完，就显出一幅彩色图画。

```bash
python3 color_by_sum.py                                 # 1 picture, sums to 10
python3 color_by_sum.py --max 20 --op both --count 2 --solution
python3 color_by_sum.py --picture butterfly --solution
python3 color_by_sum.py --op add --max 10 --count 4 --per-page 4
```

Each colored square of a hidden picture holds a sum; solve it, look up the answer in the key (answer → color), and color the square. Arithmetic practice disguised as art. Pics: `house/flower/butterfly/fish/sailboat`.

Flags: `--picture NAME` `--max N` `--op {add|sub|both}` `--count N` `--per-page {1|2|4}` `--solution` `--title STR` `--out PATH` `--seed N`

## `flow.py` — 数字连线 / Flow

**玩法**：盘面上有几对相同数字（同色）的圆点。用线把每一对相同的点连起来——线只能沿横竖方向走、不能斜着走，不同的线不能交叉或重叠，而且最后要让**所有格子都被线填满**。

```bash
python3 flow.py                                         # 1 easy 5x5
python3 flow.py --size 5 --count 4 --per-page 4 --solution
python3 flow.py --size 6 --colors 5 --solution
python3 flow.py --size 7 --count 2 --solution
```

Connect each pair of same-colored numbered dots with a path; paths can't cross and together fill every square (a spatial cousin of the maze). Generated from a real solution, so always solvable (the shown answer is one valid solution; may not be unique).

Flags: `--size {5|6|7}` `--colors N` `--count N` `--per-page {1|2|4}` `--solution` `--title STR` `--out PATH` `--seed N`

## `dot_to_dot.py` — 连点成画

**玩法**：从绿色的 1 号点开始，按数字顺序 1 → 2 → 3 … 用直线一个接一个连接所有点，连到最后一个点（闭合图形再连回 1），就显出一幅图画。

```bash
python3 dot_to_dot.py                                   # 1 random picture
python3 dot_to_dot.py --shape star --solution
python3 dot_to_dot.py --count 4 --per-page 4 --solution
```

Connect the numbered dots in order (1 → 2 → 3 …) and a picture appears — reinforces counting and number order. Start dot is green. Shapes: `star/heart/fish/house/cat/rocket/sailboat`.

Flags: `--shape NAME` `--count N` `--per-page {1|2|4}` `--solution` `--title STR` `--out PATH` `--seed N`
