#!/usr/bin/env python3
"""
nonogram.py — printable Nonogram (Picross) PDF generator for kids.

Fill in the squares using the row/column number clues; a little picture
appears. Same deductive feel as sudoku, but with a picture as the reward.
Pictures are curated pixel art; every puzzle is verified to have a unique
solution before it's printed.

Examples:
  python3 nonogram.py                                  # 1 easy 5x5
  python3 nonogram.py --size 5 --count 4 --per-page 4 --solution
  python3 nonogram.py --size 10 --count 2 --solution
  python3 nonogram.py --picture heart --solution
"""

import argparse
import random
from datetime import date
from pathlib import Path

from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas


ROMAN = 'Helvetica'
ROMAN_BOLD = 'Helvetica-Bold'

PAGE_W, PAGE_H = letter
MARGIN_X = 0.55 * inch
MARGIN_TOP = 0.5 * inch
MARGIN_BOT = 0.5 * inch


# ---------- picture library ----------
# '#' = filled, anything else = blank. Row 0 is the top row.
# Kept blocky so the clues stay short and the solution stays unique.

PICTURES = {
    5: {
        'heart': [
            ".#.#.",
            "#####",
            "#####",
            ".###.",
            "..#..",
        ],
        'face': [
            ".###.",
            "#.#.#",
            "#####",
            "#.#.#",
            ".###.",
        ],
        'tree': [
            "..#..",
            ".###.",
            "#####",
            "..#..",
            "..#..",
        ],
        'boat': [
            "..#..",
            "..#..",
            "#.#.#",
            "#####",
            ".###.",
        ],
        'cup': [
            "#####",
            "#####",
            ".###.",
            "..#..",
            ".###.",
        ],
        'fish': [
            "..#..",
            ".####",
            "#####",
            ".####",
            "..#..",
        ],
        'duck': [
            ".##..",
            "###.#",
            "#####",
            "####.",
            ".###.",
        ],
        'house': [
            "..#..",
            ".###.",
            "#####",
            "#.#.#",
            "#.#.#",
        ],
    },
    10: {
        'heart': [
            "..##..##..",
            ".########.",
            "##########",
            "##########",
            "##########",
            ".########.",
            "..######..",
            "...####...",
            "....##....",
            "..........",
        ],
        'cat': [
            "#........#",
            "##......##",
            "##########",
            "#.#....#.#",
            "##########",
            "##.####.##",
            "##########",
            "#.######.#",
            "##########",
            "#.#....#.#",
        ],
        'rocket': [
            "....##....",
            "...####...",
            "...####...",
            "..######..",
            "..######..",
            ".########.",
            ".########.",
            "##.####.##",
            "##......##",
            "...#..#...",
        ],
        'fish': [
            "..........",
            "...####...",
            "..######..",
            ".#######.#",
            "#######.##",
            "#######.##",
            ".#######.#",
            "..######..",
            "...####...",
            "..........",
        ],
    },
}


def grid_from_art(art):
    return [[1 if ch == '#' else 0 for ch in row] for row in art]


# ---------- clues ----------

def line_clue(line):
    """Run lengths of 1s in a list, e.g. [1,1,0,1,1,1] -> [2,3]. Empty -> [0]."""
    runs = []
    n = 0
    for v in line:
        if v:
            n += 1
        elif n:
            runs.append(n)
            n = 0
    if n:
        runs.append(n)
    return runs or [0]


def clues_for(grid):
    h = len(grid)
    w = len(grid[0])
    rows = [line_clue(grid[r]) for r in range(h)]
    cols = [line_clue([grid[r][c] for r in range(h)]) for c in range(w)]
    return rows, cols


# ---------- uniqueness solver ----------

def _line_patterns(clue, length):
    """All 0/1 tuples of given length whose run lengths equal `clue`."""
    if clue == [0]:
        return [tuple([0] * length)]
    blocks = clue
    k = len(blocks)
    # minimum length with one gap between blocks
    slack = length - (sum(blocks) + (k - 1))
    if slack < 0:
        return []
    results = []

    def place(idx, pos, acc):
        if idx == k:
            results.append(tuple(acc + [0] * (length - len(acc))))
            return
        # leading gap g (>=0 for first block, >=1 otherwise), bounded by remaining slack
        min_gap = 0 if idx == 0 else 1
        for g in range(min_gap, length):
            start = pos + g
            end = start + blocks[idx]
            if end > length:
                break
            new = acc + [0] * g + [1] * blocks[idx]
            # not the last block needs at least 1 gap after, handled by next min_gap
            place(idx + 1, end, new)

    place(0, 0, [])
    return results


def count_solutions(row_clues, col_clues, limit=2):
    """Count nonogram solutions up to `limit`. Returns int (capped at limit)."""
    h = len(row_clues)
    w = len(col_clues)
    col_pats = [_line_patterns(col_clues[c], h) for c in range(w)]
    if any(len(cp) == 0 for cp in col_pats):
        return 0
    row_pats = [_line_patterns(row_clues[r], w) for r in range(h)]
    if any(len(rp) == 0 for rp in row_pats):
        return 0

    count = 0

    def dfs(r, alive):
        nonlocal count
        if count >= limit:
            return
        if r == h:
            count += 1
            return
        for pat in row_pats[r]:
            new_alive = []
            ok = True
            for c in range(w):
                subset = [p for p in alive[c] if p[r] == pat[c]]
                if not subset:
                    ok = False
                    break
                new_alive.append(subset)
            if ok:
                dfs(r + 1, new_alive)
                if count >= limit:
                    return

    dfs(0, col_pats)
    return count


# ---------- PDF rendering ----------

def draw_page_header(c, title, page_num, total):
    c.setFont(ROMAN_BOLD, 16)
    c.drawCentredString(PAGE_W / 2, PAGE_H - MARGIN_TOP - 4, title)
    y = PAGE_H - MARGIN_TOP - 26
    c.setFont(ROMAN, 10)
    c.drawString(MARGIN_X, y, "Name:")
    c.line(MARGIN_X + 36, y - 2, MARGIN_X + 200, y - 2)
    c.drawString(MARGIN_X + 220, y, "Date:")
    c.line(MARGIN_X + 256, y - 2, MARGIN_X + 380, y - 2)
    c.drawString(MARGIN_X + 400, y, "Time:")
    c.line(MARGIN_X + 436, y - 2, MARGIN_X + 540, y - 2)
    c.setFont(ROMAN, 9)
    c.drawRightString(PAGE_W - MARGIN_X, MARGIN_BOT - 18, f"{page_num} / {total}")
    c.setLineWidth(0.4)
    c.line(MARGIN_X, y - 12, PAGE_W - MARGIN_X, y - 12)
    c.setLineWidth(1)
    return y - 22


def draw_nonogram(c, grid, row_clues, col_clues, x0, y0_top, max_w, max_h,
                  label=None, solved=False):
    h = len(grid)
    w = len(grid[0])
    label_h = 16 if label else 0
    if label:
        c.setFont(ROMAN_BOLD, 11)
        c.drawString(x0, y0_top - 12, label)

    clue_cols = max(len(rc) for rc in row_clues)   # width reserved for row clues
    clue_rows = max(len(cc) for cc in col_clues)    # height reserved for col clues
    total_cols = w + clue_cols
    total_rows = h + clue_rows

    inner_w = max_w
    inner_h = max_h - label_h - 8
    if inner_w <= 0 or inner_h <= 0:
        return
    cell = min(inner_w / total_cols, inner_h / total_rows)
    block_w = cell * total_cols
    block_h = cell * total_rows
    ox = x0 + (inner_w - block_w) / 2
    oy_top = y0_top - label_h - 4 - (inner_h - block_h) / 2

    # grid origin (top-left of the puzzle area, after clue margins)
    gx = ox + clue_cols * cell          # left edge of cells
    gy_top = oy_top - clue_rows * cell  # top edge of cells
    gy_bot = gy_top - h * cell

    def cell_box(r, col):
        x_left = gx + col * cell
        y_bot = gy_top - (r + 1) * cell
        return x_left, y_bot

    clue_fs = max(6.0, cell * 0.5)

    # filled cells (solution)
    if solved:
        c.setFillColorRGB(0.15, 0.15, 0.18)
        for r in range(h):
            for col in range(w):
                if grid[r][col]:
                    x_left, y_bot = cell_box(r, col)
                    c.rect(x_left + 0.6, y_bot + 0.6, cell - 1.2, cell - 1.2,
                           stroke=0, fill=1)
        c.setFillColorRGB(0, 0, 0)

    # row clues (to the left, right-aligned against the grid)
    c.setFont(ROMAN, clue_fs)
    c.setFillColorRGB(0, 0, 0)
    for r in range(h):
        _, y_bot = cell_box(r, 0)
        cy = y_bot + cell / 2 - clue_fs * 0.36
        nums = row_clues[r]
        for i, num in enumerate(reversed(nums)):
            cx = gx - (i + 0.5) * cell
            c.drawCentredString(cx, cy, str(num))

    # column clues (on top, bottom-aligned against the grid)
    for col in range(w):
        x_left, _ = cell_box(0, col)
        cx = x_left + cell / 2
        nums = col_clues[col]
        for i, num in enumerate(reversed(nums)):
            cy = gy_top + (i + 0.5) * cell - clue_fs * 0.36
            c.drawCentredString(cx, cy, str(num))

    # grid lines
    c.setStrokeColorRGB(0.5, 0.5, 0.5)
    c.setLineWidth(0.5)
    for i in range(w + 1):
        c.line(gx + i * cell, gy_bot, gx + i * cell, gy_top)
    for j in range(h + 1):
        c.line(gx, gy_bot + j * cell, gx + w * cell, gy_bot + j * cell)

    # heavier lines every 5 + outer frame
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.6)
    for i in range(0, w + 1, 5):
        c.line(gx + i * cell, gy_bot, gx + i * cell, gy_top)
    for j in range(0, h + 1, 5):
        c.line(gx, gy_bot + j * cell, gx + w * cell, gy_bot + j * cell)
    c.rect(gx, gy_bot, w * cell, h * cell, stroke=1, fill=0)
    c.setLineWidth(1)


# ---------- page layouts ----------

def slot_layout(per_page, top_y):
    usable_h = top_y - MARGIN_BOT
    usable_w = PAGE_W - 2 * MARGIN_X
    if per_page == 1:
        return [(MARGIN_X, top_y, usable_w, usable_h)]
    if per_page == 2:
        half = usable_h / 2
        return [(MARGIN_X, top_y, usable_w, half),
                (MARGIN_X, top_y - half, usable_w, half)]
    if per_page == 4:
        hw, hh = usable_w / 2, usable_h / 2
        return [(MARGIN_X, top_y, hw, hh),
                (MARGIN_X + hw, top_y, hw, hh),
                (MARGIN_X, top_y - hh, hw, hh),
                (MARGIN_X + hw, top_y - hh, hw, hh)]
    raise ValueError(f"--per-page must be 1, 2, or 4 (got {per_page})")


def draw_pages(c, puzzles, title, total_pages, per_page,
               solved=False, page_offset=0):
    """puzzles: list of (grid, row_clues, col_clues, name)."""
    n_items = len(puzzles)
    pages = (n_items + per_page - 1) // per_page
    for pi in range(pages):
        top_y = draw_page_header(c, title, pi + 1 + page_offset, total_pages)
        slots = slot_layout(per_page, top_y)
        for si, (sx, sy, sw, sh) in enumerate(slots):
            mi = pi * per_page + si
            if mi >= n_items:
                break
            grid, rcl, ccl, name = puzzles[mi]
            h, w = len(grid), len(grid[0])
            label = f"#{mi + 1}   ({w} × {h})"
            draw_nonogram(c, grid, rcl, ccl, sx + 6, sy - 4, sw - 12, sh - 10,
                          label=label, solved=solved)
        c.showPage()


# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser(
        description="Kid-friendly Nonogram (Picross) PDF generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--size', type=int, default=5, choices=[5, 10],
                   help='Grid size: 5 (default, gentle) or 10')
    p.add_argument('--picture', default=None,
                   help='Pick a specific picture by name (default: random from the library)')
    p.add_argument('--count', type=int, default=1, help='Number of puzzles (default 1)')
    p.add_argument('--per-page', type=int, default=None, choices=[1, 2, 4],
                   help='Puzzles per page (default by size)')
    p.add_argument('--solution', action='store_true', help='Add an answer-key section')
    p.add_argument('--title', default=None, help='Page title')
    p.add_argument('--out', default=None, help='Output PDF path')
    p.add_argument('--seed', type=int, default=None, help='Random seed (reproducible)')
    args = p.parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    lib = PICTURES[args.size]
    # keep only pictures whose clues yield a unique solution
    unique_names = []
    for name, art in lib.items():
        grid = grid_from_art(art)
        rcl, ccl = clues_for(grid)
        if count_solutions(rcl, ccl, limit=2) == 1:
            unique_names.append(name)
    if not unique_names:
        raise SystemExit("No uniquely-solvable pictures for this size.")

    if args.picture:
        if args.picture not in lib:
            raise SystemExit(f"Unknown picture '{args.picture}'. "
                             f"Available: {', '.join(lib)}")
        if args.picture not in unique_names:
            print(f"Warning: '{args.picture}' does not have a unique solution.")
        chosen = [args.picture] * args.count
    else:
        chosen = []
        while len(chosen) < args.count:
            pool = unique_names[:]
            rng.shuffle(pool)
            chosen.extend(pool[:args.count - len(chosen)])

    if args.per_page is None:
        args.per_page = 4 if args.size == 5 else 2

    title = args.title or f"Nonogram {args.size}×{args.size}"

    out_path = args.out
    if out_path is None:
        out_dir = Path(__file__).parent / 'worksheets'
        out_dir.mkdir(exist_ok=True)
        stamp = date.today().isoformat()
        out_path = out_dir / f'{stamp}_nonogram_{args.size}x{args.size}.pdf'
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    puzzles = []
    for name in chosen:
        grid = grid_from_art(lib[name])
        rcl, ccl = clues_for(grid)
        puzzles.append((grid, rcl, ccl, name))

    n_q_pages = (args.count + args.per_page - 1) // args.per_page
    total_pages = n_q_pages + (n_q_pages if args.solution else 0)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    draw_pages(c, puzzles, title, total_pages, args.per_page,
               solved=False, page_offset=0)
    if args.solution:
        draw_pages(c, puzzles, title + " — Answers", total_pages, args.per_page,
                   solved=True, page_offset=n_q_pages)
    c.save()

    print(f"Generated: {out_path}")
    print(f"  size={args.size}x{args.size}  count={args.count}"
          f"  per_page={args.per_page}  solution={args.solution}")
    print(f"  pictures used: {', '.join(chosen)}")
    print(f"  unique-solvable in library: {', '.join(unique_names)}")


if __name__ == '__main__':
    main()
