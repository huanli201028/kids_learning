#!/usr/bin/env python3
"""
worksheet.py — Math practice PDF generator (no answer key).

Two ways to use it:

A) Quick single-section / single-type CLI:
   python3 worksheet.py --type oral --max 20
   python3 worksheet.py --type column --max 100 --carry
   python3 worksheet.py --type mixed --pages 3 --max 20

B) Multi-section config (JSON file) — put many sections on one page,
   with half-page / quarter-page splits and per-section parameters:
   python3 worksheet.py --config configs/daily.json

   Config shape (all keys optional except "type"):
   {
     "title": "Jamie's Daily Math",
     "out":   "worksheets/today.pdf",      # optional override
     "pages": [
       {
         "sections": [
           { "type": "oral",    "max": 20,  "count": 30 },
           { "type": "column",  "max": 100, "count": 6, "carry": true }
         ]
       },
       {
         "sections": [
           { "type": "missing", "max": 20, "count": 24,
             "label": "Find the missing number" }
         ]
       }
     ]
   }

   Section keys:
     type    : "oral" | "missing" | "column"
     max     : upper bound for operands/results (default 20)
     count   : number of problems in this section (defaults: oral=40, missing=24, column=16)
     op      : "add" | "sub" | "both"  (default "both")
     carry   : true | false            (default: max > 10)
     label   : custom section heading   (default auto-generated)
     weight  : float, controls vertical share of the page
               (default = count; equal sections all share evenly)
     cols    : override the grid column count
"""

import argparse
import json
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


# ---------- problem generators ----------

def _pick_add(max_val, allow_carry):
    for _ in range(200):
        a = random.randint(0, max_val)
        b = random.randint(0, max_val - a)
        if not allow_carry:
            if (a % 10) + (b % 10) >= 10:
                continue
            if max_val > 10 and (a // 10) + (b // 10) >= 10:
                continue
        return a, b
    return 0, 0


def _pick_sub(max_val, allow_borrow):
    for _ in range(200):
        a = random.randint(1, max_val)
        b = random.randint(0, a)
        if not allow_borrow and (a % 10) < (b % 10):
            continue
        return a, b
    return 1, 0


def gen_oral(max_val, op, carry, n):
    out, seen, attempts = [], set(), 0
    while len(out) < n and attempts < n * 80:
        attempts += 1
        chosen = op if op != 'both' else random.choice(['+', '-'])
        if chosen == '+':
            a, b = _pick_add(max_val, carry)
        else:
            a, b = _pick_sub(max_val, carry)
        if a == 0 and b == 0:
            continue
        if chosen == '-' and b == 0 and random.random() < 0.7:
            continue
        if chosen == '+' and (a == 0 or b == 0) and random.random() < 0.7:
            continue
        key = (chosen, a, b)
        if key in seen:
            continue
        seen.add(key)
        out.append(key)
    return out


def gen_missing(max_val, op, carry, n):
    """Returns [(op, a, b, c, slot)]. slot 0 → ___+b=c, slot 1 → a+___=c."""
    out, seen, attempts = [], set(), 0
    while len(out) < n and attempts < n * 100:
        attempts += 1
        chosen = op if op != 'both' else random.choice(['+', '-'])
        if chosen == '+':
            a, b = _pick_add(max_val, carry)
            c = a + b
        else:
            a, b = _pick_sub(max_val, carry)
            c = a - b
        slot = random.choice([0, 1])
        if slot == 0 and a == 0:
            continue
        if slot == 1 and b == 0:
            continue
        if c == 0 or c == a or c == b:
            if random.random() < 0.7:
                continue
        key = (chosen, a, b, slot)
        if key in seen:
            continue
        seen.add(key)
        out.append((chosen, a, b, c, slot))
    return out


def gen_column(max_val, op, carry, n):
    return gen_oral(max_val, op, carry, n)


GENERATORS = {
    'oral': gen_oral,
    'missing': gen_missing,
    'column': gen_column,
}

DEFAULT_COUNT = {'oral': 40, 'missing': 24, 'column': 16}
DEFAULT_COLS  = {'oral': 4,  'missing': 3,  'column': 4}

LABEL_TEMPLATE = {
    'oral':    'Mental Math',
    'missing': 'Find the Missing Number',
    'column':  'Column Addition / Subtraction',
}


def _auto_label(sec):
    base = LABEL_TEMPLATE[sec['type']]
    max_val = sec.get('max', 20)
    op = sec.get('op', 'both')
    op_str = {'add': 'addition', 'sub': 'subtraction', 'both': '+/-'}[op]
    carry = sec.get('carry')
    if carry is False:
        return f"{base} ({op_str}, within {max_val}, no carry/borrow)"
    return f"{base} ({op_str}, within {max_val})"


# ---------- PDF rendering ----------

def draw_page_header(c, title, page_num, total_pages):
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
                      f"{page_num} / {total_pages}")

    c.setLineWidth(0.4)
    c.line(MARGIN_X, y - 12, PAGE_W - MARGIN_X, y - 12)
    c.setLineWidth(1)

    return y - 22


def draw_section_label(c, label, x, y_top, width):
    """Returns y of available content top (below label band)."""
    if not label:
        return y_top - 2
    c.setFont(ROMAN_BOLD, 11)
    c.drawString(x, y_top - 12, label)
    c.setLineWidth(0.3)
    c.setStrokeColorRGB(0.55, 0.55, 0.55)
    c.line(x, y_top - 16, x + width, y_top - 16)
    c.setStrokeColorRGB(0, 0, 0)
    c.setLineWidth(1)
    return y_top - 22


def render_oral_box(c, problems, x, y_top, width, height, label=None, cols=4):
    content_top = draw_section_label(c, label, x, y_top, width)
    rows = max(1, (len(problems) + cols - 1) // cols)
    bottom = y_top - height
    avail_h = content_top - bottom
    row_h = avail_h / rows
    col_w = width / cols
    font_size = min(18.0, max(11.0, row_h * 0.55))

    for i, (op, a, b) in enumerate(problems):
        r = i // cols
        cidx = i % cols
        cx = x + cidx * col_w + 6
        cy = content_top - r * row_h - row_h * 0.6
        c.setFont(ROMAN, 8)
        c.drawString(cx, cy + font_size * 0.85, f"{i+1}.")
        c.setFont(ROMAN, font_size)
        text = f"{a} {op} {b} ="
        c.drawString(cx + 16, cy, text)
        line_x1 = cx + 16 + c.stringWidth(text, ROMAN, font_size) + 5
        line_x2 = cx + col_w - 8
        if line_x2 > line_x1:
            c.line(line_x1, cy - 2, line_x2, cy - 2)


def render_missing_box(c, problems, x, y_top, width, height, label=None, cols=3):
    content_top = draw_section_label(c, label, x, y_top, width)
    rows = max(1, (len(problems) + cols - 1) // cols)
    bottom = y_top - height
    avail_h = content_top - bottom
    row_h = avail_h / rows
    col_w = width / cols
    font_size = min(18.0, max(11.0, row_h * 0.55))

    for i, (op, a, b, cval, slot) in enumerate(problems):
        r = i // cols
        cidx = i % cols
        cx = x + cidx * col_w + 10
        cy = content_top - r * row_h - row_h * 0.6
        c.setFont(ROMAN, 8)
        c.drawString(cx - 8, cy + font_size * 0.85, f"{i+1}.")
        c.setFont(ROMAN, font_size)
        if slot == 0:
            text = f"___  {op}  {b}  =  {cval}"
        else:
            text = f"{a}  {op}  ___  =  {cval}"
        c.drawString(cx + 8, cy, text)


def render_column_box(c, problems, x, y_top, width, height, label=None, cols=4):
    content_top = draw_section_label(c, label, x, y_top, width)
    rows = max(1, (len(problems) + cols - 1) // cols)
    bottom = y_top - height
    avail_h = content_top - bottom
    row_h = avail_h / rows
    col_w = width / cols
    digit_size = min(22.0, max(13.0, row_h * 0.30))

    for i, (op, a, b) in enumerate(problems):
        r = i // cols
        cidx = i % cols
        cx = x + cidx * col_w
        cell_top = content_top - r * row_h
        c.setFont(ROMAN, 8)
        c.drawString(cx + 4, cell_top - 10, f"{i+1}.")
        right_x = cx + col_w * 0.72
        c.setFont(ROMAN, digit_size)
        y1 = cell_top - digit_size - 4
        c.drawRightString(right_x, y1, str(a))
        y2 = y1 - digit_size - 4
        c.drawString(cx + col_w * 0.18, y2, op)
        c.drawRightString(right_x, y2, str(b))
        line_y = y2 - 5
        line_x1 = cx + col_w * 0.15
        line_x2 = right_x + 6
        c.setLineWidth(1.2)
        c.line(line_x1, line_y, line_x2, line_y)
        c.setLineWidth(1)


RENDERERS = {
    'oral': render_oral_box,
    'missing': render_missing_box,
    'column': render_column_box,
}


# ---------- page-level layout ----------

def _resolve_section(sec):
    """Fill in defaults, return resolved dict."""
    s = dict(sec)  # copy
    t = s['type']
    if t not in GENERATORS:
        raise ValueError(f"Unknown section type: {t}")
    s.setdefault('max', 20)
    s.setdefault('op', 'both')
    s.setdefault('count', DEFAULT_COUNT[t])
    s.setdefault('cols', DEFAULT_COLS[t])
    if s.get('carry') is None:
        s['carry'] = s['max'] > 10
    s.setdefault('weight', s['count'])
    if not s.get('label'):
        s['label'] = _auto_label(s)
    return s


def render_page(c, page_spec, page_num, total_pages, page_title):
    top_y = draw_page_header(c, page_title, page_num, total_pages)
    bottom_y = MARGIN_BOT
    avail_h = top_y - bottom_y
    x = MARGIN_X
    width = PAGE_W - 2 * MARGIN_X

    sections = [_resolve_section(s) for s in page_spec.get('sections', [])]
    if not sections:
        return

    weights = [max(0.1, float(s['weight'])) for s in sections]
    total_w = sum(weights)

    y_cursor = top_y
    op_map = {'add': '+', 'sub': '-', 'both': 'both'}
    for sec, w in zip(sections, weights):
        sec_h = avail_h * (w / total_w)
        t = sec['type']
        op = op_map[sec['op']]
        problems = GENERATORS[t](sec['max'], op, sec['carry'], sec['count'])
        RENDERERS[t](c, problems, x, y_cursor, width, sec_h,
                     label=sec['label'], cols=sec['cols'])
        y_cursor -= sec_h


# ---------- config / CLI ----------

def normalize_config(config):
    """Accept several shapes and return {'title': ..., 'pages': [...]}."""
    if isinstance(config, list):
        return {'title': 'Math Practice', 'pages': [{'sections': config}]}
    if 'pages' in config:
        out = dict(config)
        out.setdefault('title', 'Math Practice')
        return out
    if 'sections' in config:
        return {'title': config.get('title', 'Math Practice'),
                'out': config.get('out'),
                'pages': [{'sections': config['sections']}]}
    if 'type' in config:
        return {'title': config.get('title', 'Math Practice'),
                'pages': [{'sections': [config]}]}
    raise ValueError("Config must contain 'pages', 'sections', or 'type'")


def build_config_from_cli(args):
    pages = []
    for i in range(args.pages):
        if args.type == 'mixed':
            t = ['oral', 'missing', 'column'][i % 3]
        else:
            t = args.type
        sec = {
            'type': t,
            'max': args.max,
            'op': args.op,
            'carry': args.carry,
            'count': args.count or DEFAULT_COUNT[t],
        }
        pages.append({'sections': [sec]})
    return {'title': args.title or 'Math Practice', 'pages': pages}


def main():
    p = argparse.ArgumentParser(
        description="Math practice PDF generator (no answer key).",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    p.add_argument('--config', default=None,
                   help='JSON config for multi-section / multi-page worksheets')
    p.add_argument('--type', choices=['oral', 'missing', 'column', 'mixed'],
                   default=None, help='Single-section quick mode')
    p.add_argument('--count', type=int, default=None, help='Problems per section')
    p.add_argument('--pages', type=int, default=1, help='Number of pages')
    p.add_argument('--max', type=int, default=20, help='Number upper bound (default 20)')
    p.add_argument('--op', choices=['add', 'sub', 'both'], default='both')
    p.add_argument('--carry', dest='carry', action='store_true',
                   help='Allow carry/borrow')
    p.add_argument('--no-carry', dest='carry', action='store_false',
                   help='Disallow carry/borrow')
    p.set_defaults(carry=None)
    p.add_argument('--title', default=None, help='Page title')
    p.add_argument('--out', default=None, help='Output PDF path')
    p.add_argument('--seed', type=int, default=None, help='Random seed (reproducible)')
    args = p.parse_args()

    if args.seed is not None:
        random.seed(args.seed)

    if args.config:
        with open(args.config) as f:
            cfg = json.load(f)
        cfg = normalize_config(cfg)
        suffix = Path(args.config).stem
    else:
        if not args.type:
            args.type = 'mixed'
        if args.carry is None:
            args.carry = args.max > 10
        cfg = build_config_from_cli(args)
        suffix = args.type

    out_path = args.out or cfg.get('out')
    if out_path is None:
        out_dir = Path(__file__).parent / 'worksheets'
        out_dir.mkdir(exist_ok=True)
        stamp = date.today().isoformat()
        out_path = out_dir / f'{stamp}_{suffix}.pdf'
    out_path = Path(out_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)

    title = cfg.get('title', 'Math Practice')
    pages = cfg['pages']
    total = len(pages)

    c = canvas.Canvas(str(out_path), pagesize=letter)
    for i, page_spec in enumerate(pages):
        render_page(c, page_spec, i + 1, total, title)
        c.showPage()
    c.save()

    print(f"Generated: {out_path}")
    print(f"  pages={total}  title={title!r}")


if __name__ == '__main__':
    main()
