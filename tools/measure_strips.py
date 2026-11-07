#!/usr/bin/env python3
"""Print the dotted-circle (assigned peak) positions in each strip of a strip-game PDF.

Needs PyMuPDF (pip install pymupdf). Output: strip header box, then for each circle its
13C ppm and horizontal position as a fraction of strip width.
"""
import sys
import pymupdf

PT_PER_PPM, TICK_50_BELOW_HEADER = 19.39, 5.14


def saturated(c):
    return c and max(c) - min(c) > 0.3


for path in sys.argv[1:]:
    page = pymupdf.open(path)[0]
    drawings = page.get_drawings()
    headers = sorted({(round(d["rect"].x0, 1), round(d["rect"].x1, 1), round(d["rect"].y1, 2),
                       '#%02x%02x%02x' % tuple(round(v * 255) for v in d["fill"]))
                      for d in drawings if saturated(d.get("fill")) and d["rect"].height < 40})
    circles = [d["rect"] for d in drawings
               if d.get("dashes") not in (None, "", "[] 0") and d["rect"].width > 20]
    print("==", path)
    for x0, x1, hb, colour in headers:
        print(f"{colour} x={x0}-{x1} header_bottom={hb}")
        for c in sorted(circles, key=lambda r: r.y0):
            cx = (c.x0 + c.x1) / 2
            if x0 < cx < x1:
                cy = (c.y0 + c.y1) / 2
                ppm = 50 + (cy - (hb + TICK_50_BELOW_HEADER)) / PT_PER_PPM
                print(f"   ppm={ppm:6.2f} xfrac={(cx - x0) / (x1 - x0):.3f}")
