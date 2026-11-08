"""Measure the 13C shift of the assigned peaks directly from the strip images in assets/.

The dotted circles in the PDFs (tools/measure_strips.py) were placed by hand and can sit
~0.1-0.2 ppm off the peaks, so the game uses these image-measured centres instead:
  red  CA(i)   : centre of the innermost red HNCA contour
  black CA(i-1): centroid of the dark core of the black HNcoCA blob
Each search starts from a rough shift (the PDF circle value) and takes the nearest peak.

Needs: pillow, numpy, scipy.   Usage: python tools/measure_peaks.py
"""
from pathlib import Path

import numpy as np
from PIL import Image
from scipy import ndimage as nd

PPM_TOP, PPM_BOTTOM = 49.8, 71.0          # must match tools/build_strips.py
ROUGH = {"red": (58.84, 60.68), "blue": (57.13, 58.86), "green": (55.39, 57.37),
         "orange": (67.06, 55.44), "crimson": (56.63, 66.97), "cyan": (65.63, 56.62)}
ASSETS = Path(__file__).resolve().parent.parent / "assets"


def to_ppm(y, h):
    return PPM_TOP + y / h * (PPM_BOTTOM - PPM_TOP)


def window(a, ppm, half):
    h = a.shape[0]
    y0 = int((ppm - half - PPM_TOP) / (PPM_BOTTOM - PPM_TOP) * h)
    y1 = int((ppm + half - PPM_TOP) / (PPM_BOTTOM - PPM_TOP) * h)
    return a[y0:y1], y0, (ppm - PPM_TOP) / (PPM_BOTTOM - PPM_TOP) * h - y0


def red_peak(a, ppm):
    s, y0, yc = window(a, ppm, 1.2)
    w = a.shape[1]
    lines = (s[:, :, 0] > 110) & (s[:, :, 0] - s[:, :, 1] > 60)
    filled, n = nd.label(nd.binary_fill_holes(lines))
    near = min((np.hypot(*(np.array(nd.center_of_mass(filled == i)) - [yc, w / 2])), i)
               for i in range(1, n + 1) if (filled == i).sum() > 500)[1]
    peak = filled == near
    rings, m = nd.label(lines)
    inner = []
    for j in range(1, m + 1):
        ring = rings == j
        if peak[ring].all():
            area = nd.binary_fill_holes(ring)
            if area.sum() > 1.2 * ring.sum():      # a closed contour, not a stray fragment
                inner.append((area.sum(), j, area))
    ys, _ = np.nonzero(min(inner, key=lambda t: t[0])[2])
    return to_ppm(ys.mean() + y0, a.shape[0])


def black_peak(a, ppm):
    s, y0, yc = window(a, ppm, 1.0)
    w = a.shape[1]
    grey = s.max(axis=2)
    for level in (40, 60, 90, 120):                 # lighter blobs need a looser threshold
        dark = grey < level
        dark[:, : int(w * 0.3)] = dark[:, int(w * 0.7):] = False
        lab, n = nd.label(dark)
        cands = [(abs(nd.center_of_mass(lab == i)[0] - yc), i) for i in range(1, n + 1) if (lab == i).sum() > 50]
        if cands:
            ys, _ = np.nonzero(lab == min(cands)[1])
            return to_ppm(ys.mean() + y0, a.shape[0])
    raise ValueError("no black peak found")


for name, (ca_i, ca_im1) in ROUGH.items():
    a = np.asarray(Image.open(ASSETS / f"{name}.png").convert("RGB")).astype(int)
    print(f"{name:8s} ca_i={red_peak(a, ca_i):.2f}  ca_im1={black_peak(a, ca_im1):.2f}")
