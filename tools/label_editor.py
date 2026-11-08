"""Local label editor for the "Why assign?" HSQC: drag peak labels by hand, save their positions.

Opens a matplotlib window with the simulated K7 HSQC (same data and contours as
tools/make_hsqc_svg.py), with the same plot and callout shapes as the web page and labels sized
in the same proportion to them. Labels start where the page puts
them (a Python port of the page's placeLabels() annealing, same seed and inputs) unless a saved
position exists. Drag a label with the mouse; a Sparky-style wedge points back to its peak.

  Mode "peaks"  (peak-picked and assigned views): main spectrum (crowded centre greyed out) and, in a second
                pane beside it with the page's callout shape, the magnified centre.
  Mode "bound"  (+ DDX3 view): labels of the peaks that move on DDX3 binding, at the bound peak.

Panes: click a pane to make it the active one (blue frame); the scroll wheel (over a pane) or +/- zoom it,
and dragging on empty space pans it.
Labels are sized relative to their pane, so label-to-plot proportions match the page at any window
size and zoom; labels whose peak is out of view are hidden and can't be picked up.

Mouse: drag a label to move it; double-click a label or peak to switch its wedge on/off; press and hold
       on a peak to show its label and wedge in blue. Callout labels are kept inside the callout.
Keys:  m  switch mode     s  save     c  clear this mode's saved positions (back to automatic)
       a  wedges: aim at the label centre <-> attach at the nearest box corner or side centre
       d  the last label touched: stand-out style on/off (fully dark wedge, white round-cornered background)
       closing the window with unsaved changes asks (in the terminal) whether to save
       + / -  zoom the active pane     h (or the toolbar's house button)  reset the zoom

Saved to assets/hsqc_labels.js: only the labels you have moved away from their automatic spot, as
the offset (dH, dN) in ppm of the label centre from its peak, per mode and area ("main" / "inset").
The page uses these and places every other label automatically, exactly as the editor showed them.

Needs: numpy, contourpy, matplotlib.   Usage: python tools/label_editor.py
"""
import json
import math
import sys
from pathlib import Path

import matplotlib.pyplot as plt
from contourpy import LineType, contour_generator
from matplotlib.collections import LineCollection
from matplotlib.patches import Polygon
from matplotlib.text import Text
import numpy as np

sys.path.insert(0, str(Path(__file__).resolve().parent))
import make_hsqc_svg as spec  # noqa: E402  (same grid, ranges and peak shapes as the SVG assets)

ASSETS = spec.ASSETS
OUT = ASSETS / "hsqc_labels.js"
DPI = 100
# --- page geometry at scale 1: must match index.html (SPEC_BASE, drawHSQC, INSET) ---
W, H = 860, 740
MARGIN = dict(l=8, r=52, t=8, b=40)
INSET_SRC = dict(h=(8.55, 7.5), n=(115.55, 122.45))   # same shape as the whole spectrum
INSET_BOX = dict(h=(10.95, 9.5), n=(100.5, 114.6))   # right edge clear of the peaks (and @94's label) near 9 ppm
CALLOUT_ZOOM = 2.6                         # fixed magnification (index.html INSET.zoom)
FS, GAP = 11.5, 6.0                       # label font size and gap, px
WEIGHT_N, THRESHOLD = 1 / 7, 0.5          # conservative shift mapping, as in the bound data
ONE = dict(ALA="A", ARG="R", ASN="N", ASP="D", CYS="C", GLN="Q", GLU="E", GLY="G", HIS="H", ILE="I",
           LEU="L", LYS="K", MET="M", PHE="F", PRO="P", SER="S", THR="T", TRP="W", TYR="Y", VAL="V")


def key(p):
    return f'{p["seq"]}:{p["kind"]}'


def name(p):
    return f'W{p["seq"]}ε' if p["kind"] == "indole" else f'{ONE.get(p["res"], "?")}{p["seq"]}'


# ---------------------------------------------------------------- page geometry
def fx(h):
    return (spec.H_RANGE[0] - h) / (spec.H_RANGE[0] - spec.H_RANGE[1])


def fy(n):
    return (n - spec.N_RANGE[0]) / (spec.N_RANGE[1] - spec.N_RANGE[0])


def geometry(use_inset):
    """Plot and callout rectangles in page px, as drawHSQC() computes them at scale 1."""
    m = dict(MARGIN)
    sfw, sfh = fx(INSET_SRC["h"][1]) - fx(INSET_SRC["h"][0]), fy(INSET_SRC["n"][1]) - fy(INSET_SRC["n"][0])
    bfw, bfh = fx(INSET_BOX["h"][1]) - fx(INSET_BOX["h"][0]), fy(INSET_BOX["n"][1]) - fy(INSET_BOX["n"][0])
    z0 = CALLOUT_ZOOM
    spill_x = max(0, sfw * z0 - bfw) if use_inset else 0
    spill_y = max(0, sfh * z0 - bfh) if use_inset else 0
    pw, ph = (W - m["l"] - m["r"]) / (1 + spill_x), (H - m["t"] - m["b"]) / (1 + spill_y)
    m["l"] += spill_x * pw
    m["t"] += spill_y * ph
    X = lambda h: m["l"] + fx(h) * pw  # noqa: E731
    Y = lambda n: m["t"] + fy(n) * ph  # noqa: E731
    sx0, sx1, sy0, sy1 = X(INSET_SRC["h"][0]), X(INSET_SRC["h"][1]), Y(INSET_SRC["n"][0]), Y(INSET_SRC["n"][1])
    iw, ih = sfw * z0 * pw, sfh * z0 * ph
    ix, iy = X(INSET_BOX["h"][1]) - iw, Y(INSET_BOX["n"][1]) - ih
    return dict(m=m, pw=pw, ph=ph, X=X, Y=Y, src=(sx0, sx1, sy0, sy1), inset=(ix, iy, iw, ih),
                to_inset=lambda x, y: (ix + (x - sx0) / (sx1 - sx0) * iw, iy + (y - sy0) / (sy1 - sy0) * ih))


# ---------------------------------------------------------------- port of the page's placeLabels()
def lead(px, py, box, rx, ry, gap=GAP):
    """The wedge rule (page leadFor): none for a label close to its peak and up-left of it, otherwise a
    leader from the peak centre aimed at the label's centre, ending at the edge of the label's box.
    Screen-style coords (y down)."""
    x, y, w, h = box
    cx, cy = x + w / 2, y + h / 2
    near = math.hypot(cx - px, cy - py) <= math.hypot(w / 2, h / 2) + math.hypot(rx, ry) + gap
    if near and cx < px and cy < py:
        return None
    return (px, py) + box_edge(px, py, box)


ATTACH = "centre"   # wedge attachment (page: K7.labelStyle.attach): "centre" or "anchor"; key a switches it


def box_edge(px, py, box):
    """where a wedge meets its label: "centre" = where the line from the peak (px, py) to the label's centre
    crosses the box edge; "anchor" = whichever box corner or side centre is nearest the peak"""
    x, y, w, h = box
    if ATTACH == "anchor":
        pts = [(ax, ay) for ax in (x, x + w / 2, x + w) for ay in (y, y + h / 2, y + h)
               if not (ax == x + w / 2 and ay == y + h / 2)]
        return min(pts, key=lambda q: math.hypot(q[0] - px, q[1] - py))
    cx, cy = x + w / 2, y + h / 2
    dx, dy = cx - px, cy - py
    s = min(1, w / 2 / abs(dx) if dx else math.inf, h / 2 / abs(dy) if dy else math.inf)
    return (cx - dx * s, cy - dy * s)
def mulberry32(seed):
    state = [seed & 0xFFFFFFFF]

    def rnd():
        s = (state[0] + 0x6D2B79F5) & 0xFFFFFFFF
        state[0] = s
        t = ((s ^ (s >> 15)) * (1 | s)) & 0xFFFFFFFF
        t = ((t + (((t ^ (t >> 7)) * (61 | t)) & 0xFFFFFFFF)) & 0xFFFFFFFF) ^ t
        return ((t ^ (t >> 14)) & 0xFFFFFFFF) / 4294967296
    return rnd


def place_labels(labels, bounds, peaks, rx, ry, forbid):
    """labels: [dict(x, y, t)] in px. Returns the chosen box (x, y, w, h) for each label."""
    n = len(labels)
    if not n:
        return []
    cw, h = FS * 0.66, FS * 1.15     # label box: measured text size (page placeLabels too)

    def hit(a, b):
        return a[0] < b[0] + b[2] and b[0] < a[0] + a[2] and a[1] < b[1] + b[3] and b[1] < a[1] + a[3]

    def lead_for(L, c):
        return lead(L["x"], L["y"], (c["x"], c["y"], c["w"], c["h"]), rx, ry)

    dirs = [(-1, -1), (0, -1), (-1, 0), (1, -1), (-1, 1), (1, 0), (0, 1), (1, 1)]
    rings = [0.9, 1.6, 2.4, 3.3]          # must match placeLabels() in index.html
    cands = []
    for L in labels:
        w, lst = len(L["t"]) * cw, []
        for ri, r in enumerate(rings):
            for di, (dx, dy) in enumerate(dirs):
                ax, ay = L["x"] + dx * (rx + GAP * r), L["y"] + dy * (ry + GAP * r)
                c = dict(x=ax if dx > 0 else ax - w if dx < 0 else ax - w / 2,
                         y=ay if dy > 0 else ay - h if dy < 0 else ay - h / 2, w=w, h=h, ri=ri)
                box = (c["x"], c["y"], w, h)
                u = ri * 3 + di * 0.3
                if c["x"] < bounds[0] or c["y"] < bounds[1] or c["x"] + w > bounds[0] + bounds[2] or c["y"] + h > bounds[1] + bounds[3]:
                    u += 40
                u += 40 * sum(hit(box, f) for f in forbid)
                u += 4 * sum(hit(box, (px - rx, py - ry, 2 * rx, 2 * ry)) for px, py in peaks)
                c["u"], c["box"] = u, box
                c["lead"] = lead_for(L, c)
                lst.append(c)
        cands.append(lst)

    def sign(v):
        return (v > 0) - (v < 0)

    def cross(a, b):
        if not a or not b:
            return False
        o = lambda p, q, r: sign((q[0] - p[0]) * (r[1] - p[1]) - (q[1] - p[1]) * (r[0] - p[0]))  # noqa: E731
        p1, p2, p3, p4 = (a[0], a[1]), (a[2], a[3]), (b[0], b[1]), (b[2], b[3])
        return o(p1, p2, p3) != o(p1, p2, p4) and o(p3, p4, p1) != o(p3, p4, p2)

    def seg_box(sg, b):
        if not sg:
            return False
        t0, t1 = 0.0, 1.0
        dx, dy = sg[2] - sg[0], sg[3] - sg[1]
        for p, q in ((-dx, sg[0] - b[0]), (dx, b[0] + b[2] - sg[0]), (-dy, sg[1] - b[1]), (dy, b[1] + b[3] - sg[1])):
            if p == 0:
                if q < 0:
                    return False
                continue
            r = q / p
            if p < 0:
                t0 = max(t0, r)
            else:
                t1 = min(t1, r)
            if t0 > t1:
                return False
        return True

    pick = [0] * n

    def local(i, c):
        v = c["u"]
        for j in range(n):
            if j == i:
                continue
            o = cands[j][pick[j]]
            if hit(c["box"], o["box"]):
                v += 12
            if cross(c["lead"], o["lead"]):
                v += 4
            if seg_box(c["lead"], o["box"]) or seg_box(o["lead"], c["box"]):
                v += 10
        return v

    rnd = mulberry32(7)
    T = 3.0
    steps = 80 * n
    cool = (0.01 / T) ** (1 / steps)
    for _ in range(steps):
        i = math.floor(rnd() * n)
        c = math.floor(rnd() * len(cands[i]))
        if c != pick[i]:
            d = local(i, cands[i][c]) - local(i, cands[i][pick[i]])
            if d <= 0 or rnd() < math.exp(-d / T):
                pick[i] = c
        T *= cool
    return [cands[i][pick[i]]["box"] for i in range(n)]


# ---------------------------------------------------------------- the page's label texts
def shuffle(a, rnd):
    """the page's Fisher-Yates shuffle (index.html shuffle()), driven by a seeded mulberry32"""
    for i in range(len(a) - 1, 0, -1):
        j = math.floor(rnd() * (i + 1))
        a[i], a[j] = a[j], a[i]
    return a


def peak_labels(free):
    """the page's @n labels (drawLabels): a fixed shuffle of 1-150 over the peaks"""
    pool = shuffle(list(range(1, 151)), mulberry32(150))
    return {key(p): f"@{pool[i]}" for i, p in enumerate(free)}


def example_names(free):
    """the page's example assignment (drawExampleAssignment): residue names shuffled among the peaks"""
    out, rnd = {}, mulberry32(2)
    for kind in ("backbone", "indole"):
        lst = [p for p in free if p["kind"] == kind]
        while True:
            names = shuffle([name(p) for p in lst], rnd)
            if not any(130 <= p["seq"] <= 135 and names[i] == name(p) for i, p in enumerate(lst)):
                break
        out.update({key(p): names[i] for i, p in enumerate(lst)})
    return out


# ---------------------------------------------------------------- Sparky-style wedge
class LabelWedge(Polygon):
    """Wedge from a label back to its peak, as the page draws it (placeLabels/leadFor): a point at the
    edge of the peak, a base FS*0.16 either side at the nearest point of the label box. The shape is
    worked out when it is drawn, from the renderer and transforms of that moment, so it is right after
    any zoom, pan, drag, window resize or (Retina) resolution change. Only drawn when the label is far
    enough from its peak to need one (the page's rule for hand-placed labels)."""

    def __init__(self, ann, at):
        super().__init__([[0, 0]] * 3, closed=True, fc="#888", ec="none", alpha=0.7, zorder=2.5)   # under the labels
        self.ann, self.at, self.shown = ann, at, False

    def draw(self, renderer):
        ann, ax = self.ann, self.ann.axes
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
        if not (min(x0, x1) <= self.at[0] <= max(x0, x1) and min(y0, y1) <= self.at[1] <= max(y0, y1)):
            return                                                    # peak out of view: label hidden too
        zoom = ax._span0 / abs(x1 - x0)
        scale = ax.get_window_extent(renderer).width / ax._page_w * zoom   # screen px per page px
        bb = Text.get_window_extent(ann, renderer)
        if ann._solid and ann.get_bbox_patch() is not None:   # stand-out label: end at its white background
            ann.update_bbox_position_size(renderer)
            bb = ann.get_bbox_patch().get_window_extent(renderer)
        H = self.figure.bbox.height                                   # display y is up; the page's is down
        px, py = ax.transData.transform(self.at)
        rx, ry = ax._r_page[0] * scale, ax._r_page[1] * scale
        box = (bb.x0, H - bb.y1, bb.width, bb.height)
        L = lead(px, H - py, box, rx, ry, GAP * scale)
        if self.ann._force is not None:                               # switched on/off by double-click
            L = (px, H - py) + box_edge(px, H - py, box) if self.ann._force else None
        self.shown = L is not None
        if L is None:
            return                                                    # close and up-left: no wedge
        x0, y0, x1, y1 = L[0], H - L[1], L[2], H - L[3]               # peak centre -> label end
        if math.hypot(x1 - x0, y1 - y0) < 1e-6:
            return                                                    # peak under its own label: no wedge
        d = math.hypot(x1 - x0, y1 - y0) or 1
        half = FS * 0.16 * scale
        wx, wy = -(y1 - y0) / d * half, (x1 - x0) / d * half
        # where the ray leaves the peak's lowest contour (an ellipse, semi-axes in ppm -> screen px)
        eh, en = self.ann._foot
        ex = abs(ax.transData.transform((self.at[0] + eh, self.at[1]))[0] - px)
        ey = abs(ax.transData.transform((self.at[0], self.at[1] + en))[1] - py)
        ux, uy = (x1 - x0) / d, (y1 - y0) / d
        f = min(1, 1 / math.hypot(ux / ex, uy / ey) / d)
        mx, my = x0 + (x1 - x0) * f, y0 + (y1 - y0) * f
        inv = ax.transData.inverted()
        outer = [(mx + wx * f, my + wy * f), (x1 + wx, y1 + wy), (x1 - wx, y1 - wy), (mx - wx * f, my - wy * f)]
        inner = [(x0, y0), (mx + wx * f, my + wy * f), (mx - wx * f, my - wy * f)]
        colour = self.get_facecolor()
        if self.ann._solid:   # stand-out label: the whole wedge dark
            self.set_xy(inv.transform([(x0, y0), (x1 + wx, y1 + wy), (x1 - wx, y1 - wy)]))
            self.set_alpha(0.9)
            super().draw(renderer)
            return
        self.set_xy(inv.transform(outer))
        self.set_alpha(0.7)
        super().draw(renderer)
        self.set_xy(inv.transform(inner))                             # inside the contours: lighter
        self.set_alpha(0.25)
        super().draw(renderer)
        self.set_facecolor(colour)


# ---------------------------------------------------------------- the editor
def load_saved():
    """(labels, style) from assets/hsqc_labels.js"""
    if not OUT.exists():
        return {}, {}
    src = OUT.read_text()

    def part(name):
        tag = f"K7.{name} = "
        if tag not in src:
            return {}
        start = src.index(tag) + len(tag)
        return json.loads(src[start: src.index(";\n", start)])
    return part("labels"), part("labelStyle")


def entry_options(entry):
    """optional third value of a saved entry: {"wedge": 1/0, "solid": 1} (older files: a bare 1/0)"""
    if len(entry) < 3:
        return {}
    return entry[2] if isinstance(entry[2], dict) else {"wedge": entry[2]}


class Editor:
    def __init__(self):
        self.free = spec.load("k7_hsqc.js", "free")
        self.bound = {key(p): p for p in spec.load("k7_ddx3_bound.js", "bound")}
        shape = spec.shapes(self.free, np.random.default_rng(15740))
        self.v_free = spec.grid(self.free, shape, np.random.default_rng(1))
        self.v_bound = spec.grid(list(self.bound.values()), shape, np.random.default_rng(2))
        # each peak's lowest contour: ellipse semi-axes (ppm), as in assets/hsqc_shapes.js
        self.foot = {f"{seq}:{kind}": (math.sqrt(2 * math.log(v["a"] / spec.LEVELS[0])) * v["sh"],
                                       math.sqrt(2 * math.log(v["a"] / spec.LEVELS[0])) * v["sn"])
                     for (seq, kind), v in shape.items()}
        global ATTACH
        self.saved, self.style = load_saved()
        ATTACH = self.style.get("attach", "centre")
        self.last = None   # the label most recently touched (key d acts on it)
        self.at_n, self.example = peak_labels(self.free), example_names(self.free)
        self.mode = "peaks"
        self.drag = self.pan = self.hold = None
        self.callout = None
        self.dirty = False   # unsaved label changes
        self.fig = plt.figure(figsize=(15, 8.5))
        self.active = None
        for ev, fn in (("key_press_event", self.on_key), ("button_press_event", self.on_press),
                       ("motion_notify_event", self.on_move), ("button_release_event", self.on_release),
                       ("scroll_event", self.on_scroll), ("resize_event", lambda ev: self.fit_fonts()),
                       ("close_event", self.on_close)):
            self.fig.canvas.mpl_connect(ev, fn)
        self.anns = {}   # (area, key) -> (annotation, peak (h, n))
        self.auto_off = {}   # (area, key) -> automatic (dH, dN) offset
        self.draw()

    def moved(self):
        out = []
        for p in self.free:
            q = self.bound.get(key(p))
            if q and math.hypot(q["h"] - p["h"], WEIGHT_N * (q["n"] - p["n"])) >= THRESHOLD:
                out.append((p, q))
        return out

    # ---- layout: page px -> matplotlib axes, and the page's automatic label positions ----
    def axes(self, rect, region, page_size):
        """a pane in figure fractions, kept at the page's aspect ratio; page_size = its (w, h) on the page"""
        ax = self.fig.add_axes(rect)
        ax.set_box_aspect(page_size[1] / page_size[0])
        ax._page_w = page_size[0]
        hh, nn = None, None
        (h0, h1), (n0, n1) = region
        ax.set_xlim(h0, h1)          # 1H decreases to the right
        ax.set_ylim(n1, n0)          # 15N increases downwards
        ax._span0 = h0 - h1
        ax._home = (ax.get_xlim(), ax.get_ylim())
        ax.tick_params(labelsize=12)   # axis numbers, 1.5x the old 8 pt
        return ax, hh, nn

    def contours(self, ax, v, colour, width):
        """the same contourpy lines as the SVG assets (tools/make_hsqc_svg.py), in ppm"""
        gen = contour_generator(z=v, line_type=LineType.Separate)
        sx = (spec.H_RANGE[1] - spec.H_RANGE[0]) / (spec.NX - 1)
        sy = (spec.N_RANGE[1] - spec.N_RANGE[0]) / (spec.NY - 1)
        lines = [np.column_stack([spec.H_RANGE[0] + c[:, 0] * sx, spec.N_RANGE[0] + c[:, 1] * sy])
                 for level in spec.LEVELS for c in gen.lines(level)]
        ax.add_collection(LineCollection(lines, colors=colour, linewidths=width))

    def auto(self, g, labels, area, use_inset):
        """Page-identical automatic placement; returns {key: (dH, dN)} label-centre offsets in ppm."""
        m, pw, ph = g["m"], g["pw"], g["ph"]
        prx = 2.4 * 0.02 / (spec.H_RANGE[0] - spec.H_RANGE[1]) * pw
        pry = 2.4 * 0.18 / (spec.N_RANGE[1] - spec.N_RANGE[0]) * ph
        sx0, sx1, sy0, sy1 = g["src"]
        ix, iy, iw, ih = g["inset"]
        if area == "main":
            bounds, rx, ry = (m["l"], m["t"], pw, ph), prx, pry
            forbid = [(sx0, sy0, sx1 - sx0, sy1 - sy0), (ix, iy, iw, ih)] if use_inset else [(m["l"], m["t"], 220, 22)]
            ppx, ppy = pw / (spec.H_RANGE[0] - spec.H_RANGE[1]), ph / (spec.N_RANGE[1] - spec.N_RANGE[0])
        else:
            bounds, rx, ry, forbid = (ix, iy, iw, ih), prx * iw / (sx1 - sx0), pry * ih / (sy1 - sy0), []
            ppx = iw / (INSET_SRC["h"][0] - INSET_SRC["h"][1])
            ppy = ih / (INSET_SRC["n"][1] - INSET_SRC["n"][0])
        boxes = place_labels(labels["items"], bounds, labels["pts"], rx, ry, forbid)
        if True:   # every label wholly inside its plot or callout (page: placeLabels contain)
            boxes = [(min(max(bx, bounds[0]), bounds[0] + bounds[2] - bw), min(max(by, bounds[1]), bounds[1] + bounds[3] - bh), bw, bh)
                     for bx, by, bw, bh in boxes]
        out = {}
        for L, (bx, by, bw, bh) in zip(labels["items"], boxes):
            cx, cy = bx + bw / 2, by + bh / 2
            out[L["key"]] = (-(cx - L["x"]) / ppx, (cy - L["y"]) / ppy)
        return out

    def draw(self):
        self.fig.clf()
        self.anns.clear()
        self.callout = None
        use_inset = self.mode == "peaks"
        g = geometry(use_inset)
        ix, iy, iw, ih = g["inset"]
        # two panes side by side (peaks mode): the main spectrum and the callout, each with the page's
        # shape; label sizes follow each pane's size, so label-to-plot proportions match the page
        main, hh, nn = self.axes([0.04, 0.06, 0.44, 0.88] if use_inset else [0.06, 0.06, 0.9, 0.88],
                                 (spec.H_RANGE, spec.N_RANGE), (g["pw"], g["ph"]))
        # a peak's contour footprint on the page (as in drawHSQC), for the wedge's point
        prx = 2.4 * 0.02 / (spec.H_RANGE[0] - spec.H_RANGE[1]) * g["pw"]
        pry = 2.4 * 0.18 / (spec.N_RANGE[1] - spec.N_RANGE[0]) * g["ph"]
        main._r_page = (prx, pry)
        main._page_ppm = (g["pw"] / (spec.H_RANGE[0] - spec.H_RANGE[1]), g["ph"] / (spec.N_RANGE[1] - spec.N_RANGE[0]))
        sx0, sx1, sy0, sy1 = g["src"]
        in_src = lambda x, y: use_inset and sx0 <= x <= sx1 and sy0 <= y <= sy1  # noqa: E731
        areas = {"main": dict(items=[], pts=[]), "inset": dict(items=[], pts=[])}
        anchors = {}
        if use_inset:
            self.contours(main, self.v_free, "#1d1d1f", 0.6)
            main.add_patch(plt.Rectangle((INSET_SRC["h"][0], INSET_SRC["n"][0]), INSET_SRC["h"][1] - INSET_SRC["h"][0],
                                         INSET_SRC["n"][1] - INSET_SRC["n"][0], fc=(0.43, 0.43, 0.46, 0.16), ec="#8a8a90", zorder=3))
            call, _, _ = self.axes([0.53, 0.06, 0.44, 0.88], (INSET_SRC["h"], INSET_SRC["n"]), (iw, ih))   # same size as main
            self.contours(call, self.v_free, "#1d1d1f", 0.35)
            call.set_title("callout", fontsize=12)
            self.callout = call
            call._page_ppm = (iw / (INSET_SRC["h"][0] - INSET_SRC["h"][1]), ih / (INSET_SRC["n"][1] - INSET_SRC["n"][0]))
            call._r_page = (prx * iw / (g["src"][1] - g["src"][0]), pry * ih / (g["src"][3] - g["src"][2]))
            for p in self.free:
                x, y = g["X"](p["h"]), g["Y"](p["n"])
                area = "inset" if in_src(x, y) else "main"
                px = g["to_inset"](x, y) if area == "inset" else (x, y)
                areas[area]["pts"].append(px)
                areas[area]["items"].append(dict(key=key(p), x=px[0], y=px[1], t=self.at_n[key(p)]))
                anchors[(area, key(p))] = (call if area == "inset" else main, (p["h"], p["n"]), p)
        else:
            self.contours(main, self.v_free, "#a3a3a8", 0.6)
            self.contours(main, self.v_bound, "#1d1d1f", 0.6)
            for p in self.free:
                areas["main"]["pts"].append((g["X"](p["h"]), g["Y"](p["n"])))
                q = self.bound.get(key(p))
                if q:
                    areas["main"]["pts"].append((g["X"](q["h"]), g["Y"](q["n"])))
            for p, q in self.moved():
                main.annotate("", xy=(q["h"], q["n"]), xytext=(p["h"], p["n"]),
                              arrowprops=dict(arrowstyle="->", color="#d9730d", lw=1.4))
                x, y = g["X"](q["h"]), g["Y"](q["n"])
                areas["main"]["items"].append(dict(key=key(p), x=x, y=y, t=self.example[key(p)]))
                anchors[("main", key(p))] = (main, (q["h"], q["n"]), p)
        saved = self.saved.get(self.mode, {})
        for area, lab in areas.items():
            auto = self.auto(g, lab, area, use_inset) if lab["items"] else {}
            text = {L["key"]: L["t"] for L in lab["items"]}
            for k, off in auto.items():
                ax, at, p = anchors[(area, k)]
                entry = saved.get(area, {}).get(k, off)
                dh, dn = entry[0], entry[1]
                self.auto_off[(area, k)] = off      # the page's automatic spot, to tell edits apart
                ann = ax.annotate(text[k], xy=at, xytext=(at[0] + dh, at[1] + dn), ha="center", va="center",
                                  color="#333", annotation_clip=True)    # hidden when its peak is out of view
                ann.set_clip_box(ax.bbox)                                   # and clipped to its pane
                ann.set_clip_on(True)
                opt = entry_options(entry)
                ann._force = bool(opt["wedge"]) if "wedge" in opt else None   # wedge forced on/off, or automatic
                ann._solid = bool(opt.get("solid"))                              # stand-out style (sticky)
                self.style_label(ann)
                ann._foot = self.foot[k]
                ann._wedge = LabelWedge(ann, at)
                ax.add_patch(ann._wedge)
                ann._wedge.set_clip_box(ax.bbox)
                ann._wedge.set_clip_on(True)
                ann._dot, = ax.plot(*at, "o", color="#d0021b", ms=7, mew=0, alpha=0.6)
                self.anns[(area, k)] = (ann, at)
                self.contain(ann)   # saved callout positions outside the callout are pulled back in
        for ax in self.fig.axes:   # labels grow with the zoom, so crowding stays as on the page
            ax.callbacks.connect("xlim_changed", lambda ax: self.fit_fonts())
        self.set_active(main)
        self.fig.suptitle(f"mode: {self.mode} — drag labels; click a pane to make it active (blue): scroll or +/- "
                          "zooms it, h resets;  m: mode, s: save, c: clear, a: wedge attach, d: stand out", fontsize=9)
        self.fit_fonts()

    def fit_fonts(self):
        """label size = page size x (pane width on screen / pane width on the page) x zoom"""
        for ax in self.fig.axes:
            if not hasattr(ax, "_page_w"):
                continue
            px_w = ax.get_window_extent().width
            zoom = ax._span0 / abs(ax.get_xlim()[1] - ax.get_xlim()[0])
            for ann, _ in self.anns.values():
                if ann.axes is ax:
                    ann.set_fontsize(FS * px_w / ax._page_w * zoom * 72 / self.fig.dpi)
        self.fig.canvas.draw_idle()

    def contain(self, ann):
        """keep a label wholly inside its pane's full region (plot or callout), as the page does, so no
        label is ever hidden outside its pane and out of reach. Worked out in ppm from the label's size on
        the page (the same box placeLabels uses), so it does not depend on the screen."""
        ax = ann.axes
        ppx, ppy = ax._page_ppm                                  # page px per ppm in this pane
        hw = len(ann.get_text()) * FS * 0.66 / 2 / ppx * 1.12   # half-size of the label box, ppm
        hh = FS * 1.15 / 2 / ppy * 1.12                          # (+12%: matplotlib text runs a little wider)
        (h0, h1), (n0, n1) = ax._home
        x, y = ann.xyann
        x = min(max(x, min(h0, h1) + hw), max(h0, h1) - hw)
        y = min(max(y, min(n0, n1) + hh), max(n0, n1) - hh)
        ann.xyann = (x, y)

    # ---- the active pane: the one zoom acts on ----
    def set_active(self, ax):
        self.active = ax
        for a in self.fig.axes:
            for sp in a.spines.values():
                sp.set_edgecolor("#2e6bd9" if a is ax else "#1d1d1f")
                sp.set_linewidth(2.2 if a is ax else 0.8)
        self.fig.canvas.draw_idle()

    @staticmethod
    def clamp(lim, home):
        """keep a (possibly reversed) axis range inside its starting range: no zooming or panning out"""
        lo, hi = min(home), max(home)
        a, b = min(lim), max(lim)
        span = min(b - a, hi - lo)
        a = min(max(a, lo), hi - span)
        b = a + span
        return (b, a) if lim[0] > lim[1] else (a, b)

    def set_view(self, ax, xlim, ylim):
        ax.set_ylim(*self.clamp(ylim, ax._home[1]))
        ax.set_xlim(*self.clamp(xlim, ax._home[0]))   # last: its callback refits the labels

    def zoom(self, ax, factor, cx=None, cy=None):
        (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
        cx = (x0 + x1) / 2 if cx is None else cx
        cy = (y0 + y1) / 2 if cy is None else cy
        self.set_view(ax, (cx + (x0 - cx) / factor, cx + (x1 - cx) / factor),
                      (cy + (y0 - cy) / factor, cy + (y1 - cy) / factor))

    def on_scroll(self, ev):
        if ev.inaxes is None:
            return
        self.set_active(ev.inaxes)
        self.zoom(ev.inaxes, 1.25 if ev.button == "up" else 1 / 1.25, ev.xdata, ev.ydata)

    # ---- dragging (own handler: robust, and inactive while the toolbar's zoom/pan is on) ----
    def toggle_wedge(self, ev):
        """double-click on a label or a peak dot: switch its wedge on/off (overrides the automatic rule)"""
        renderer = self.fig.canvas.get_renderer()
        best = None
        for ann, at in self.anns.values():
            ax = ann.axes
            if not ax.get_window_extent().contains(ev.x, ev.y):
                continue
            px, py = ax.transData.transform(at)
            d = math.hypot(px - ev.x, py - ev.y)
            if Text.get_window_extent(ann, renderer).contains(ev.x, ev.y):
                d = 0
            if d < 12 and (best is None or d < best[0]):
                best = (d, ann)
        if best:
            ann = best[1]
            shown = ann._wedge.shown                                   # what is drawn now
            ann._force = not shown
            self.last = ann
            self.dirty = True
            self.fig.canvas.draw_idle()

    def on_press(self, ev):
        if getattr(ev, "dblclick", False):
            self.toggle_wedge(ev)
            return
        tb = getattr(self.fig.canvas, "toolbar", None)
        if ev.button != 1 or (tb is not None and getattr(tb, "mode", "") != ""):   # toolbar zoom/pan is on
            return
        renderer = self.fig.canvas.get_renderer()
        for ann, (h, n) in self.anns.values():   # hit-test the label's text box on screen
            ax = ann.axes
            (x0, x1), (y0, y1) = ax.get_xlim(), ax.get_ylim()
            if not (min(x0, x1) <= h <= max(x0, x1) and min(y0, y1) <= n <= max(y0, y1)):
                continue                                     # its peak is out of view: label hidden
            if not ax.get_window_extent().contains(ev.x, ev.y):
                continue                                     # only the visible part of a pane
            bb = Text.get_window_extent(ann, renderer)
            if bb.contains(ev.x, ev.y):
                x, y = ann.xyann
                mx, my = ax.transData.inverted().transform((ev.x, ev.y))
                self.drag = (ann, x - mx, y - my)
                self.last = ann
                self.highlight(ann, True)
                self.set_active(ax)
                return
        near = []   # press and hold on a peak: show its label and wedge in blue (the nearest peak)
        for ann, at in self.anns.values():
            if ann.axes is ev.inaxes:
                px, py = ann.axes.transData.transform(at)
                near.append((math.hypot(px - ev.x, py - ev.y), id(ann), ann))
        if near and min(near)[0] < 10 * self.fig.dpi / 100:
            self.hold = self.last = min(near)[2]
            self.highlight(self.hold, True)
            return
        if ev.inaxes is not None:   # a press on a pane (not on a label): make it active and pan it
            self.set_active(ev.inaxes)
            self.pan = (ev.inaxes, ev.x, ev.y, ev.inaxes.get_xlim(), ev.inaxes.get_ylim(),
                        ev.inaxes.transData.inverted().frozen())

    def on_move(self, ev):
        if self.pan:   # drag on empty space: move the spectrum with the mouse
            ax, x0, y0, (a, b), (c, d), inv = self.pan   # transform as it was at the press
            (sx, sy), (ex, ey) = inv.transform((x0, y0)), inv.transform((ev.x, ev.y))
            self.set_view(ax, (a - (ex - sx), b - (ex - sx)), (c - (ey - sy), d - (ey - sy)))
            return
        if not self.drag:
            return
        ann, ox, oy = self.drag
        mx, my = ann.axes.transData.inverted().transform((ev.x, ev.y))   # works outside the axes too
        ann.xyann = (mx + ox, my + oy)
        self.contain(ann)
        self.fig.canvas.draw_idle()

    def on_release(self, ev):
        if self.drag:
            self.highlight(self.drag[0], False)
            self.dirty = True
        if self.hold:
            self.highlight(self.hold, False)
            self.hold = None
        self.drag = self.pan = None

    @staticmethod
    def style_label(ann):
        """stand-out labels sit on a white, slightly translucent, round-cornered background"""
        ann.set_bbox(dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.85) if ann._solid else None)

    def highlight(self, ann, on):
        """while a label is being moved, it and its peak are shown in blue"""
        c = "#2e6bd9" if on else "#333"
        ann.set_color(c)
        ann.set_fontweight("bold" if on else "normal")
        ann._wedge.set_facecolor("#2e6bd9" if on else "#888")
        ann._dot.set_color("#2e6bd9" if on else "#d0021b")
        ann._dot.set_markersize(11 if on else 7)
        ann._dot.set_alpha(0.8 if on else 0.6)
        self.fig.canvas.draw_idle()

    # ---- keys ----
    def collect(self):
        """keep only hand edits: labels moved away from their automatic spot. A label dragged back onto
        its automatic spot (or never moved) is left out, so the page keeps placing it itself."""
        mode = {}
        for (area, k), (ann, (h, n)) in self.anns.items():
            x, y = ann.xyann
            off = [round(x - h, 4), round(y - n, 4)]
            auto = self.auto_off[(area, k)]
            moved = abs(off[0] - auto[0]) > 1e-3 or abs(off[1] - auto[1]) > 1e-2
            opt = {}
            if ann._force is not None:
                opt["wedge"] = int(ann._force)
            if ann._solid:
                opt["solid"] = 1
            if moved or opt:
                mode.setdefault(area, {})[k] = off + ([opt] if opt else [])
        if mode:
            self.saved[self.mode] = mode
        else:
            self.saved.pop(self.mode, None)

    def on_key(self, event):
        if event.key in ("+", "=", "-") and self.active is not None:
            self.zoom(self.active, 1.25 if event.key != "-" else 1 / 1.25)
        elif event.key in ("h", "home"):   # back to the starting view (all panes)
            for ax in self.fig.axes:
                if hasattr(ax, "_home"):
                    self.set_view(ax, *ax._home)
        elif event.key == "m":
            self.collect()
            self.mode = "bound" if self.mode == "peaks" else "peaks"
            self.draw()
        elif event.key == "s":
            self.save()
        elif event.key == "a":   # wedges: aim at the label centre <-> attach at nearest corner / side centre
            global ATTACH
            self.collect()
            ATTACH = "anchor" if ATTACH == "centre" else "centre"
            print(f"wedge attachment: {ATTACH}")
            self.dirty = True
            self.draw()
        elif event.key == "d" and self.last is not None:   # last label: stand-out style on/off (sticky)
            self.last._solid = not self.last._solid
            self.style_label(self.last)
            self.dirty = True
            self.fig.canvas.draw_idle()
        elif event.key == "c":   # not "r": matplotlib uses r/h/home to reset the zoom
            self.saved.pop(self.mode, None)
            self.dirty = True
            self.draw()

    def save(self):
        self.collect()
        self.style["attach"] = ATTACH
        OUT.write_text("window.K7 = window.K7 || {};\n// written by tools/label_editor.py: label centre offsets "
                       "(dH, dN) in ppm from each peak, per view mode and area, with optional\n"
                       "// {wedge: 1/0, solid: 1}; and the wedge style (attach: centre | anchor)\nK7.labels = "
                       + json.dumps(self.saved, indent=1) + ";\nK7.labelStyle = " + json.dumps(self.style) + ";\n")
        print(f"saved {sum(len(a) for m in self.saved.values() for a in m.values())} moved labels -> {OUT}")
        self.dirty = False

    def on_close(self, ev):
        """closing the window (or q) with unsaved changes: ask in the terminal whether to save"""
        if self.dirty:
            try:
                answer = input("Label positions have changed. Save them? [Y/n] ").strip().lower()
            except EOFError:
                answer = "y"
            if answer in ("", "y", "yes"):
                self.save()


if __name__ == "__main__":
    Editor()
    plt.show()
