#!/usr/bin/env python3
"""
flow.py — printable "connect the dots" (Flow / Number Link) PDF generator.

Connect each pair of same-colored dots with a path. Paths can't cross, and
together they must fill every square in the grid. A spatial-logic cousin of the
maze. Each puzzle is generated from a real solution, so it's always solvable.

Examples:
  python3 flow.py                                   # 1 easy 5x5
  python3 flow.py --size 5 --count 4 --per-page 4 --solution
  python3 flow.py --size 6 --colors 5 --solution
  python3 flow.py --size 7 --count 2 --solution --seed 7
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


# color index -> rgb
COLORS = {
    1: (0.90, 0.27, 0.27),   # red
    2: (0.27, 0.50, 0.92),   # blue
    3: (0.27, 0.68, 0.36),   # green
    4: (0.96, 0.58, 0.18),   # orange
    5: (0.62, 0.38, 0.82),   # purple
    6: (0.15, 0.68, 0.68),   # teal
    7: (0.93, 0.45, 0.68),   # pink
    8: (0.55, 0.40, 0.25),   # brown
}

DIRS = [(1, 0), (-1, 0), (0, 1), (0, -1)]


# ---------- solution generation ----------

def hamiltonian_path(n, rng, tries=400):
    """Return a list of (x, y) visiting every cell once, or None.

    Randomized backtracking with a Warnsdorff-style 'fewest onward moves first'
    ordering, which finds a full path almost immediately on small grids.
    """
    total = n * n

    def neighbors(cell, visited):
        x, y = cell
        out = []
        for dx, dy in DIRS:
            nx, ny = x + dx, y + dy
            if 0 <= nx < n and 0 <= ny < n and (nx, ny) not in visited:
                out.append((nx, ny))
        return out

    for _ in range(tries):
        start = (rng.randrange(n), rng.randrange(n))
        visited = {start}
        path = [start]
        budget = [200000]

        def dfs(cur):
            if len(path) == total:
                return True
            if budget[0] <= 0:
                return False
            budget[0] -= 1
            nbrs = neighbors(cur, visited)
            # Warnsdorff: prefer moves that leave the fewest onward options
            rng.shuffle(nbrs)
            nbrs.sort(key=lambda c: len(neighbors(c, visited)))
            for nb in nbrs:
                visited.add(nb)
                path.append(nb)
                if dfs(nb):
                    return True
                path.pop()
                visited.discard(nb)
            return False

        if dfs(start):
            return path
    return None


def snake_path(n):
    """Boustrophedon fallback — always a valid Hamiltonian path."""
    path = []
    for y in range(n):
        xs = range(n) if y % 2 == 0 else range(n - 1, -1, -1)
        for x in xs:
            path.append((x, y))
    return path


def cut_into_segments(path, k, rng):
    """Split the path into k contiguous segments, each at least 2 cells long."""
    L = len(path)
    lengths = [2] * k
    extra = L - 2 * k
    for _ in range(extra):
        lengths[rng.randrange(k)] += 1
    segments = []
    i = 0
    for ln in lengths:
        segments.append(path[i:i + ln])
        i += ln
    return segments


def make_puzzle(n, k, rng):
    """Return list of segments (each a list of cells); segment index = color-1."""
    path = hamiltonian_path(n, rng) or snake_path(n)
    segs = cut_into_segments(path, k, rng)
    rng.shuffle(segs)   # so colors aren't laid out in path order
    return segs


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


def draw_flow(c, segments, n, x0, y0_top, max_w, max_h, label=None, solved=False):
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
    oy = oy_top - grid_h

    def center(cellxy):
        x, y = cellxy
        return ox + x * cell + cell / 2, oy + y * cell + cell / 2

    # solution paths (under the dots)
    if solved:
        c.setLineCap(1)   # round
        c.setLineJoin(1)
        for idx, seg in enumerate(segments):
            col = COLORS[(idx % len(COLORS)) + 1]
            c.setStrokeColorRGB(*col)
            c.setLineWidth(max(2.0, cell * 0.34))
            pts = [center(cl) for cl in seg]
            for a, b in zip(pts, pts[1:]):
                c.line(a[0], a[1], b[0], b[1])
        c.setLineWidth(1)
        c.setStrokeColorRGB(0, 0, 0)

    # grid lines
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.setLineWidth(0.7)
    for i in range(n + 1):
        c.line(ox + i * cell, oy, ox + i * cell, oy + grid_h)
        c.line(ox, oy + i * cell, ox + grid_w, oy + i * cell)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1.6)
    c.rect(ox, oy, grid_w, grid_h, stroke=1, fill=0)

    # endpoints: colored discs with the color number
    r = cell * 0.32
    fs = max(7.0, cell * 0.42)
    for idx, seg in enumerate(segments):
        col = COLORS[(idx % len(COLORS)) + 1]
        for cl in (seg[0], seg[-1]):
            cx, cy = center(cl)
            c.setFillColorRGB(*col)
            c.setStrokeColorRGB(0, 0, 0)
            c.setLineWidth(0.8)
            c.circle(cx, cy, r, stroke=1, fill=1)
            c.setFillColorRGB(1, 1, 1)
            c.setFont(ROMAN_BOLD, fs)
            c.drawCentredString(cx, cy - fs * 0.36, str(idx + 1))
    c.setFillColorRGB(0, 0, 0)
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
    """puzzles: list of (segments, n)."""
    n_items = len(puzzles)
    pages = (n_items + per_page - 1) // per_page
    for pi in range(pages):
        top_y = draw_page_header(c, title, pi + 1 + page_offset, total_pages)
        slots = slot_layout(per_page, top_y)
        for si, (sx, sy, sw, sh) in enumerate(slots):
            mi = pi * per_page + si
            if mi >= n_items:
                break
            segments, n = puzzles[mi]
            label = f"#{mi + 1}   ({n} × {n}, {len(segments)} colors)"
            draw_flow(c, segments, n, sx + 6, sy - 4, sw - 12, sh - 10,
                      label=label, solved=solved)
        c.showPage()


# ---------- CLI ----------

DEFAULT_COLORS = {5: 4, 6: 5, 7: 6}


def main():
    p = argparse.ArgumentParser(
        description="Flow / Number-Link PDF generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--size', type=int, default=5, choices=[5, 6, 7],
                   help='Grid size (default 5)')
    p.add_argument('--colors', type=int, default=None,
                   help='Number of color pairs (default by size)')
    p.add_argument('--count', type=int, default=1, help='Number of puzzles (default 1)')
    p.add_argument('--per-page', type=int, default=None, choices=[1, 2, 4],
                   help='Puzzles per page (default by size)')
    p.add_argument('--solution', action='store_true', help='Add an answer-key section')
    p.add_argument('--title', default=None, help='Page title')
    p.add_argument('--out', default=None, help='Output PDF path')
    p.add_argument('--seed', type=int, default=None, help='Random seed (reproducible)')
    args = p.parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    n = args.size
    k = args.colors if args.colors is not None else DEFAULT_COLORS[n]
    if k < 2:
        raise SystemExit("--colors must be at least 2.")
    if 2 * k > n * n:
        raise SystemExit(f"--colors {k} is too many for a {n}x{n} grid.")
    if k > len(COLORS):
        raise SystemExit(f"--colors max is {len(COLORS)}.")

    if args.per_page is None:
        args.per_page = 4 if n == 5 else 2

    title = args.title or f"Flow {n}×{n}"

    out_path = args.out
    if out_path is None:
        out_dir = Path(__file__).parent / 'worksheets'
        out_dir.mkdir(exist_ok=True)
        stamp = date.today().isoformat()
        out_path = out_dir / f'{stamp}_flow_{n}x{n}.pdf'
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    puzzles = [(make_puzzle(n, k, rng), n) for _ in range(args.count)]

    n_q_pages = (args.count + args.per_page - 1) // args.per_page
    total_pages = n_q_pages + (n_q_pages if args.solution else 0)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    draw_pages(c, puzzles, title, total_pages, args.per_page, solved=False, page_offset=0)
    if args.solution:
        draw_pages(c, puzzles, title + " — Answers", total_pages, args.per_page,
                   solved=True, page_offset=n_q_pages)
    c.save()

    print(f"Generated: {out_path}")
    print(f"  size={n}x{n}  colors={k}  count={args.count}"
          f"  per_page={args.per_page}  solution={args.solution}")
    print("  note: each puzzle has at least the shown solution (may not be unique).")


if __name__ == '__main__':
    main()
