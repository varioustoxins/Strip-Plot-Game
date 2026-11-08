"""Extract the 1D protein 1H spectrum line art from Gary's slides into assets/oned.js.

The "1D Protein NMR Spectrum" slide (a Keynote PDF) has the spectrum as vector polylines, an axis
labelled 11 ... -2 ppm, four region brackets (amide and aromatic, H-alpha, aliphatic, methyl) and two
picked-out amides, "a" and "b". This
reads those with PyMuPDF, converts the trace to (ppm, intensity 0..1) using the axis labels, and the
brackets to ppm ranges, so the page can draw the spectrum itself and animate it.

Needs: pymupdf.
Usage: python tools/extract_1d.py "path/to/slides.pdf" [page number, 1-based; default 28]
"""
import json
import sys
from pathlib import Path

import fitz  # PyMuPDF
import numpy as np

OUT = Path(__file__).resolve().parent.parent / "assets" / "oned.js"
BRACKETS = {"amide and aromatic": "amide", "Hα": "Hα", "aliphatic": "aliphatic", "methyl": "methyl"}
# corrections to the slide: the methyl bracket stops short of the far-right methyl peak (about -2 ppm)
TO_PPM = {"methyl": -2.5}


def main():
    pdf, page_no = sys.argv[1], int(sys.argv[2]) if len(sys.argv) > 2 else 28
    page = fitz.open(pdf)[page_no - 1]
    words = page.get_text("words")
    # the axis: ppm labels (integers) below the trace -> a linear fit of x against ppm
    ticks = [((w[0] + w[2]) / 2, int(w[4])) for w in words if w[4].lstrip("-").isdigit() and w[1] > 680]
    xs, ppms = np.array([t[0] for t in ticks]), np.array([t[1] for t in ticks])
    slope, icept = np.polyfit(ppms, xs, 1)                       # x = slope * ppm + icept
    to_ppm = lambda x: (x - icept) / slope                       # noqa: E731
    # the trace: the many thin black polylines with lots of points along the baseline region
    pts = []
    for d in page.get_drawings():
        if d["type"] == "s" and len(d["items"]) > 100:
            for it in d["items"]:
                if it[0] == "l":
                    pts += [(it[1].x, it[1].y), (it[2].x, it[2].y)]
                elif it[0] == "c":
                    pts += [(it[1].x, it[1].y), (it[4].x, it[4].y)]
    pts = sorted(set((round(x, 2), round(y, 2)) for x, y in pts))
    base, top = max(y for _, y in pts), min(y for _, y in pts)
    trace = [[round(to_ppm(x), 4), round((base - y) / (base - top), 4)] for x, y in pts]
    # the brackets: filled-and-stroked 3-segment shapes above the trace; each named by the label above it
    brackets = []
    for d in page.get_drawings():
        if d["type"] == "fs" and len(d["items"]) == 3:
            r = d["rect"]
            labels = [w[4] for w in words if r.x0 - 5 <= (w[0] + w[2]) / 2 <= r.x1 + 5 and r.y0 - 45 < w[3] <= r.y0 + 2]
            name = " ".join(labels)
            brackets.append(dict(name=name, from_ppm=round(to_ppm(r.x0), 3), to_ppm=round(to_ppm(r.x1), 3),
                                 height=round((base - r.y0) / (base - top), 3)))
    for b in brackets:
        b["to_ppm"] = TO_PPM.get(b["name"], b["to_ppm"])
    brackets.sort(key=lambda b: -b["from_ppm"])
    # the two picked-out amides: boxed letters "a" (solid) and "b" (dotted) above the amide region
    markers = []
    for w in words:
        if w[4] in ("a", "b") and 440 < w[1] < 520:
            x = (w[0] + w[2]) / 2
            near = [y for px, y in pts if abs(px - x) < 1.5]           # where the trace is under the marker
            markers.append(dict(name=w[4], ppm=round(to_ppm(x), 3), dotted=w[4] == "b",
                                label_height=round((base - (w[1] + w[3]) / 2) / (base - top), 3),
                                trace_height=round((base - min(near)) / (base - top), 3) if near else 0))
    markers.sort(key=lambda m: m["name"])
    data = dict(source=f"{Path(pdf).name}, page {page_no}", trace=trace, brackets=brackets, markers=markers,
                ppm_range=[round(to_ppm(min(x for x, _ in pts)), 3), round(to_ppm(max(x for x, _ in pts)), 3)])
    OUT.write_text("window.K7 = window.K7 || {};\n// written by tools/extract_1d.py from the 1D slide's line art\nK7.oneD = "
                   + json.dumps(data) + ";\n")
    print(f"{len(trace)} trace points, brackets: {[(b['name'], b['from_ppm'], b['to_ppm']) for b in brackets]} -> {OUT}")


if __name__ == "__main__":
    main()
