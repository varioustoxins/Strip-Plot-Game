"""Simulate the K7 1H-15N HSQC as real-looking data and save its contour plots as SVG assets.

A real HSQC is a grid of intensities drawn as contours, not a symbol per peak. Each peak in
assets/k7_hsqc.js (free) and assets/k7_ddx3_bound.js (DDX3 bound) becomes a 2D Gaussian with a
realistic line width (about 0.04 ppm in 1H, 0.4 ppm in 15N) and its own height; they are summed on
one grid with a little noise, so overlapping peaks merge as in real data, then contoured at levels
starting above the noise and stepping by x1.45. A peak keeps the same width and height in the free
and bound spectra; the shapes are random but seeded, so rebuilding gives the same pictures.

Writes (viewBox = the spectral window, 1H 11.0 -> 6.0 ppm left to right, 15N 100 -> 133 top to bottom):
  assets/hsqc_free.svg        free spectrum, black contours
  assets/hsqc_free_grey.svg   free spectrum, grey contours (underlay for the bound overlay)
  assets/hsqc_bound.svg       DDX3-bound spectrum, black contours
  assets/hsqc_shapes.js       each peak's lowest-contour ellipse (for label wedges that stop at the contours)
and a *_fine.svg of each with thinner lines, for the magnified inset of the crowded centre. Also
  assets/hnca_hca.svg         the HNCA's 1H-13C-alpha projection (1H 11.0 -> 6.0 ppm, 13C-alpha 42 -> 70 ppm top to
                              bottom), black contours (as the HSQC): each amide's Ca(i) peak and its weaker Ca(i-1) peak, with the same
                              1H widths and heights as in the HSQC

Contours are traced with contourpy (matplotlib's contouring engine: smooth, correctly joined lines).

Needs: numpy, contourpy.   Usage: python tools/make_hsqc_svg.py   (after the data tools)
"""
import json
from pathlib import Path

import numpy as np
from contourpy import LineType, contour_generator

ASSETS = Path(__file__).resolve().parent.parent / "assets"
H_RANGE, N_RANGE = (11.0, 6.0), (100.0, 133.0)     # must match H_RANGE / N_RANGE in index.html
CA_RANGE = (42.0, 70.0)                            # 13C-alpha, top to bottom: must match CUBE.ca in index.html
CA_SIGMA, PREV = 0.22, 0.55                        # Ca line width (sigma, ppm); Ca(i-1) height relative to Ca(i)
NX, NY = 900, 660                                  # grid points
LEVELS = [0.09 * 1.45 ** i for i in range(9)]
STROKE = 1.1                                       # in grid units (~0.9 px at the usual size)
FINE = STROKE / 2.5                                # for the magnified inset (drawn ~2.5x larger)


def load(name, var):
    src = (ASSETS / name).read_text()
    start = src.index(f"K7.{var} = ") + len(f"K7.{var} = ")
    return json.loads(src[start: src.rindex("}") + 1])["peaks"]


def key(p):
    return (p["seq"], p["kind"])


def shapes(peaks, rng):
    out = {}
    for p in peaks:
        flexible = p["seq"] <= 6 or p["seq"] >= 142          # floppy ends: sharper, taller peaks
        out[key(p)] = dict(a=1.4 + rng.random() * 0.6 if flexible else 0.45 + rng.random() * 0.75,
                           sh=0.012 if flexible else 0.016 + rng.random() * 0.008,   # sigma, ppm 1H
                           sn=0.12 if flexible else 0.15 + rng.random() * 0.08)      # sigma, ppm 15N
    return out


def grid(peaks, shape, rng):
    h = np.linspace(H_RANGE[0], H_RANGE[1], NX)
    n = np.linspace(N_RANGE[0], N_RANGE[1], NY)
    v = np.zeros((NY, NX))
    for p in peaks:
        s = shape[key(p)]
        v += s["a"] * np.outer(np.exp(-0.5 * ((n - p["n"]) / s["sn"]) ** 2),
                               np.exp(-0.5 * ((h - p["h"]) / s["sh"]) ** 2))
    return v + (rng.random(v.shape) - 0.5) * 0.03


def grid_hca(peaks, shape, rng):
    h = np.linspace(H_RANGE[0], H_RANGE[1], NX)
    c = np.linspace(CA_RANGE[0], CA_RANGE[1], NY)
    v = np.zeros((NY, NX))
    for p in peaks:
        if not (p.get("ca") and p.get("ca_prev")):
            continue
        s = shape[key(p)]
        across = np.exp(-0.5 * ((h - p["h"]) / s["sh"]) ** 2)
        for ca, f in ((p["ca"], 1.0), (p["ca_prev"], PREV)):
            v += f * s["a"] * np.outer(np.exp(-0.5 * ((c - ca) / CA_SIGMA) ** 2), across)
    return v + (rng.random(v.shape) - 0.5) * 0.03


def simplify(c, tol=0.2):
    """Ramer-Douglas-Peucker: drop points within tol grid units of the line (invisible on screen)."""
    if len(c) < 3:
        return c
    a, b = c[0], c[-1]
    ab = b - a
    if not ab.any():                                    # closed ring: split at the farthest point
        k = int(np.argmax(np.hypot(*(c - a).T)))
        return np.vstack([simplify(c[: k + 1], tol)[:-1], simplify(c[k:], tol)]) if 0 < k < len(c) - 1 else c
    d = np.abs(ab[0] * (c[:, 1] - a[1]) - ab[1] * (c[:, 0] - a[0])) / np.hypot(*ab)
    k = int(np.argmax(d))
    if d[k] <= tol:
        return np.vstack([a, b])
    return np.vstack([simplify(c[: k + 1], tol)[:-1], simplify(c[k:], tol)])


def svg(v, colour, stroke):
    gen = contour_generator(z=v, line_type=LineType.Separate)   # x = column, y = row, in grid units
    paths = []
    for level in LEVELS:
        for c in gen.lines(level):
            c = simplify(c)
            closed = np.allclose(c[0], c[-1])
            d = "M" + "L".join(f"{x:.1f},{y:.1f}" for x, y in c) + ("Z" if closed else "")
            paths.append(d)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {NX - 1} {NY - 1}" preserveAspectRatio="none">'
            f'<path fill="none" stroke="{colour}" stroke-width="{stroke}" stroke-linejoin="round" '
            f'd="{"".join(paths)}"/></svg>\n')


def main():
    free, bound = load("k7_hsqc.js", "free"), load("k7_ddx3_bound.js", "bound")
    shape = shapes(free, np.random.default_rng(15740))
    # each peak's shape, so the page can find exactly where its lowest contour lies: for a Gaussian of
    # height a and widths (sh, sn) ppm, the lowest level L is the ellipse with semi-axes sqrt(2 ln(a/L)) * (sh, sn)
    radii = {f"{seq}:{kind}": [round(float(np.sqrt(2 * np.log(v["a"] / LEVELS[0])) * v["sh"]), 4),
                               round(float(np.sqrt(2 * np.log(v["a"] / LEVELS[0])) * v["sn"]), 4)]
             for (seq, kind), v in shape.items()}
    # and in the 1H-13Ca projection: the 13C-alpha semi-axis of each amide's Ca(i) and Ca(i-1) peaks
    radii_ca = {f"{seq}:{kind}": [round(float(np.sqrt(2 * np.log(max(f * v["a"] / LEVELS[0], 1.01))) * CA_SIGMA), 4)
                                  for f in (1.0, PREV)] for (seq, kind), v in shape.items()}
    ln_a = {f"{seq}:{kind}": round(float(np.log(v["a"] / LEVELS[0])), 4) for (seq, kind), v in shape.items()}
    (ASSETS / "hsqc_shapes.js").write_text(
        "window.K7 = window.K7 || {};\n// written by tools/make_hsqc_svg.py: semi-axes (1H, 15N ppm) of each peak's "
        "lowest contour\nK7.footprint = " + json.dumps(radii) + ";\n"
        "// and the 13C-alpha semi-axes (ppm) of each amide's Ca(i) and Ca(i-1) peaks in the 1H-13Ca projection\n"
        "K7.footprintCA = " + json.dumps(radii_ca) + ";\n"
        "// ln(height / lowest contour level) of each peak, so the page can draw its contours as the nested ellipses\n"
        "// they are: the contour at LEVELS[k] has semi-axes footprint * sqrt(1 - k ln 1.45 / lnA)\n"
        "K7.peakLnA = " + json.dumps(ln_a) + ";\n")
    v_free, v_bound = grid(free, shape, np.random.default_rng(1)), grid(bound, shape, np.random.default_rng(2))
    for name, v, colour in [("hsqc_free", v_free, "#1d1d1f"), ("hsqc_free_grey", v_free, "#a3a3a8"),
                            ("hsqc_bound", v_bound, "#1d1d1f")]:
        for suffix, stroke in [("", STROKE), ("_fine", FINE)]:   # _fine: thinner lines for the zoomed inset
            out = ASSETS / f"{name}{suffix}.svg"
            out.write_text(svg(v, colour, stroke))
            print(f"{out.name}: {out.stat().st_size // 1024} KB")
    out = ASSETS / "hnca_hca.svg"
    out.write_text(svg(grid_hca(free, shape, np.random.default_rng(3)), "#1d1d1f", STROKE))
    print(f"{out.name}: {out.stat().st_size // 1024} KB")


if __name__ == "__main__":
    main()
