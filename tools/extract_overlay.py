"""Read the K7 free / K7 + DDX3 peptide HSQC overlay (a PostScript plot, black and red contours) into the page's frame.

The plot draws its contours as line segments ("x y m  x y l") in plot coordinates, after a colour ("r g b
setrgbcolor"); the axes are labelled with ppm ticks: 1H along one edge and 15N along the other. This reads the
tick labels to get ppm = a + b * coordinate for each axis, converts every segment, and finds each peak's centre
(segments are joined into blobs on a fine grid; a blob's centre is the mean of its points).

Writes
  assets/k7_pept_black.svg, assets/k7_pept_red.svg   the two spectra as contour lines, in the same frame as the
                                                     simulated HSQCs (1H 11 -> 6 ppm across, 15N 100 -> 133 down),
                                                     and *_fine.svg with thin lines for magnified close-ups
  assets/k7_ddx3_bound.js                            K7.bound: the bound shift of every assigned amide (BMRB free
                                                     shift + the mapped move), for step 1's "+ DDX3" view and
                                                     tools/make_hsqc_svg.py
  assets/k7_pept_peaks.js                            K7.overlay = {black: [[h, n], ...], red: [...]}, and K7.peptide:
                                                     each assigned K7 amide (assets/k7_hsqc.js) followed from its
                                                     black (free) peak to the nearest red (with peptide) peak

Black is K7 on its own, red is K7 with the DDX3 peptide. The shifts are found by minimal shift mapping: each
free peak is matched to the nearest bound peak (red peaks may be shared), so each CSP is a lower bound, the
conservative choice. Peak positions are the centres of each colour's innermost contours.

Needs: numpy.  Usage: python tools/extract_overlay.py [path/to/overlay.ps]   (default: assets/k7_pept_overlay.ps)
"""
import json
import re
import sys
from pathlib import Path

import numpy as np

ASSETS = Path(__file__).resolve().parent.parent / "assets"
H_RANGE, N_RANGE = (11.0, 6.0), (100.0, 133.0)       # the page's HSQC frame
NX, NY = 900, 660                                    # its SVG viewBox (as tools/make_hsqc_svg.py)
NUM = r"(-?\d+\.?\d*)"
W_N = 0.14                                           # 15N weight in the combined shift (as the page's CSP)
CUTOFF = 0.08                                        # ppm: a move this big is significant (chosen by eye)


def axes(text):
    """ppm = a + b * coordinate for 1H (from x) and 15N (from y), fitted to the tick labels."""
    h = [(float(x), float(v)) for x, y, v in re.findall(NUM + r"\s+" + NUM + r"\s+moveto\s*\(\s*(\d+\.\d+)\)\s*NJ", text)]
    n = [(float(y), float(v)) for x, y, v in re.findall(NUM + r"\s+" + NUM + r"\s+moveto\s*\(\s*(\d{3})\)\s*EJ", text)]
    fit = lambda pts: np.polyfit([p[0] for p in pts], [p[1] for p in pts], 1)          # noqa: E731
    return fit(h), fit(n)


def segments(text):
    """Every contour segment, by colour: {colour: [(x1, y1, x2, y2), ...]} in plot coordinates."""
    out, colour, start = {}, None, None
    body = text[text.index("newpath"):]                  # after the axes
    for line in body.splitlines():
        line = line.strip()
        if line.endswith("setrgbcolor"):
            r, g, b = (float(v) for v in line.split()[:3])
            colour = "red" if r > 0.5 and g < 0.5 else "black"
        elif line.endswith(" m"):
            start = tuple(float(v) for v in line.split()[:2])
        elif line.endswith(" l") and start and colour:
            end = tuple(float(v) for v in line.split()[:2])
            out.setdefault(colour, []).append((*start, *end))
            start = end
    return out


def loops(ss):
    """Join a colour's segments into contour lines (by their shared end points)."""
    from collections import defaultdict
    key = lambda x, y: (round(x, 2), round(y, 2))                                         # noqa: E731
    ends = defaultdict(list)
    for k, (x1, y1, x2, y2) in enumerate(ss):
        ends[key(x1, y1)].append((k, key(x2, y2)))
        ends[key(x2, y2)].append((k, key(x1, y1)))
    used, out = set(), []
    for k, (x1, y1, x2, y2) in enumerate(ss):
        if k in used:
            continue
        used.add(k)
        line = [key(x1, y1), key(x2, y2)]
        for direction in (0, 1):                     # grow from both ends
            cur = line[-1] if direction == 0 else line[0]
            while True:
                nxt = [(kk, p) for kk, p in ends[cur] if kk not in used]
                if not nxt:
                    break
                kk, cur = nxt[0]
                used.add(kk)
                line.append(cur) if direction == 0 else line.insert(0, cur)
        out.append(np.array(line))
    return out


def centres(lines, ppm):
    """Peak maxima: the centres of the innermost contours (contour lines with no other line inside them)."""
    boxes = [(L[:, 0].min(), L[:, 0].max(), L[:, 1].min(), L[:, 1].max()) for L in lines]
    peaks = []
    for a, (x0, x1, y0, y1) in enumerate(boxes):
        inside = any(b != a and x0 <= bx0 and bx1 <= x1 and y0 <= by0 and by1 <= y1
                     for b, (bx0, bx1, by0, by1) in enumerate(boxes))
        if not inside:
            h, n = ppm(*lines[a].mean(0))
            peaks.append([round(float(h), 3), round(float(n), 2)])
    return peaks


def main():
    text = Path(sys.argv[1] if len(sys.argv) > 1 else ASSETS / "k7_pept_overlay.ps").read_text(errors="replace")
    (hb, ha), (nb, na) = axes(text)
    ppm = lambda x, y: (ha + hb * x, na + nb * y)                                          # noqa: E731
    gx = lambda h: (H_RANGE[0] - h) / (H_RANGE[0] - H_RANGE[1]) * (NX - 1)                # noqa: E731
    gy = lambda n: (n - N_RANGE[0]) / (N_RANGE[1] - N_RANGE[0]) * (NY - 1)                # noqa: E731
    segs, data = segments(text), {}
    for colour, ss in segs.items():
        d, pts = [], []
        for x1, y1, x2, y2 in ss:
            (h1, n1), (h2, n2) = ppm(x1, y1), ppm(x2, y2)
            pts += [(h1, n1), (h2, n2)]
            d.append(f"M{gx(h1):.1f},{gy(n1):.1f}L{gx(h2):.1f},{gy(n2):.1f}")
        stroke = "#c62828" if colour == "red" else "#1d1d1f"
        for suffix, width in (("", 1.1), ("_fine", 0.16)):   # _fine: thin lines, for close-ups magnified ~7x
            (ASSETS / f"k7_pept_{colour}{suffix}.svg").write_text(
                f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {NX - 1} {NY - 1}" preserveAspectRatio="none">'
                f'<path fill="none" stroke="{stroke}" stroke-width="{width}" stroke-linecap="round" d="{"".join(d)}"/></svg>\n')
        data[colour] = centres(loops(ss), ppm)
        print(f"{colour}: {len(ss)} segments, {len(data[colour])} peaks")
    # minimal shift mapping (conservative): each assigned amide's free peak (the black peak nearest its BMRB shifts)
    # is taken to have moved to the nearest red peak, so its CSP is the smallest it could be
    src = (ASSETS / "k7_hsqc.js").read_text()
    free = json.loads(src[src.index("K7.free = ") + 10: src.rindex("}") + 1])["peaks"]
    dist = lambda a, b: float(np.hypot(a[0] - b[0], W_N * (a[1] - b[1])))                # noqa: E731
    peaks = []
    for p in free:
        b = min(data["black"], key=lambda q: dist(q, (p["h"], p["n"])))
        r = min(data["red"], key=lambda q: dist(q, b))
        peaks.append(dict(seq=p["seq"], res=p["res"], kind=p["kind"], h=r[0], n=r[1], free_h=b[0], free_n=b[1],
                          csp=round(dist(b, r), 3)))
    peptide = dict(source="K7 with and without the DDX3 peptide (k7_pept_overlay.ps): black free, red bound; "
                          "minimal shift mapping", csp_weight_n=W_N, peaks=peaks)
    print(f"mapped {len(peaks)} amides")
    # the bound spectrum for step 1: each amide's BMRB free shift moved by its mapped move; "moved" above CUTOFF
    threshold = CUTOFF
    bound = dict(source="K7 + DDX3 peptide (k7_pept_overlay.ps), minimal shift mapping", placeholder=False,
                 csp_weight_n=W_N, csp_threshold=threshold,
                 peaks=[dict(seq=q["seq"], res=q["res"], kind=q["kind"], h=round(f["h"] + q["h"] - q["free_h"], 3),
                             n=round(f["n"] + q["n"] - q["free_n"], 2)) for f, q in zip(free, peaks)])
    (ASSETS / "k7_ddx3_bound.js").write_text("window.K7 = window.K7 || {};\n// written by tools/extract_overlay.py\nK7.bound = "
                                             + json.dumps(bound, indent=1) + ";\n")
    print(f"k7_ddx3_bound.js: cutoff {threshold} ppm")
    (ASSETS / "k7_pept_peaks.js").write_text(
        "window.K7 = window.K7 || {};\n// written by tools/extract_overlay.py: peak centres (1H, 15N ppm) in the "
        "K7 / K7 + DDX3 peptide overlay\nK7.overlay = " + json.dumps(data) + ";\nK7.peptide = " + json.dumps(peptide) + ";\n")


if __name__ == "__main__":
    main()
