#!/usr/bin/env python3
"""Build clean strip PNGs (no dotted circles / connector lines) from the strip-game PDFs.

macOS only: needs pdftocairo (poppler), qlmanage and sips.
Geometry was measured from the PDFs with PyMuPDF (see tools/measure_strips.py).
"""
import re
import subprocess
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
OUT = ROOT / "assets"

PT_PER_PPM = 19.39          # 50 -> 70 ppm spans 387.82 pt on strip-game-4
TICK_50_BELOW_HEADER = 5.14 # 50 ppm sits this far below the header bottom
PPM_TOP, PPM_BOTTOM = 49.8, 71.0
INSET = 1.6                 # trim the PDF's own strip border lines

# (pdf, header x0, header x1, header bottom y, output name)
STRIPS = [
    ("strip-game-2.pdf", 74.0, 146.1, 261.09, "red"),
    ("strip-game-2.pdf", 260.0, 332.1, 266.93, "blue"),
    ("strip-game-2.pdf", 446.5, 518.6, 266.93, "green"),
    ("strip-game-1.pdf", 62.3, 134.4, 264.42, "orange"),
    ("strip-game-1.pdf", 269.9, 342.1, 264.42, "crimson"),
    ("strip-game-1.pdf", 431.3, 503.4, 264.42, "cyan"),
]

# horizontal recentring (pt) for strips whose peaks sit off the strip centre in the PDF
X_SHIFT = {"green": -1.25}

OVERLAYS = [r'stroke-dasharray=', r'stroke="rgb\(75\.212097%']
PX = 2400


def clean_svg(pdf: Path, tmp: Path) -> str:
    svg_path = tmp / (pdf.stem + ".svg")
    subprocess.run(["pdftocairo", "-svg", str(pdf), str(svg_path)], check=True)
    svg = svg_path.read_text()
    return re.sub(r'<path\b[^>]*/>',
                  lambda m: '' if any(re.search(p, m.group(0)) for p in OVERLAYS) else m.group(0),
                  svg)


def main():
    OUT.mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory() as t:
        tmp = Path(t)
        cleaned = {}
        for pdf, x0, x1, hb, name in STRIPS:
            if pdf not in cleaned:
                cleaned[pdf] = clean_svg(ROOT / pdf, tmp)
            y_top = hb + TICK_50_BELOW_HEADER + (PPM_TOP - 50) * PT_PER_PPM
            y_bot = hb + TICK_50_BELOW_HEADER + (PPM_BOTTOM - 50) * PT_PER_PPM
            x, w, h = x0 + INSET + X_SHIFT.get(name, 0), (x1 - x0) - 2 * INSET, y_bot - y_top
            # square canvas so qlmanage doesn't crop; strip is centred, sips trims the sides
            svg = re.sub(r'<svg\b[^>]*>',
                         f'<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
                         f'width="{h}pt" height="{h}pt" viewBox="{x} {y_top} {w} {h}" '
                         f'preserveAspectRatio="xMidYMid meet">', cleaned[pdf], count=1)
            src = tmp / f"{name}.svg"
            src.write_text(svg)
            subprocess.run(["qlmanage", "-t", "-s", str(PX), "-o", str(tmp), str(src)],
                           check=True, capture_output=True)
            png = OUT / f"{name}.png"
            subprocess.run(["sips", "-c", str(PX), str(round(PX * w / h)),
                            str(tmp / f"{name}.svg.png"), "--out", str(png)],
                           check=True, capture_output=True)
            print("wrote", png.relative_to(ROOT))


if __name__ == "__main__":
    main()
