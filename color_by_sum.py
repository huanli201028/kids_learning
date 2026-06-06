#!/usr/bin/env python3
"""
color_by_sum.py — printable "color by addition/subtraction" PDF generator.

Every colored square of a hidden picture holds a little sum. Solve it, look up
the answer in the key (answer -> color), and color the square. When the whole
grid is colored, the picture appears. Arithmetic practice disguised as art.

Examples:
  python3 color_by_sum.py                                # 1 picture, sums to 10
  python3 color_by_sum.py --max 20 --op both --count 2 --solution
  python3 color_by_sum.py --picture butterfly --solution
  python3 color_by_sum.py --op add --max 10 --count 4 --per-page 4
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


# ---------- palette ----------
# Color index (as used in the pictures) -> (name, rgb). '.' in art = blank (white).

PALETTE = {
    1: ('red',    (0.90, 0.27, 0.27)),
    2: ('yellow', (0.97, 0.80, 0.20)),
    3: ('green',  (0.30, 0.70, 0.36)),
    4: ('blue',   (0.27, 0.55, 0.90)),
    5: ('orange', (0.95, 0.55, 0.20)),
    6: ('purple', (0.62, 0.38, 0.82)),
}


# ---------- picture library ----------
# Each character is a color index (1-6) or '.' for a blank/white square.
# Row 0 is the top row.

PICTURES = {
    'house': [
        "..2222..",
        ".222222.",
        "22222222",
        "11111111",
        "11133111",
        "11133111",
        "11133111",
        "11111111",
    ],
    'flower': [
        "..1111..",
        ".111111.",
        "11222211",
        "11222211",
        ".111111.",
        "..1111..",
        "...33...",
        "...33...",
    ],
    'butterfly': [
        ".6....6.",
        "66.55.66",
        "66655666",
        "66655666",
        "66655666",
        "66655666",
        "66.55.66",
        ".6....6.",
    ],
    'fish': [
        "........",
        "..444...",
        ".44444..",
        "44444411",
        "44444411",
        ".44444..",
        "..444...",
        "........",
    ],
    'sailboat': [
        "....2...",
        "....22..",
        "....222.",
        "..1.2222",
        "..11.2..",
        "33333333",
        ".333333.",
        "........",
    ],
}


def parse_picture(art):
    """Return grid[r][c] = color index (int) or 0 for blank."""
    return [[int(ch) if ch.isdigit() else 0 for ch in row] for row in art]


# ---------- problem generation ----------

def make_problem(target, maxv, op, rng):
    """A string 'a+b' or 'a-b' whose value == target, within [0, maxv]."""
    choices = []
    if op in ('add', 'both'):
        choices.append('add')
    if op in ('sub', 'both'):
        # subtraction only possible if there's room above the target
        if maxv >= target:
            choices.append('sub')
    kind = rng.choice(choices) if choices else 'add'
    if kind == 'add':
        a = rng.randint(0, target)
        b = target - a
        return f"{a}+{b}"
    # subtraction: a - b = target, with a <= maxv
    a = rng.randint(target, maxv)
    b = a - target
    return f"{a}-{b}"


def assign_targets(color_indices, maxv, rng):
    """Map each used color index to a distinct answer number in [1, maxv]."""
    pool = list(range(1, maxv + 1))
    rng.shuffle(pool)
    if len(color_indices) > len(pool):
        raise SystemExit(f"--max {maxv} is too small for {len(color_indices)} colors.")
    return {ci: pool[i] for i, ci in enumerate(sorted(color_indices))}


def build_puzzle(grid, maxv, op, rng):
    """Return (problems, targets) where problems[r][c] is a string or None."""
    used = sorted({grid[r][c] for r in range(len(grid)) for c in range(len(grid[0]))
                   if grid[r][c] != 0})
    targets = assign_targets(used, maxv, rng)
    problems = []
    for r in range(len(grid)):
        row = []
        for c in range(len(grid[0])):
            ci = grid[r][c]
            if ci == 0:
                row.append(None)
            else:
                row.append(make_problem(targets[ci], maxv, op, rng))
        problems.append(row)
    return problems, targets


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


def draw_key(c, targets, x0, y_top):
    """Color key: a swatch + '= N' for each color, laid out left to right."""
    c.setFont(ROMAN_BOLD, 10)
    c.setFillColorRGB(0, 0, 0)
    c.drawString(x0, y_top, "Color key:")
    x = x0 + 64
    sw = 14
    c.setFont(ROMAN, 10)
    for ci in sorted(targets):
        _, rgb = PALETTE[ci]
        c.setFillColorRGB(*rgb)
        c.setStrokeColorRGB(0.3, 0.3, 0.3)
        c.setLineWidth(0.6)
        c.rect(x, y_top - 3, sw, sw, stroke=1, fill=1)
        c.setFillColorRGB(0, 0, 0)
        c.drawString(x + sw + 4, y_top, f"= {targets[ci]}")
        x += sw + 44
    return y_top - 22


def draw_grid(c, grid, problems, x0, y0_top, max_w, max_h, label=None, solved=False):
    h = len(grid)
    w = len(grid[0])
    label_h = 16 if label else 0
    if label:
        c.setFont(ROMAN_BOLD, 11)
        c.drawString(x0, y0_top - 12, label)

    inner_w = max_w
    inner_h = max_h - label_h - 8
    if inner_w <= 0 or inner_h <= 0:
        return
    cell = min(inner_w / w, inner_h / h)
    grid_w, grid_h = cell * w, cell * h
    ox = x0 + (inner_w - grid_w) / 2
    oy_top = y0_top - label_h - 4 - (inner_h - grid_h) / 2
    oy = oy_top - grid_h

    def cell_box(r, col):
        return ox + col * cell, oy + (h - 1 - r) * cell

    fs = max(5.5, cell * 0.30)
    for r in range(h):
        for col in range(w):
            x_left, y_bot = cell_box(r, col)
            ci = grid[r][col]
            if solved and ci != 0:
                _, rgb = PALETTE[ci]
                c.setFillColorRGB(*rgb)
                c.rect(x_left, y_bot, cell, cell, stroke=0, fill=1)
            elif (not solved) and problems[r][col] is not None:
                c.setFont(ROMAN, fs)
                c.setFillColorRGB(0, 0, 0)
                c.drawCentredString(x_left + cell / 2,
                                    y_bot + cell / 2 - fs * 0.36,
                                    problems[r][col])

    # grid lines (only meaningful cells get a clear border; draw all for structure)
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.setLineWidth(0.5)
    for i in range(w + 1):
        c.line(ox + i * cell, oy, ox + i * cell, oy + grid_h)
    for j in range(h + 1):
        c.line(ox, oy + j * cell, ox + grid_w, oy + j * cell)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.2)
    c.rect(ox, oy, grid_w, grid_h, stroke=1, fill=0)
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


def draw_pages(c, puzzles, title, total_pages, per_page, solved=False, page_offset=0):
    """puzzles: list of (grid, problems, targets, name)."""
    n_items = len(puzzles)
    pages = (n_items + per_page - 1) // per_page
    for pi in range(pages):
        top_y = draw_page_header(c, title, pi + 1 + page_offset, total_pages)
        # one shared key per page works when all puzzles on the page share targets;
        # to stay correct we draw each puzzle's key just above its own grid for per_page 1.
        slots = slot_layout(per_page, top_y)
        for si, (sx, sy, sw, sh) in enumerate(slots):
            mi = pi * per_page + si
            if mi >= n_items:
                break
            grid, problems, targets, name = puzzles[mi]
            inner_top = sy
            if per_page == 1:
                inner_top = draw_key(c, targets, sx + 6, sy - 8)
            h, w = len(grid), len(grid[0])
            label = f"#{mi + 1}   ({w} × {h})"
            if per_page != 1:
                # compact inline key in the label row
                draw_key(c, targets, sx + 6, sy - 12)
                label = None
                inner_top = sy - 22
            draw_grid(c, grid, problems, sx + 6, inner_top - 4, sw - 12,
                      (inner_top - (sy - sh)) - 10, label=label, solved=solved)
        c.showPage()


# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser(
        description="Color-by-sum (math coloring) PDF generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--picture', default=None,
                   help=f'Picture name (default random). Available: {", ".join(PICTURES)}')
    p.add_argument('--max', type=int, default=10,
                   help='Largest number used in problems / answers (default 10)')
    p.add_argument('--op', choices=['add', 'sub', 'both'], default='add',
                   help='Operation(s) in the cells (default add)')
    p.add_argument('--count', type=int, default=1, help='Number of pages/pictures (default 1)')
    p.add_argument('--per-page', type=int, default=1, choices=[1, 2, 4],
                   help='Pictures per page (default 1)')
    p.add_argument('--solution', action='store_true', help='Add a colored answer-key section')
    p.add_argument('--title', default=None, help='Page title')
    p.add_argument('--out', default=None, help='Output PDF path')
    p.add_argument('--seed', type=int, default=None, help='Random seed (reproducible)')
    args = p.parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    names = list(PICTURES)
    if args.picture:
        if args.picture not in PICTURES:
            raise SystemExit(f"Unknown picture '{args.picture}'. Available: {', '.join(names)}")
        chosen = [args.picture] * args.count
    else:
        chosen = []
        while len(chosen) < args.count:
            pool = names[:]
            rng.shuffle(pool)
            chosen.extend(pool[:args.count - len(chosen)])

    title = args.title or "Color by Math"

    out_path = args.out
    if out_path is None:
        out_dir = Path(__file__).parent / 'worksheets'
        out_dir.mkdir(exist_ok=True)
        stamp = date.today().isoformat()
        out_path = out_dir / f'{stamp}_color_by_sum_{args.op}_max{args.max}.pdf'
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    puzzles = []
    for name in chosen:
        grid = parse_picture(PICTURES[name])
        problems, targets = build_puzzle(grid, args.max, args.op, rng)
        puzzles.append((grid, problems, targets, name))

    n_q_pages = (args.count + args.per_page - 1) // args.per_page
    total_pages = n_q_pages + (n_q_pages if args.solution else 0)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    draw_pages(c, puzzles, title, total_pages, args.per_page, solved=False, page_offset=0)
    if args.solution:
        draw_pages(c, puzzles, title + " — Answers", total_pages, args.per_page,
                   solved=True, page_offset=n_q_pages)
    c.save()

    print(f"Generated: {out_path}")
    print(f"  op={args.op}  max={args.max}  count={args.count}"
          f"  per_page={args.per_page}  solution={args.solution}")
    print(f"  pictures used: {', '.join(chosen)}")


if __name__ == '__main__':
    main()
