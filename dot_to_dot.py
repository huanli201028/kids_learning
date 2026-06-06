#!/usr/bin/env python3
"""
dot_to_dot.py — printable connect-the-dots PDF generator for kids.

Connect the numbered dots in order (1 -> 2 -> 3 ...) and a picture appears.
Reinforces counting and number order. The answer key shows the finished line.

Examples:
  python3 dot_to_dot.py                                  # 1 random picture
  python3 dot_to_dot.py --shape star --solution
  python3 dot_to_dot.py --count 4 --per-page 4 --solution
  python3 dot_to_dot.py --count 2 --solution --seed 3
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


# ---------- shape library ----------
# Each shape: list of (x, y) points in [0,1] (y up), in connect order, plus a
# 'closed' flag (whether the last dot links back to the first).

def _star_points():
    pts = []
    cx, cy = 0.5, 0.5
    R, r = 0.48, 0.20
    for i in range(10):
        ang = math.pi / 2 + i * math.pi / 5      # start at top, go around
        rad = R if i % 2 == 0 else r
        pts.append((cx + rad * math.cos(ang), cy + rad * math.sin(ang)))
    return pts


def _heart_points(n=20):
    raw = []
    for i in range(n):
        t = math.pi / 2 - (i / n) * 2 * math.pi   # start at top dip, go clockwise
        x = 16 * (math.sin(t) ** 3)
        y = 13 * math.cos(t) - 5 * math.cos(2 * t) - 2 * math.cos(3 * t) - math.cos(4 * t)
        raw.append((x, y))
    xs = [p[0] for p in raw]
    ys = [p[1] for p in raw]
    minx, maxx = min(xs), max(xs)
    miny, maxy = min(ys), max(ys)
    span = max(maxx - minx, maxy - miny)
    return [((x - minx) / span * 0.9 + 0.05, (y - miny) / span * 0.9 + 0.05)
            for (x, y) in raw]


SHAPES = {
    'star': (_star_points(), True),
    'heart': (_heart_points(), True),
    'fish': ([
        (0.08, 0.50), (0.24, 0.70), (0.48, 0.74), (0.66, 0.63),
        (0.76, 0.58), (0.95, 0.82), (0.86, 0.50), (0.95, 0.18),
        (0.76, 0.42), (0.66, 0.37), (0.48, 0.26), (0.24, 0.30),
    ], True),
    'house': ([
        (0.20, 0.06), (0.20, 0.46), (0.08, 0.46), (0.50, 0.82),
        (0.92, 0.46), (0.80, 0.46), (0.80, 0.06),
    ], True),
    'cat': ([
        (0.22, 0.54), (0.18, 0.78), (0.10, 0.95), (0.33, 0.80),
        (0.50, 0.86), (0.67, 0.80), (0.90, 0.95), (0.82, 0.78),
        (0.78, 0.54), (0.68, 0.30), (0.50, 0.22), (0.32, 0.30),
    ], True),
    'rocket': ([
        (0.50, 0.95), (0.64, 0.56), (0.64, 0.26), (0.82, 0.10),
        (0.58, 0.16), (0.55, 0.05), (0.45, 0.05), (0.42, 0.16),
        (0.18, 0.10), (0.36, 0.26), (0.36, 0.56),
    ], True),
    'sailboat': ([
        (0.10, 0.32), (0.24, 0.12), (0.78, 0.12), (0.90, 0.32),
        (0.54, 0.32), (0.54, 0.88), (0.18, 0.40), (0.50, 0.40),
    ], False),
}


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


def draw_dots(c, shape, x0, y0_top, max_w, max_h, label=None, solved=False):
    points, closed = shape
    label_h = 16 if label else 0
    if label:
        c.setFont(ROMAN_BOLD, 11)
        c.drawString(x0, y0_top - 12, label)

    pad = 26   # room for number labels
    inner_w = max_w - 2 * pad
    inner_h = max_h - label_h - 8 - 2 * pad
    if inner_w <= 0 or inner_h <= 0:
        return
    side = min(inner_w, inner_h)
    ox = x0 + pad + (inner_w - side) / 2 + (max_w - 2 * pad - inner_w) / 2
    oy_top = y0_top - label_h - 4 - pad - (inner_h - side) / 2
    oy = oy_top - side

    def to_xy(pt):
        return ox + pt[0] * side, oy + pt[1] * side

    cx = sum(p[0] for p in points) / len(points)
    cy = sum(p[1] for p in points) / len(points)

    # solution line
    if solved:
        c.setStrokeColorRGB(0.20, 0.45, 0.85)
        c.setLineWidth(2.0)
        c.setLineCap(1)
        c.setLineJoin(1)
        seq = list(points) + ([points[0]] if closed else [])
        xy = [to_xy(p) for p in seq]
        for a, b in zip(xy, xy[1:]):
            c.line(a[0], a[1], b[0], b[1])
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)

    # dots + numbers
    for i, pt in enumerate(points):
        px, py = to_xy(pt)
        first = (i == 0)
        if first:
            c.setFillColorRGB(0.20, 0.65, 0.30)   # green start dot
        else:
            c.setFillColorRGB(0.15, 0.15, 0.18)
        c.circle(px, py, 2.2, stroke=0, fill=1)
        # number offset radially outward from the centroid
        dx, dy = pt[0] - cx, pt[1] - cy
        d = math.hypot(dx, dy) or 1.0
        lx = px + (dx / d) * 11
        ly = py + (dy / d) * 11
        c.setFont(ROMAN_BOLD, 10)
        if first:
            c.setFillColorRGB(0.20, 0.65, 0.30)
        else:
            c.setFillColorRGB(0, 0, 0)
        c.drawCentredString(lx, ly - 3.5, str(i + 1))
    c.setFillColorRGB(0, 0, 0)


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
    """puzzles: list of (shape, name)."""
    n_items = len(puzzles)
    pages = (n_items + per_page - 1) // per_page
    for pi in range(pages):
        top_y = draw_page_header(c, title, pi + 1 + page_offset, total_pages)
        slots = slot_layout(per_page, top_y)
        for si, (sx, sy, sw, sh) in enumerate(slots):
            mi = pi * per_page + si
            if mi >= n_items:
                break
            shape, name = puzzles[mi]
            label = f"#{mi + 1}   1 → {len(shape[0])}"
            draw_dots(c, shape, sx + 6, sy - 4, sw - 12, sh - 10,
                      label=label, solved=solved)
        c.showPage()


# ---------- CLI ----------

def main():
    p = argparse.ArgumentParser(
        description="Connect-the-dots PDF generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--shape', default=None,
                   help=f'Shape name (default random). Available: {", ".join(SHAPES)}')
    p.add_argument('--count', type=int, default=1, help='Number of puzzles (default 1)')
    p.add_argument('--per-page', type=int, default=2, choices=[1, 2, 4],
                   help='Puzzles per page (default 2)')
    p.add_argument('--solution', action='store_true', help='Add an answer-key section')
    p.add_argument('--title', default=None, help='Page title')
    p.add_argument('--out', default=None, help='Output PDF path')
    p.add_argument('--seed', type=int, default=None, help='Random seed (reproducible)')
    args = p.parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    names = list(SHAPES)
    if args.shape:
        if args.shape not in SHAPES:
            raise SystemExit(f"Unknown shape '{args.shape}'. Available: {', '.join(names)}")
        chosen = [args.shape] * args.count
    else:
        chosen = []
        while len(chosen) < args.count:
            pool = names[:]
            rng.shuffle(pool)
            chosen.extend(pool[:args.count - len(chosen)])

    title = args.title or "Connect the Dots"

    out_path = args.out
    if out_path is None:
        out_dir = Path(__file__).parent / 'worksheets'
        out_dir.mkdir(exist_ok=True)
        stamp = date.today().isoformat()
        out_path = out_dir / f'{stamp}_dot_to_dot.pdf'
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    puzzles = [(SHAPES[name], name) for name in chosen]

    n_q_pages = (args.count + args.per_page - 1) // args.per_page
    total_pages = n_q_pages + (n_q_pages if args.solution else 0)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    draw_pages(c, puzzles, title, total_pages, args.per_page, solved=False, page_offset=0)
    if args.solution:
        draw_pages(c, puzzles, title + " — Answers", total_pages, args.per_page,
                   solved=True, page_offset=n_q_pages)
    c.save()

    print(f"Generated: {out_path}")
    print(f"  count={args.count}  per_page={args.per_page}  solution={args.solution}")
    print(f"  shapes used: {', '.join(chosen)}")


if __name__ == '__main__':
    main()
