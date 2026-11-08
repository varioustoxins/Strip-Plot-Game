"""Fetch the free K7 1H-15N HSQC peaks from BMRB 15740 and write assets/k7_hsqc.js.

Peaks kept: backbone amides (H/N, with this residue's CA and the previous residue's CA, as the
HNCA sees them) and the Trp indole NH (HE1/NE1).
Asn/Gln side-chain NH2 peaks are left out.

Standard library only.   Usage: python tools/fetch_bmrb.py
"""
import json
import re
import urllib.request
from pathlib import Path

ENTRY = 15740
URL = f"https://api.bmrb.io/v2/entry/{ENTRY}?format=rawnmrstar"
OUT = Path(__file__).resolve().parent.parent / "assets" / "k7_hsqc.js"
PAIRS = [("H", "N", "backbone"), ("HE1", "NE1", "indole")]   # (proton, nitrogen, kind)


def shifts(star):
    """{(seq, residue): {atom: shift}} from the first assigned chemical shift loop."""
    loop = star[star.index("_Atom_chem_shift.ID"):]
    tags = re.findall(r"^\s*(_Atom_chem_shift\.\w+)", loop[: loop.index("\n\n")], re.M)
    col = {t.split(".")[1]: i for i, t in enumerate(tags)}
    body = loop[loop.index("\n\n"): loop.index("stop_")]
    out = {}
    for line in body.splitlines():
        f = line.split()
        if len(f) != len(tags):
            continue
        out.setdefault((int(f[col["Seq_ID"]]), f[col["Comp_ID"]]), {})[f[col["Atom_ID"]]] = float(f[col["Val"]])
    return out


def main():
    star = urllib.request.urlopen(URL, timeout=60).read().decode()
    peaks = []
    table = shifts(star)
    ca = {seq: atoms["CA"] for (seq, res), atoms in table.items() if "CA" in atoms}
    for (seq, res), atoms in sorted(table.items()):
        for h, n, kind in PAIRS:
            if h in atoms and n in atoms:
                p = dict(seq=seq, res=res, kind=kind, h=atoms[h], n=atoms[n])
                if kind == "backbone":   # the HNCA sees this residue's CA and the previous one's
                    p.update(ca=ca.get(seq), ca_prev=ca.get(seq - 1))
                peaks.append(p)
    data = dict(source=f"BMRB {ENTRY} (Vaccinia virus K7, free)", peaks=peaks)
    # a script, not .json, so the page can load it from a web server or straight from disk (file://)
    OUT.write_text("window.K7 = window.K7 || {};\nK7.free = " + json.dumps(data, indent=1) + ";\n")
    print(f"{len(peaks)} peaks -> {OUT}")


if __name__ == "__main__":
    main()
