"""Reconstruct, for each residue the paper calls significant, which red (with peptide) peak its black (free) peak
moved to, using the paper's shift changes (Fig. 6) as a guide. Writes assets/k7_pept_guided.js (K7.guided).

The overlay alone can't say where a peak went: the minimal (nearest-peak) mapping in tools/extract_overlay.py sends
a big move to whatever red peak happens to be close, and often sends several residues to the same red peak. Here:

1. The paper's combined shift change is fitted as  delta = sqrt((a * dH)^2 + (b * dN)^2)  on the residues whose
   minimal mapping is trustworthy (their own black peak, a red peak no other residue claims, a clear move).
2. Each significant residue (paper delta >= its cutoff) moves to the red peak whose fitted delta is closest to the
   paper's. As in conservative (minimal) shift mapping, residues may share a red peak.
3. A residue with no red peak within MISMATCH of the paper's value is listed as missing: its bound peak is probably
   too weak to see (below the noise floor).

This is a reconstruction guided by the paper's numbers, not a measurement: the close-ups in step 5 say so.

Needs: numpy, scipy.  Usage: python tools/guide_moves.py
"""
import json
import re
from pathlib import Path

import numpy as np
from scipy.optimize import least_squares

ASSETS = Path(__file__).resolve().parent.parent / "assets"
W_N = 0.14              # the page's 15N weight (for the 'nearest' distances only)
OWN_BLACK = (0.06, 0.4)  # ppm (1H, 15N): a black peak this close to a residue's BMRB shift is its own
MISMATCH = 0.45         # largest relative mismatch (|fitted - paper| / paper) allowed for a red peak


def js_object(path, name):
    text = path.read_text()
    m = re.search(r"K7\." + name + r"\s*=\s*", text)
    return json.JSONDecoder().raw_decode(text[m.end():])[0]


def main():
    overlay, peptide = js_object(ASSETS / "k7_pept_peaks.js", "overlay"), js_object(ASSETS / "k7_pept_peaks.js", "peptide")
    paper = js_object(ASSETS / "k7_csp_paper.js", "paperCSP")
    all_free = js_object(ASSETS / "k7_hsqc.js", "free")["peaks"]
    free = {p["seq"]: p for p in all_free if p["kind"] == "backbone"}
    indole = {p["seq"]: p for p in all_free if p["kind"] == "indole"}   # tryptophan side-chain N-H
    mapped = {p["seq"]: p for p in peptide["peaks"] if p["kind"] == "backbone"}
    black, red = np.array(overlay["black"]), np.array(overlay["red"])
    delta = {int(k): v["delta"] for k, v in paper["bars"].items()}
    cutoff = paper.get("cutoff", 0.5)

    # each residue's own black peak (or none, when the nearest black peak is too far from its BMRB shift)
    def own_black(s, f=None):
        f = f or free[s]
        d = np.hypot(black[:, 0] - f["h"], W_N * (black[:, 1] - f["n"]))
        b = black[int(d.argmin())]
        return b if abs(b[0] - f["h"]) <= OWN_BLACK[0] and abs(b[1] - f["n"]) <= OWN_BLACK[1] else None

    # 1. fit the paper's metric on trustworthy residues
    red_use = {}
    for p in mapped.values():
        red_use[(p["h"], p["n"])] = red_use.get((p["h"], p["n"]), 0) + 1
    train = [(s, mapped[s]) for s in delta if s in mapped and s in free and own_black(s) is not None
             and red_use[(mapped[s]["h"], mapped[s]["n"])] == 1 and mapped[s]["csp"] >= 0.05]
    dh = np.array([p["h"] - p["free_h"] for _, p in train]); dn = np.array([p["n"] - p["free_n"] for _, p in train])
    target = np.array([delta[s] for s, _ in train])
    fit = least_squares(lambda ab: np.hypot(ab[0] * dh, ab[1] * dn) - target, x0=[5.0, 1.0], bounds=([0, 0], [20, 5]))
    a, b = fit.x
    rel = np.abs(np.hypot(a * dh, b * dn) - target) / target
    print(f"metric fitted on {len(train)} residues: delta = sqrt(({a:.2f} dH)^2 + ({b:.2f} dN)^2), "
          f"median mismatch {np.median(rel):.0%}")

    sig = sorted(s for s in delta if delta[s] >= cutoff and s in free)
    # where each residue starts: its backbone amide's black peak; for a tryptophan, the paper plots whichever of its
    # two N-H peaks (backbone or side-chain indole) moves more, so that one is used (sizes from the nearest-peak mapping)
    def start(f):
        bk = own_black(None, f)
        return bk if bk is not None else np.array([f["h"], f["n"]])
    side = {p["seq"]: p for p in peptide["peaks"] if p["kind"] == "indole"}
    def kind_of(s):
        return "side chain" if s in indole and s in side and side[s]["csp"] > mapped.get(s, {}).get("csp", 0) else "backbone"
    # 2. each residue on its own: the red peak whose fitted delta is closest to the paper's (red peaks may be shared)
    moves = {}
    for s in sig:
        kind = kind_of(s)
        f = indole[s] if kind == "side chain" else free[s]
        st = start(f)
        m = np.hypot(a * (red[:, 0] - st[0]), b * (red[:, 1] - st[1]))
        mis = np.abs(m - delta[s]) / delta[s]
        k = int(mis.argmin())
        if mis[k] > MISMATCH:
            continue
        moves[str(s)] = dict(kind=kind, free_h=round(float(st[0]), 3), free_n=round(float(st[1]), 2),
                             unresolved=own_black(None, f) is None,   # its free peak is below the noise floor: starts at its BMRB shift
                             h=round(float(red[k, 0]), 3), n=round(float(red[k, 1]), 2), paper=delta[s],
                             fitted=round(float(m[k]), 2))
    missing = [s for s in sig if str(s) not in moves]
    for s in sig:
        m = moves.get(str(s))
        print(f"{free[s]['res']}{s}: paper {delta[s]:.2f}  " +
              (f"-> red ({m['h']}, {m['n']}), fitted {m['fitted']:.2f} ({m['kind']})" if m else "no red peak fits"))
    guided = dict(source="red peaks chosen to match Kalverda et al. (2009) Fig. 6 (tools/guide_moves.py); a "
                         "reconstruction, not a measurement", metric=dict(a=round(a, 3), b=round(b, 3)),
                  moves=moves, missing=missing)
    (ASSETS / "k7_pept_guided.js").write_text(
        "window.K7 = window.K7 || {};\n// written by tools/guide_moves.py\nK7.guided = " + json.dumps(guided) + ";\n")
    print(f"{len(moves)} of {len(sig)} significant residues paired -> assets/k7_pept_guided.js")


if __name__ == "__main__":
    main()
