# Step 2: the HNCA pane

## Goal

Show, with animation, how the HNCA (and HNcoCA) experiments move magnetisation along the backbone
and record chemical shifts, and how the resulting 3D spectrum is cut into the planes and strips used
in the strip game. No pulse sequence: the transfer is shown on the molecule itself.

## Sources

- `strip-game-8.pdf` and the "Backbone couplings" slide: residues i-1 and i drawn as a chain, with the
  one-bond J couplings (Hz) on the bonds: H-N 92, N-CA 11, N-CA(i-1) 8 (two-bond), N-C' 15,
  C'-CA 52, CA-CB 35, C-H 129. Colour scheme: HN brown/red, CA purple, CO/CA blue
  (the "HN CA" / "CA CONH" tags).
- The "Assignment" slide: the HNCA strip with red CA(i) and a weaker red CA(i-1); the HNcoCA strip with
  black CA(i-1); arrows showing that the CA(i-1) of one strip is the CA(i) of the strip to its left.
- The "3D cube" and "3D spectra" slides: a 3D cube with three axes; a plane of the cube; a strip pulled
  out of it. They use an HSQC-NOESY; here the axes are **1H amide, 15N amide and 13C-alpha**, and the
  planes are the **1H-15N plane** (like the HSQC) and the **1H-13C-alpha plane** at one 15N shift.

## Data

- `tools/fetch_bmrb.py` also stores each residue's C-alpha shift and the previous residue's, so every
  backbone peak has (H, N, CA(i), CA(i-1)). Real K7 data from BMRB 15740.
- The demonstration uses **the six strip-game residues** (Asp130-Ile135), so the steps lead straight
  into the game.

## The pane: five short steps (buttons, as in step 1), each with a caption and a play/replay control

1. **Couplings.** The backbone of residues i-1 and i, drawn in the same style as the strip game's chain,
   with the J couplings on the bonds. The text explains that magnetisation can only move along bonds,
   at rates set by these couplings.
2. **HNCA transfer (animated).** A glowing "magnetisation" token moves H(i) -> N(i), then splits to
   CA(i) (11 Hz) and CA(i-1) (8 Hz). Each atom lights up as its shift is recorded (a "dN", "dCA" tag
   appears). The token returns to H for detection. The result builds the strip: a red CA(i) peak and a
   weaker red CA(i-1) peak, at the amide's H and N shifts.
3. **HNcoCA transfer (animated).** H(i) -> N(i) -> C'(i-1) -> CA(i-1) and back. Only CA(i-1) is
   recorded, giving the black peak. The two strips overlap, and the text explains why the black peak
   sits on the weaker red one.
4. **The 3D spectrum.** A cube with axes 1H, 15N and 13C-alpha holds every amide's peaks: an HNCA peak at
   (H, N, CA(i)) and one at (H, N, CA(i-1)). The cube can be turned by dragging. Looking down the
   13C-alpha axis, the peaks collapse onto the **1H-15N plane**, which is the HSQC from step 1.
5. **Planes and strips.** Pick one amide in the 1H-15N plane. The **1H-13C-alpha plane** at its 15N
   shift slides out of the cube (as in the 3D-spectra slide). Then a narrow **strip** at its 1H shift is
   cut from that plane, giving exactly the strip shown in the strip game. The last frame shows the strip
   drawn in the game's style, as the link to step 3.

## Drawing and animation

- Everything in SVG, sized with the same size-token / fitPane() approach as the other panes (no scroll
  bars), with the same shared labels (@n) as step 1.
- The 3D cube is drawn in SVG with a small oblique projection like the slides (1H across the front,
  13C-alpha up, 15N into the depth), animated between set views. No 3D library is needed.
- Peaks: dots in the cube; the extracted planes and strips use contour lines computed once (not
  re-contoured while animating).
- Animations run with requestAnimationFrame on a timeline per step, with play / pause / replay and a
  scrubber. They are stopped when the step or pane is left.

## Files

```
index.html            the pane, molecule drawing, transfer animation, 3D cube and plane/strip views
tools/fetch_bmrb.py   adds CA(i) and CA(i-1) to assets/k7_hsqc.js
```

## Decisions

- Step buttons with play / replay per step.
- Cube like the slides, animated transitions only.
- The demonstration uses the six game residues.
- Dots in the cube; pre-computed contour lines in the planes and strips.

## Status (built)

- All five steps are in `index.html` with play / pause / replay and a scrubber; animation stops when
  the pane is left. The demonstration residue is Asp130 (the red strip, already placed in the game) with
  Thr129 as residue i-1; Asp130's HNCA strip ends as the game's red strip image.
- Planes are drawn with dots/blobs; the final strip uses the game's red strip image.
- To refine: a more detailed couplings molecule (all H atoms as in the slide), contour lines in the
  extracted plane instead of blobs, and timing/wording of the captions.
