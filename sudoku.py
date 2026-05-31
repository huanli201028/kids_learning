#!/usr/bin/env python3
"""
sudoku.py — printable kid-friendly Sudoku PDF generator.

Built for small kids who find the standard 9x9 grid too hard. The default is a
gentle 4x4 grid (numbers 1-4, 2x2 boxes); 6x6 is the next step up; 9x9 is there
for when they grow into it. Every puzzle has a unique solution.

Examples:
  python3 sudoku.py                                   # 1 easy 4x4 puzzle
  python3 sudoku.py --size 4 --difficulty easy --count 4 --per-page 4
  python3 sudoku.py --size 4 --symbols --count 2      # shapes instead of numbers
  python3 sudoku.py --size 6 --difficulty medium
  python3 sudoku.py --size 9 --difficulty hard --solution
  python3 sudoku.py --count 6 --per-page 6 --solution --seed 42
"""

import argparse
import math
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


# ---------- grid shapes ----------
# Each size maps to (box_rows, box_cols); the grid is n x n where n = box_rows * box_cols.
# Boxes are box_rows tall and box_cols wide.

BOX_SHAPE = {
    4: (2, 2),   # numbers 1-4
    6: (2, 3),   # numbers 1-6
    9: (3, 3),   # numbers 1-9
}


# ---------- sudoku generation ----------

def _candidates(grid, n, br, bc, r, c):
    """Set of values that may legally go in empty cell (r, c)."""
    used = set()
    for i in range(n):
        used.add(grid[r][i])
        used.add(grid[i][c])
    box_r = (r // br) * br
    box_c = (c // bc) * bc
    for i in range(box_r, box_r + br):
        for j in range(box_c, box_c + bc):
            used.add(grid[i][j])
    return [v for v in range(1, n + 1) if v not in used]


def _first_empty(grid, n):
    for r in range(n):
        for c in range(n):
            if grid[r][c] == 0:
                return r, c
    return None


def gen_full(n, br, bc, rng):
    """Return a fully filled valid grid (list of lists), built by randomized backtracking."""
    grid = [[0] * n for _ in range(n)]

    def fill():
        spot = _first_empty(grid, n)
        if spot is None:
            return True
        r, c = spot
        cands = _candidates(grid, n, br, bc, r, c)
        rng.shuffle(cands)
        for v in cands:
            grid[r][c] = v
            if fill():
                return True
            grid[r][c] = 0
        return False

    fill()
    return grid


def count_solutions(grid, n, br, bc, limit=2):
    """Count solutions up to `limit` (used to verify uniqueness). Non-destructive."""
    work = [row[:] for row in grid]

    def solve():
        spot = _first_empty(work, n)
        if spot is None:
            return 1
        r, c = spot
        total = 0
        for v in _candidates(work, n, br, bc, r, c):
            work[r][c] = v
            total += solve()
            work[r][c] = 0
            if total >= limit:
                return total
        return total

    return solve()


def make_puzzle(full, n, br, bc, rng, clues):
    """Carve a unique-solution puzzle from a full grid, keeping ~`clues` givens.

    Cells are removed in a random order; a removal is kept only if the puzzle
    still has exactly one solution. Symmetric (rotational) pairs are removed
    together so the sheet looks tidy.
    """
    puzzle = [row[:] for row in full]
    cells = [(r, c) for r in range(n) for c in range(n)]
    rng.shuffle(cells)

    filled = n * n
    for (r, c) in cells:
        if filled <= clues:
            break
        if puzzle[r][c] == 0:
            continue
        # rotationally symmetric partner
        r2, c2 = n - 1 - r, n - 1 - c
        pair = {(r, c), (r2, c2)}
        saved = {(pr, pc): puzzle[pr][pc] for (pr, pc) in pair}
        for (pr, pc) in pair:
            puzzle[pr][pc] = 0
        if count_solutions(puzzle, n, br, bc, limit=2) == 1:
            filled -= len(pair)
        else:
            for (pr, pc), v in saved.items():
                puzzle[pr][pc] = v
    return puzzle


# ---------- clue counts by size & difficulty ----------
# Higher = more given numbers = easier. Tuned so the default 4x4/easy is very
# gentle for a pre-K / early-grade kid.

CLUES = {
    4: {'easy': 9,  'medium': 7,  'hard': 5},
    6: {'easy': 22, 'medium': 17, 'hard': 13},
    9: {'easy': 40, 'medium': 32, 'hard': 26},
}


# ---------- symbol drawing (shapes instead of numbers) ----------
# Maps value -> a little colored shape so the puzzle feels like a game, not math.
# Used only for the 4x4 and 6x6 grids (where there are few enough symbols).

SYMBOL_COLORS = [
    (0.90, 0.25, 0.25),   # 1 red
    (0.20, 0.55, 0.95),   # 2 blue
    (0.25, 0.70, 0.35),   # 3 green
    (0.95, 0.70, 0.15),   # 4 yellow
    (0.65, 0.35, 0.80),   # 5 purple
    (0.95, 0.50, 0.20),   # 6 orange
]


def _shape_circle(c, cx, cy, s):
    c.circle(cx, cy, s, stroke=1, fill=1)


def _shape_square(c, cx, cy, s):
    c.rect(cx - s, cy - s, 2 * s, 2 * s, stroke=1, fill=1)


def _shape_triangle(c, cx, cy, s):
    p = c.beginPath()
    p.moveTo(cx, cy + s)
    p.lineTo(cx + s, cy - s)
    p.lineTo(cx - s, cy - s)
    p.close()
    c.drawPath(p, stroke=1, fill=1)


def _shape_star(c, cx, cy, s):
    R = s
    r = s * 0.45
    p = c.beginPath()
    for i in range(10):
        ang = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        x = cx + rad * math.cos(ang)
        y = cy + rad * math.sin(ang)
        if i == 0:
            p.moveTo(x, y)
        else:
            p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=1, fill=1)


def _shape_diamond(c, cx, cy, s):
    p = c.beginPath()
    p.moveTo(cx, cy + s)
    p.lineTo(cx + s, cy)
    p.lineTo(cx, cy - s)
    p.lineTo(cx - s, cy)
    p.close()
    c.drawPath(p, stroke=1, fill=1)


def _shape_heart(c, cx, cy, s):
    p = c.beginPath()
    p.moveTo(cx, cy - s)
    p.curveTo(cx + s * 1.4, cy + s * 0.4, cx + s * 0.5, cy + s * 1.1, cx, cy + s * 0.4)
    p.curveTo(cx - s * 0.5, cy + s * 1.1, cx - s * 1.4, cy + s * 0.4, cx, cy - s)
    p.close()
    c.drawPath(p, stroke=1, fill=1)


SHAPE_DRAWERS = [
    _shape_circle,
    _shape_square,
    _shape_triangle,
    _shape_star,
    _shape_diamond,
    _shape_heart,
]


def draw_symbol(c, value, cx, cy, cell):
    """Draw the shape for `value` (1-based) centered at (cx, cy)."""
    idx = (value - 1) % len(SHAPE_DRAWERS)
    s = cell * 0.26
    col = SYMBOL_COLORS[idx % len(SYMBOL_COLORS)]
    c.setFillColorRGB(*col)
    c.setStrokeColorRGB(col[0] * 0.6, col[1] * 0.6, col[2] * 0.6)
    c.setLineWidth(0.8)
    SHAPE_DRAWERS[idx](c, cx, cy, s)
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)


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


def draw_grid(c, puzzle, n, br, bc, x0, y0_top, max_w, max_h,
              label=None, symbols=False, solution=None):
    """Draw a sudoku grid inside the box anchored at top-left (x0, y0_top).

    `puzzle` holds the givens (0 = blank). If `solution` is provided, its values
    are drawn in light gray in the blanks (used for the answer-key pages).
    """
    label_h = 16 if label else 0
    if label:
        c.setFont(ROMAN_BOLD, 11)
        c.drawString(x0, y0_top - 12, label)

    inner_w = max_w
    inner_h = max_h - label_h - 8
    if inner_w <= 0 or inner_h <= 0:
        return

    cell = min(inner_w / n, inner_h / n)
    grid_w = grid_h = cell * n
    ox = x0 + (inner_w - grid_w) / 2
    oy_top = y0_top - label_h - 4 - (inner_h - grid_h) / 2
    oy = oy_top - grid_h  # bottom-left of grid

    def cell_box(r, c_):
        # row 0 is the top row
        x_left = ox + c_ * cell
        y_bot = oy + (n - 1 - r) * cell
        return x_left, y_bot

    # numbers / symbols
    for r in range(n):
        for col in range(n):
            v = puzzle[r][col]
            x_left, y_bot = cell_box(r, col)
            cx = x_left + cell / 2
            cy = y_bot + cell / 2
            if v != 0:
                if symbols:
                    draw_symbol(c, v, cx, cy, cell)
                else:
                    c.setFillColorRGB(0, 0, 0)
                    fs = cell * 0.55
                    c.setFont(ROMAN_BOLD, fs)
                    c.drawCentredString(cx, cy - fs * 0.36, str(v))
            elif solution is not None:
                sv = solution[r][col]
                if symbols:
                    # faint shape: just draw it (already light pastel enough)
                    draw_symbol(c, sv, cx, cy, cell)
                else:
                    c.setFillColorRGB(0.6, 0.6, 0.6)
                    fs = cell * 0.5
                    c.setFont(ROMAN, fs)
                    c.drawCentredString(cx, cy - fs * 0.36, str(sv))
                    c.setFillColorRGB(0, 0, 0)

    # thin cell lines
    c.setStrokeColorRGB(0.45, 0.45, 0.45)
    c.setLineWidth(0.6)
    for i in range(n + 1):
        c.line(ox + i * cell, oy, ox + i * cell, oy + grid_h)
        c.line(ox, oy + i * cell, ox + grid_w, oy + i * cell)

    # thick box borders + outer frame
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(2.0)
    for i in range(0, n + 1, bc):
        c.line(ox + i * cell, oy, ox + i * cell, oy + grid_h)
    for j in range(0, n + 1, br):
        c.line(ox, oy + j * cell, ox + grid_w, oy + j * cell)
    c.rect(ox, oy, grid_w, grid_h, stroke=1, fill=0)

    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)


def draw_legend(c, n, x0, y_top, symbols):
    """For symbol mode, show which shape is which (a little key)."""
    if not symbols:
        return
    c.setFont(ROMAN, 9)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(x0, y_top, "Key:")
    x = x0 + 28
    for v in range(1, n + 1):
        draw_symbol(c, v, x, y_top + 3, 22)
        x += 26


# ---------- page layouts ----------

def slot_layout(per_page, top_y):
    usable_h = top_y - MARGIN_BOT
    usable_w = PAGE_W - 2 * MARGIN_X
    if per_page == 1:
        return [(MARGIN_X, top_y, usable_w, usable_h)]
    if per_page == 2:
        half = usable_h / 2
        return [
            (MARGIN_X, top_y,        usable_w, half),
            (MARGIN_X, top_y - half, usable_w, half),
        ]
    if per_page == 4:
        hw, hh = usable_w / 2, usable_h / 2
        return [
            (MARGIN_X,      top_y,      hw, hh),
            (MARGIN_X + hw, top_y,      hw, hh),
            (MARGIN_X,      top_y - hh, hw, hh),
            (MARGIN_X + hw, top_y - hh, hw, hh),
        ]
    if per_page == 6:
        hw = usable_w / 2
        th = usable_h / 3
        slots = []
        for row in range(3):
            for col in range(2):
                slots.append((MARGIN_X + col * hw, top_y - row * th, hw, th))
        return slots
    raise ValueError(f"--per-page must be 1, 2, 4, or 6 (got {per_page})")


def draw_pages(c, puzzles, title, total_pages, per_page,
               symbols=False, with_solution=False, page_offset=0):
    """puzzles is a list of (puzzle, full, n, br, bc). Draw across pages."""
    n_items = len(puzzles)
    pages = (n_items + per_page - 1) // per_page
    for pi in range(pages):
        top_y = draw_page_header(c, title, pi + 1 + page_offset, total_pages)
        if symbols:
            n0 = puzzles[0][2]
            draw_legend(c, n0, MARGIN_X, top_y - 2, symbols)
            top_y -= 22
        slots = slot_layout(per_page, top_y)
        for si, (sx, sy, sw, sh) in enumerate(slots):
            mi = pi * per_page + si
            if mi >= n_items:
                break
            puzzle, full, n, br, bc = puzzles[mi]
            label = f"#{mi + 1}   ({n} × {n})"
            sol = full if with_solution else None
            draw_grid(c, puzzle, n, br, bc, sx + 6, sy - 4, sw - 12, sh - 10,
                      label=label, symbols=symbols, solution=sol)
        c.showPage()


# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser(
        description="Kid-friendly Sudoku PDF generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--size', type=int, default=4, choices=[4, 6, 9],
                   help='Grid size: 4 (1-4, default), 6 (1-6), or 9 (classic)')
    p.add_argument('--difficulty', choices=['easy', 'medium', 'hard'],
                   default='easy', help='Controls how many numbers are given (default easy)')
    p.add_argument('--clues', type=int, default=None,
                   help='Exact number of given cells (overrides --difficulty)')
    p.add_argument('--count', type=int, default=1, help='Number of puzzles (default 1)')
    p.add_argument('--per-page', type=int, default=None, choices=[1, 2, 4, 6],
                   help='Puzzles per page (default picks a sensible value by size)')
    p.add_argument('--symbols', action='store_true',
                   help='Use colored shapes instead of numbers (great for little kids; '
                        'best with --size 4 or 6)')
    p.add_argument('--solution', action='store_true',
                   help='Add an answer-key section at the end')
    p.add_argument('--title', default=None, help='Page title')
    p.add_argument('--out', default=None, help='Output PDF path')
    p.add_argument('--seed', type=int, default=None, help='Random seed (reproducible)')
    args = p.parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    n = args.size
    br, bc = BOX_SHAPE[n]
    clues = args.clues if args.clues is not None else CLUES[n][args.difficulty]

    if args.per_page is None:
        args.per_page = {4: 4, 6: 2, 9: 1}[n]

    if args.symbols and n == 9:
        print("Note: --symbols with --size 9 needs 9 distinct shapes; "
              "consider --size 4 or 6 for clearer symbols.")

    title = args.title or (f"Shape Sudoku {n}×{n}" if args.symbols
                           else f"Sudoku {n}×{n}")

    out_path = args.out
    if out_path is None:
        out_dir = Path(__file__).parent / 'worksheets'
        out_dir.mkdir(exist_ok=True)
        stamp = date.today().isoformat()
        sym_tag = '_shapes' if args.symbols else ''
        out_path = out_dir / f'{stamp}_sudoku_{n}x{n}_{args.difficulty}{sym_tag}.pdf'
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    puzzles = []
    for _ in range(args.count):
        full = gen_full(n, br, bc, rng)
        puzzle = make_puzzle(full, n, br, bc, rng, clues)
        puzzles.append((puzzle, full, n, br, bc))

    n_q_pages = (args.count + args.per_page - 1) // args.per_page
    total_pages = n_q_pages + (n_q_pages if args.solution else 0)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    draw_pages(c, puzzles, title, total_pages, args.per_page,
               symbols=args.symbols, with_solution=False, page_offset=0)
    if args.solution:
        draw_pages(c, puzzles, title + " — Answers", total_pages, args.per_page,
                   symbols=args.symbols, with_solution=True, page_offset=n_q_pages)
    c.save()

    print(f"Generated: {out_path}")
    print(f"  size={n}x{n}  difficulty={args.difficulty}  clues={clues}"
          f"  count={args.count}  per_page={args.per_page}"
          f"  symbols={args.symbols}  solution={args.solution}")


if __name__ == '__main__':
    main()
