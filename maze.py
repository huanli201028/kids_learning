#!/usr/bin/env python3
"""
maze.py — printable maze PDF generator.

Examples:
  python3 maze.py                                # 1 medium maze, no solution
  python3 maze.py --difficulty easy --count 2 --per-page 2
  python3 maze.py --width 25 --height 30
  python3 maze.py --count 6 --per-page 4 --solution
  python3 maze.py --difficulty hard --solution --seed 42
"""

import argparse
import random
from collections import deque
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


# ---------- maze generation (recursive backtracker, iterative) ----------

DIRS = {
    'N': (0, 1, 'S'),
    'S': (0, -1, 'N'),
    'E': (1, 0, 'W'),
    'W': (-1, 0, 'E'),
}


def gen_maze(width, height, rng):
    """Return walls dict: walls[(x, y)] = {'N': bool, 'S': bool, 'E': bool, 'W': bool}.
    True = wall present. Coordinate (0, 0) is bottom-left."""
    walls = {(x, y): {'N': True, 'S': True, 'E': True, 'W': True}
             for x in range(width) for y in range(height)}
    visited = {(0, 0)}
    stack = [(0, 0)]
    while stack:
        x, y = stack[-1]
        cands = []
        for d, (dx, dy, opp) in DIRS.items():
            nx, ny = x + dx, y + dy
            if 0 <= nx < width and 0 <= ny < height and (nx, ny) not in visited:
                cands.append((d, opp, nx, ny))
        if not cands:
            stack.pop()
            continue
        d, opp, nx, ny = rng.choice(cands)
        walls[(x, y)][d] = False
        walls[(nx, ny)][opp] = False
        visited.add((nx, ny))
        stack.append((nx, ny))
    return walls


def solve_maze(walls, width, height, start, end):
    """BFS — return shortest path as list of (x, y) cells."""
    parent = {start: None}
    q = deque([start])
    while q:
        cur = q.popleft()
        if cur == end:
            break
        x, y = cur
        for d, (dx, dy, _) in DIRS.items():
            nx, ny = x + dx, y + dy
            if (0 <= nx < width and 0 <= ny < height
                    and not walls[(x, y)][d] and (nx, ny) not in parent):
                parent[(nx, ny)] = (x, y)
                q.append((nx, ny))
    if end not in parent:
        return []
    path, cur = [], end
    while cur is not None:
        path.append(cur)
        cur = parent[cur]
    return list(reversed(path))


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
    c.drawRightString(PAGE_W - MARGIN_X, MARGIN_BOT - 18,
                      f"{page_num} / {total}")
    c.setLineWidth(0.4)
    c.line(MARGIN_X, y - 12, PAGE_W - MARGIN_X, y - 12)
    c.setLineWidth(1)
    return y - 22


def _reset_colors(c):
    c.setFillColorRGB(0, 0, 0)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)


# ---------- cartoon icons ----------
# Each icon centered at (cx, cy) and roughly fits in a box ~2.0*size wide by 1.6*size tall.

def _draw_mouse(c, cx, cy, size):
    """Cute mouse facing right (into maze)."""
    bw, bh = size * 1.5, size * 0.95
    c.setFillColorRGB(0.68, 0.68, 0.72)
    c.setStrokeColorRGB(0.25, 0.25, 0.28)
    c.setLineWidth(0.7)
    c.ellipse(cx - bw / 2, cy - bh / 2, cx + bw / 2, cy + bh / 2,
              stroke=1, fill=1)
    hr = size * 0.42
    hcx = cx + bw / 2 - hr * 0.25
    hcy = cy + size * 0.05
    c.circle(hcx, hcy, hr, stroke=1, fill=1)
    er = size * 0.24
    c.circle(hcx - hr * 0.45, hcy + hr * 0.85, er, stroke=1, fill=1)
    c.circle(hcx + hr * 0.45, hcy + hr * 0.85, er, stroke=1, fill=1)
    c.setFillColorRGB(1.0, 0.7, 0.8)
    c.setStrokeColorRGB(1.0, 0.7, 0.8)
    c.circle(hcx - hr * 0.45, hcy + hr * 0.85, er * 0.55, stroke=0, fill=1)
    c.circle(hcx + hr * 0.45, hcy + hr * 0.85, er * 0.55, stroke=0, fill=1)
    c.setFillColorRGB(0, 0, 0)
    c.circle(hcx + hr * 0.4, hcy + hr * 0.1, size * 0.08, stroke=0, fill=1)
    c.setFillColorRGB(0.95, 0.3, 0.5)
    c.circle(hcx + hr * 0.95, hcy - hr * 0.1, size * 0.10, stroke=0, fill=1)
    c.setStrokeColorRGB(0.5, 0.5, 0.55)
    c.setLineWidth(1.3)
    p = c.beginPath()
    p.moveTo(cx - bw / 2 + size * 0.05, cy - size * 0.05)
    p.curveTo(cx - bw * 0.85, cy + size * 0.3,
              cx - bw * 0.9,  cy - size * 0.55,
              cx - bw * 0.45, cy - size * 0.6)
    c.drawPath(p, stroke=1, fill=0)
    _reset_colors(c)


def _draw_cheese(c, cx, cy, size):
    """Triangular cheese wedge with holes."""
    w, h = size * 1.6, size * 1.1
    c.setFillColorRGB(1.0, 0.82, 0.25)
    c.setStrokeColorRGB(0.6, 0.45, 0.05)
    c.setLineWidth(0.9)
    p = c.beginPath()
    p.moveTo(cx - w / 2,    cy - h / 2)
    p.lineTo(cx + w / 2,    cy - h / 2)
    p.lineTo(cx + w / 2,    cy + h / 2 - size * 0.1)
    p.lineTo(cx - w / 2 + size * 0.15, cy - h / 2 + size * 0.15)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    c.setFillColorRGB(0.85, 0.6, 0.1)
    c.setStrokeColorRGB(0.6, 0.45, 0.05)
    c.setLineWidth(0.5)
    for (rx, ry, rr) in [(0.15, -0.15, 0.10),
                         (0.45, -0.35, 0.08),
                         (0.30, 0.05, 0.07),
                         (0.55, -0.05, 0.06)]:
        c.circle(cx + size * rx, cy + size * ry, size * rr, stroke=1, fill=1)
    _reset_colors(c)


def _draw_car(c, cx, cy, size):
    """Simple cartoon car facing right."""
    body_w, body_h = size * 1.7, size * 0.55
    body_x = cx - body_w / 2
    body_y = cy - size * 0.05
    c.setFillColorRGB(0.85, 0.20, 0.20)
    c.setStrokeColorRGB(0.3, 0.05, 0.05)
    c.setLineWidth(0.8)
    c.roundRect(body_x, body_y, body_w, body_h, size * 0.15, stroke=1, fill=1)
    roof_w = body_w * 0.55
    roof_h = size * 0.45
    p = c.beginPath()
    p.moveTo(body_x + body_w * 0.18, body_y + body_h)
    p.lineTo(body_x + body_w * 0.30, body_y + body_h + roof_h)
    p.lineTo(body_x + body_w * 0.68, body_y + body_h + roof_h)
    p.lineTo(body_x + body_w * 0.78, body_y + body_h)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    c.setFillColorRGB(0.75, 0.9, 1.0)
    c.setStrokeColorRGB(0.3, 0.3, 0.3)
    c.setLineWidth(0.5)
    win_x = body_x + body_w * 0.34
    win_y = body_y + body_h + roof_h * 0.15
    win_w = body_w * 0.30
    win_h = roof_h * 0.65
    c.rect(win_x, win_y, win_w, win_h, stroke=1, fill=1)
    c.setFillColorRGB(0.1, 0.1, 0.1)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(0.6)
    wr = size * 0.18
    c.circle(body_x + body_w * 0.25, body_y, wr, stroke=1, fill=1)
    c.circle(body_x + body_w * 0.75, body_y, wr, stroke=1, fill=1)
    c.setFillColorRGB(0.7, 0.7, 0.7)
    c.circle(body_x + body_w * 0.25, body_y, wr * 0.4, stroke=0, fill=1)
    c.circle(body_x + body_w * 0.75, body_y, wr * 0.4, stroke=0, fill=1)
    _reset_colors(c)


def _draw_flag(c, cx, cy, size):
    """Checkered finish flag on a pole."""
    pole_x = cx - size * 0.55
    c.setStrokeColorRGB(0.2, 0.2, 0.2)
    c.setLineWidth(1.3)
    c.line(pole_x, cy - size * 0.8, pole_x, cy + size * 0.9)
    flag_w = size * 1.2
    flag_h = size * 0.8
    flag_x = pole_x
    flag_y = cy + size * 0.1
    cols, rows = 4, 3
    cell_w = flag_w / cols
    cell_h = flag_h / rows
    c.setStrokeColorRGB(0.15, 0.15, 0.15)
    c.setLineWidth(0.4)
    for i in range(cols):
        for j in range(rows):
            black = (i + j) % 2 == 0
            if black:
                c.setFillColorRGB(0.15, 0.15, 0.15)
            else:
                c.setFillColorRGB(1.0, 1.0, 1.0)
            c.rect(flag_x + i * cell_w, flag_y + j * cell_h,
                   cell_w, cell_h, stroke=1, fill=1)
    _reset_colors(c)


def _draw_rocket(c, cx, cy, size):
    """Rocket pointing right with flame trailing left."""
    body_w, body_h = size * 1.3, size * 0.7
    bx, by = cx - body_w / 2 + size * 0.1, cy - body_h / 2
    c.setFillColorRGB(0.95, 0.95, 0.97)
    c.setStrokeColorRGB(0.25, 0.25, 0.30)
    c.setLineWidth(0.8)
    # main body
    p = c.beginPath()
    p.moveTo(bx, by)
    p.lineTo(bx + body_w * 0.75, by)
    p.lineTo(bx + body_w,        cy)
    p.lineTo(bx + body_w * 0.75, by + body_h)
    p.lineTo(bx,                 by + body_h)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    # window
    c.setFillColorRGB(0.4, 0.7, 1.0)
    c.circle(bx + body_w * 0.55, cy, size * 0.15, stroke=1, fill=1)
    # top fin
    c.setFillColorRGB(0.85, 0.20, 0.20)
    c.setStrokeColorRGB(0.3, 0.05, 0.05)
    p = c.beginPath()
    p.moveTo(bx + body_w * 0.05, by + body_h)
    p.lineTo(bx + body_w * 0.30, by + body_h + size * 0.35)
    p.lineTo(bx + body_w * 0.35, by + body_h)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    # bottom fin
    p = c.beginPath()
    p.moveTo(bx + body_w * 0.05, by)
    p.lineTo(bx + body_w * 0.30, by - size * 0.35)
    p.lineTo(bx + body_w * 0.35, by)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    # flame
    c.setFillColorRGB(1.0, 0.55, 0.1)
    c.setStrokeColorRGB(0.9, 0.3, 0.0)
    p = c.beginPath()
    p.moveTo(bx, by + body_h * 0.2)
    p.lineTo(bx - size * 0.5, cy + size * 0.05)
    p.lineTo(bx, by + body_h * 0.5)
    p.lineTo(bx - size * 0.35, cy - size * 0.05)
    p.lineTo(bx, by + body_h * 0.8)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    _reset_colors(c)


def _draw_star(c, cx, cy, size):
    """5-pointed gold star."""
    import math
    R = size * 0.7
    r = R * 0.4
    c.setFillColorRGB(1.0, 0.82, 0.15)
    c.setStrokeColorRGB(0.7, 0.5, 0.0)
    c.setLineWidth(0.8)
    p = c.beginPath()
    for i in range(10):
        angle = -math.pi / 2 + i * math.pi / 5
        rad = R if i % 2 == 0 else r
        x = cx + rad * math.cos(angle)
        y = cy + rad * math.sin(angle)
        if i == 0:
            p.moveTo(x, y)
        else:
            p.lineTo(x, y)
    p.close()
    c.drawPath(p, stroke=1, fill=1)
    _reset_colors(c)


ICON_DRAWERS = {
    'mouse':  _draw_mouse,
    'cheese': _draw_cheese,
    'car':    _draw_car,
    'flag':   _draw_flag,
    'rocket': _draw_rocket,
    'star':   _draw_star,
}

THEMES = {
    'mouse':  ('mouse',  'cheese'),
    'car':    ('car',    'flag'),
    'rocket': ('rocket', 'star'),
}


def draw_maze(c, walls, width, height, x0, y0_top, max_w, max_h,
              label=None, solution=None, theme='mouse'):
    """Draw maze inside the box anchored at top-left (x0, y0_top), size (max_w, max_h).
    Start at top-left cell (0, height-1), End at bottom-right cell (width-1, 0).
    """
    start = (0, height - 1)
    end = (width - 1, 0)

    label_h = 16 if label else 0
    if label:
        c.setFont(ROMAN_BOLD, 11)
        c.drawString(x0, y0_top - 12, label)

    arrow_pad = 32  # horizontal padding for start/goal icons
    inner_w = max_w - 2 * arrow_pad
    inner_h = max_h - label_h - 8
    if inner_w <= 0 or inner_h <= 0:
        return

    cell = min(inner_w / width, inner_h / height)
    maze_w = cell * width
    maze_h = cell * height

    ox = x0 + arrow_pad + (inner_w - maze_w) / 2
    oy_top = y0_top - label_h - 4 - (inner_h - maze_h) / 2
    oy = oy_top - maze_h  # bottom-left of maze

    def cell_xy(cx, cy):
        return ox + cx * cell, oy + cy * cell

    # walls
    c.setLineWidth(1.4)
    c.setStrokeColorRGB(0, 0, 0)
    for cx in range(width):
        for cy in range(height):
            x_left, y_bot = cell_xy(cx, cy)
            x_right = x_left + cell
            y_top = y_bot + cell
            w = walls[(cx, cy)]
            # Open the west wall at start, east wall at end (for arrows to enter/exit)
            draw_w = w['W'] and (cx, cy) != start
            draw_e = w['E'] and (cx, cy) != end
            if w['S']:
                c.line(x_left, y_bot, x_right, y_bot)
            if draw_w:
                c.line(x_left, y_bot, x_left, y_top)
            if cy == height - 1 and w['N']:
                c.line(x_left, y_top, x_right, y_top)
            if cx == width - 1 and draw_e:
                c.line(x_right, y_bot, x_right, y_top)

    # solution overlay
    if solution:
        c.setStrokeColorRGB(0.85, 0.15, 0.15)
        c.setLineWidth(max(1.5, cell * 0.18))
        prev = None
        for (cx, cy) in solution:
            x_left, y_bot = cell_xy(cx, cy)
            px = x_left + cell / 2
            py = y_bot + cell / 2
            if prev:
                c.line(prev[0], prev[1], px, py)
            prev = (px, py)
        c.setStrokeColorRGB(0, 0, 0)
        c.setLineWidth(1)

    # start / end cartoon icons
    start_icon, end_icon = THEMES.get(theme, THEMES['mouse'])
    sx_left, sy_bot = cell_xy(*start)
    sy_mid = sy_bot + cell / 2
    ex_left, ey_bot = cell_xy(*end)
    ex_right = ex_left + cell
    ey_mid = ey_bot + cell / 2

    icon_size = min(14.0, max(8.0, cell * 0.55))
    ICON_DRAWERS[start_icon](c, sx_left - arrow_pad / 2, sy_mid, icon_size)
    ICON_DRAWERS[end_icon](c,   ex_right + arrow_pad / 2, ey_mid, icon_size)


# ---------- page layouts ----------

def slot_layout(per_page, top_y):
    usable_h = top_y - MARGIN_BOT
    usable_w = PAGE_W - 2 * MARGIN_X
    if per_page == 1:
        return [(MARGIN_X, top_y, usable_w, usable_h)]
    if per_page == 2:
        half = usable_h / 2
        return [
            (MARGIN_X, top_y,            usable_w, half),
            (MARGIN_X, top_y - half,     usable_w, half),
        ]
    if per_page == 4:
        half_w = usable_w / 2
        half_h = usable_h / 2
        return [
            (MARGIN_X,           top_y,           half_w, half_h),
            (MARGIN_X + half_w,  top_y,           half_w, half_h),
            (MARGIN_X,           top_y - half_h,  half_w, half_h),
            (MARGIN_X + half_w,  top_y - half_h,  half_w, half_h),
        ]
    raise ValueError(f"--per-page must be 1, 2, or 4 (got {per_page})")


def draw_mazes_pages(c, mazes, title, total_pages, per_page,
                     with_solution=False, page_offset=0):
    """mazes is a list of (walls, path, W, H, theme). Draw them across pages."""
    n = len(mazes)
    pages = (n + per_page - 1) // per_page
    for pi in range(pages):
        top_y = draw_page_header(c, title, pi + 1 + page_offset, total_pages)
        slots = slot_layout(per_page, top_y)
        for si, (sx, sy, sw, sh) in enumerate(slots):
            mi = pi * per_page + si
            if mi >= n:
                break
            walls, path, W, H, theme = mazes[mi]
            label = f"#{mi + 1}   ({W} × {H})"
            sol = path if with_solution else None
            draw_maze(c, walls, W, H, sx + 4, sy - 4, sw - 8, sh - 6,
                      label=label, solution=sol, theme=theme)
        c.showPage()


# ---------- CLI ----------

PRESETS = {
    'easy':   (12, 14),
    'medium': (18, 22),
    'hard':   (24, 30),
    'xl':     (32, 40),
}


def main():
    p = argparse.ArgumentParser(
        description="Maze PDF generator.",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--width', type=int, default=None,
                   help='Maze width in cells (overrides --difficulty)')
    p.add_argument('--height', type=int, default=None,
                   help='Maze height in cells (overrides --difficulty)')
    p.add_argument('--difficulty', choices=list(PRESETS), default='medium',
                   help=f'Preset size. Options: {", ".join(f"{k}={w}x{h}" for k,(w,h) in PRESETS.items())}')
    p.add_argument('--count', type=int, default=1, help='Number of mazes (default 1)')
    p.add_argument('--per-page', type=int, default=None, choices=[1, 2, 4],
                   help='Mazes per page (default: 1 if difficulty>=medium else 2)')
    p.add_argument('--solution', action='store_true',
                   help='Add a solutions section at the end')
    p.add_argument('--theme', choices=list(THEMES) + ['random'], default='mouse',
                   help='Start/goal cartoon: mouse→cheese, car→flag, rocket→star, '
                        'or "random" to mix across mazes (default mouse)')
    p.add_argument('--title', default='Maze', help='Page title (default "Maze")')
    p.add_argument('--out', default=None, help='Output PDF path')
    p.add_argument('--seed', type=int, default=None, help='Random seed (reproducible)')
    args = p.parse_args()

    rng = random.Random(args.seed) if args.seed is not None else random.Random()

    if args.width and args.height:
        W, H = args.width, args.height
    elif args.width or args.height:
        raise SystemExit("Specify both --width and --height, or neither.")
    else:
        W, H = PRESETS[args.difficulty]

    if args.per_page is None:
        # default: 1 for big mazes, 2 for easy
        args.per_page = 2 if args.difficulty == 'easy' and not args.width else 1

    out_path = args.out
    if out_path is None:
        out_dir = Path(__file__).parent / 'worksheets'
        out_dir.mkdir(exist_ok=True)
        stamp = date.today().isoformat()
        diff_tag = f'{W}x{H}' if args.width and args.height else args.difficulty
        out_path = out_dir / f'{stamp}_maze_{diff_tag}.pdf'
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    theme_names = list(THEMES)
    mazes = []
    for i in range(args.count):
        walls = gen_maze(W, H, rng)
        path = solve_maze(walls, W, H, (0, H - 1), (W - 1, 0))
        if args.theme == 'random':
            theme = rng.choice(theme_names)
        else:
            theme = args.theme
        mazes.append((walls, path, W, H, theme))

    n_q_pages = (args.count + args.per_page - 1) // args.per_page
    total_pages = n_q_pages + (n_q_pages if args.solution else 0)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    draw_mazes_pages(c, mazes, args.title, total_pages,
                     args.per_page, with_solution=False, page_offset=0)
    if args.solution:
        draw_mazes_pages(c, mazes, args.title + " — Solutions",
                         total_pages, args.per_page,
                         with_solution=True, page_offset=n_q_pages)
    c.save()

    print(f"Generated: {out_path}")
    print(f"  count={args.count}  size={W}x{H}  per_page={args.per_page}"
          f"  solution={args.solution}")


if __name__ == '__main__':
    main()
