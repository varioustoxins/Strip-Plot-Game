"""Read the chemical shift changes and helices from Fig. 6 of Kalverda et al. (J. Mol. Biol. 2009) into assets/k7_csp_paper.js.

Kalverda, Thompson, Vogel, Schröder, Bowie, Khan & Homans (2009). Poxvirus K7 protein adopts a Bcl-2 fold: biochemical
mapping of its interactions with human DEAD box RNA helicase DDX3. J. Mol. Biol. 385, 843-853. doi:10.1016/j.jmb.2008.09.048

The figure is a raster image in the paper's PDF. Its bar chart has tick marks every 10 residues along the bottom and
every 0.25 ppm up the left; each bar is black (below the 0.5 ppm cutoff) or magenta (above it), on a blue band
(below the cutoff) and grey bands (the helices). This finds the ticks, then for each residue the top of its bar and
its colour, and the ends of each grey band.

The paper numbers K7 from its full-length construct; that is the page's numbering (BMRB 15740, the strip game) plus
OFFSET (e.g. the paper's Trp36 is our Trp32): everything is written in the page's numbering.

Needs: pymupdf, numpy.  Usage: python tools/digitise_csp_figure.py path/to/1-s2.0-S0022283608011947-main.pdf
"""
import json
import sys
from pathlib import Path

import fitz
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "assets" / "k7_csp_paper.js"
PAGE, OFFSET = 7, 4                  # the figure's page (1-based); paper residue = page residue + OFFSET
HELICES = ["α1", "α2", "α3", "α5", "α6", "α7"]


def groups(values, gap=2):
    out = []
    for v in values:
        if out and v - out[-1][-1] <= gap:
            out[-1].append(v)
        else:
            out.append([v])
    return [float(np.mean(g)) for g in out]


def main():
    doc = fitz.open(sys.argv[1])
    xref = doc[PAGE - 1].get_images(full=True)[0][0]
    pix = fitz.Pixmap(doc, xref)
    if pix.n > 4:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    a = np.frombuffer(pix.samples, dtype=np.uint8).reshape(pix.height, pix.width, pix.n)[:, :, :3].astype(int)
    R, G, B = a[..., 0], a[..., 1], a[..., 2]
    dark = a.sum(2) < 250
    # the plot frame: the long vertical lines; its bottom axis is the lowest long horizontal line
    vlines = [x for x in range(pix.width) if dark[pix.height // 2:, x].sum() > 250]
    x_left, x_right = vlines[0], vlines[-1]
    hlines = [y for y in range(pix.height // 2, pix.height) if dark[y, x_left:x_right].sum() > 0.9 * (x_right - x_left)]
    y_axis = hlines[-1]
    # ticks: residues every 10 under the bottom axis; ppm every 0.25 left of the left axis
    xt = groups([x for x in range(x_left, x_right + 2) if dark[y_axis + 2:y_axis + 9, x].sum() >= 4])
    yt = groups([y for y in range(pix.height // 2, y_axis) if dark[y, x_left - 8:x_left - 1].sum() >= 4])
    res_per_px = 10 / np.mean(np.diff(xt)); x10 = xt[0]                       # the first tick is residue 10
    X = lambda r: x10 + (r - 10) / res_per_px                                  # noqa: E731
    y0, ppm_per_px = yt[-1], 0.25 / np.mean(np.diff(yt))                       # the last tick is 0 ppm
    # bars: black or magenta, standing on the 0 ppm line
    bar_px = (a.sum(2) < 230) | ((R > 100) & (G < 90) & (B > 90) & (R - G > 50))
    magenta = (R > 100) & (G < 90) & (B > 90) & (R - G > 50)
    bars = {}
    for r in range(2, 150):
        best, mag = 0.0, 0
        for x in range(int(round(X(r) - 1)), int(round(X(r) + 1)) + 1):
            y = int(y0) - 1
            if not bar_px[y, x]:
                continue
            while y > yt[0] and bar_px[y - 1, x]:
                y -= 1
            best = max(best, (y0 - y) * ppm_per_px)
            mag += magenta[y:int(y0), x].sum()
        if best > 0.01:
            bars[r - OFFSET] = dict(delta=round(best, 3), significant=bool(mag > 3))
    # helices: the grey bands. Each column between 1.3 and 2.1 ppm is called grey, white or bar (the few tall bars
    # cross the bands); a band is a run of grey columns, which bars may interrupt but white may not
    rows = [int(y0 - v / ppm_per_px) for v in np.linspace(1.3, 2.1, 9)]
    def kind(x):
        px = a[rows, x]
        greyish = np.all(np.abs(px - 211) < 25, axis=1).sum()
        white = np.all(px > 240, axis=1).sum()
        return "grey" if greyish >= 5 else "white" if white >= 5 else "bar"
    kinds = [kind(x) for x in range(x_left + 2, x_right - 1)] + ["white"]
    runs, start, last_grey = [], None, None
    for i, k in enumerate(kinds):
        x = i + x_left + 2
        if k == "grey":
            start = x if start is None else start
            last_grey = x
        elif k == "white" and start is not None:
            end = x - 1 if x - 1 - last_grey <= 12 else last_grey   # bars standing at a band's end are inside it
            if end - start > 8:
                runs.append((start, end))
            start = None
    to_res = lambda x: 10 + (x - x10) * res_per_px                             # noqa: E731
    helices = [[name, round(to_res(x0)) - OFFSET, round(to_res(x1)) - OFFSET] for name, (x0, x1) in zip(HELICES, runs)]
    data = dict(source="Kalverda et al. (2009) J. Mol. Biol. 385, 843-853, doi:10.1016/j.jmb.2008.09.048, Fig. 6, digitised (tools/digitise_csp_figure.py)",
                note=f"residues in the page's numbering (the paper's minus {OFFSET}); delta in ppm, cutoff 0.5",
                cutoff=0.5, offset=OFFSET, bars=bars, helices=helices)
    OUT.write_text("window.K7 = window.K7 || {};\n// written by tools/digitise_csp_figure.py\nK7.paperCSP = " + json.dumps(data) + ";\n")
    print(f"{len(bars)} bars, {sum(b['significant'] for b in bars.values())} significant; helices {helices} -> {OUT}")


if __name__ == "__main__":
    main()
