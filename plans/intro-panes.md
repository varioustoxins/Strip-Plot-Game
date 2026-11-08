# Intro panes: why assign the HSQC, and how the HNCA works

## Goal

Put two explanatory panes in front of the existing strip game, so the game becomes step 3 of a short lesson:

1. **Why assign?** The ¹H-¹⁵N HSQC of K7 shown four ways: unassigned → peak picked (@n pseudo-labels) → assigned (residue names) → with DDX3 bound (shifts move, so we can tell which residues bind, but only because the spectrum is assigned).
2. **How the HNCA works.** An interactive version of `strip-game-8.pdf`: the backbone and its one-bond J couplings, the HNCA and HNcoCA transfer pathways, and the strips they give (red CA(i) plus a weaker red CA(i-1), black CA(i-1)).
3. **Strip game.** The existing game, introduced by the rule sheet in `strip-game-7.pdf` (black on the right → red on the left, with the first two strips worked as an example).

## Data

- **BMRB 15740**: Vaccinia virus K7, free form (Kalverda et al., "Poxvirus K7 protein adopts a Bcl-2 fold…"). It has ¹H/¹⁵N shifts for 136 residues. The strip-game residues are K7 Asp130–Ile135; their ¹H/¹⁵N values match this entry exactly.
- `tools/fetch_bmrb.py` downloads the entry and writes `assets/k7_hsqc.json`:
  - `[{seq, res, atom, h, n}]` for the backbone amides (H/N) plus the Trp indole NH (HE1/NE1);
  - Asn/Gln side-chain NH₂ peaks are not shown.
- **DDX3-bound shifts are not in BMRB 15740.** Gary has the real data from the original work. Until it arrives:
  - `assets/k7_ddx3_bound.json` holds a **placeholder** with the same format, moving a contiguous patch of about 10 residues by plausible amounts.
  - The pane labels this view on screen as *illustrative placeholder data*.
  - Swapping in the real file needs no code change.

## Architecture

- **Stepper shell.**
  - One pane is visible at a time.
  - Back/Next buttons plus a step indicator, "1 Why assign · 2 HNCA · 3 Strip game", whose steps can also be clicked.
  - The current step is kept in the URL hash (`#assign`, `#hnca`, `#strips`) so a link or a reload lands on the same pane.
- **Pane contract.** Each pane is a `<section>` with `init()` (runs once), `fit(box)` (fit to the space it is given) and `draw()`. Only the visible pane is fitted and drawn.
- **Size tokens become per pane.**
  - The current `fitPuzzle()` becomes a generic `fitPane(pane, tokens)`. It applies scale-1 tokens, measures the pane at two scales, solves the affine fit, then nudges down if anything still overflows.
  - Each pane declares its own base tokens: strip sizes for the game, spectrum size and font sizes for the HSQC, diagram size for the HNCA.
  - Tokens are written to the pane element, not `:root`, so panes are independent. The drag ghost is appended inside its pane so it inherits them.
  - The shared text scale (the `clamp()` font size) stays page-wide.
- **Shared state.** The random @n labels are drawn once per visit and shared. The six strip residues carry the same @n in the peak-picked HSQC as on their strips, so students can connect the two panes.
- **Python (Pyodide)** stays the place for data logic: loading the JSON, computing chemical shift perturbations (CSP, Δδ = √(Δδ_H² + (0.14·Δδ_N)²)), and choosing which residues count as perturbed.

## Pane 1: Why assign the HSQC?

- **Spectrum.**
  - SVG, with axes the NMR way: ¹H decreasing left to right (about 10.5–6.0 ppm), ¹⁵N increasing downwards (about 104–132 ppm), as in `strip-game0.pdf`.
  - Peaks drawn as small nested-ellipse contours in a Gaussian style.
- **Four views** chosen with a segmented control. Peaks morph smoothly between views:
  1. *Unassigned*: peaks only.
  2. *Peak picked*: each peak gets an @n pseudo-atom label (cross marker plus label). Labels repel each other to avoid overlaps.
  3. *Assigned*: labels become residue names, but as a clearly marked **example assignment** (real names shuffled at random among the peaks, once per visit), so the strip game's answer is not given away. The six strip-game peaks stay highlighted in their strip header colours and never get their own real name.
  4. *+ DDX3*: free peaks are drawn faint, bound peaks solid, with an arrow from each free peak to its bound position. Residues whose CSP is above the threshold are highlighted and listed. The placeholder banner shows while the data is the placeholder.
- **Short text beside the spectrum:** each peak is one backbone amide; without assignments a moving peak tells you nothing; with them, the moving peaks map the binding site onto the sequence and structure.
- **Hover/tap on a peak** shows its ¹H and ¹⁵N shifts and its label for the current view.

## Pane 2: The HNCA triple resonance

- **Diagram rebuilt in SVG from `strip-game-8.pdf`**: residues 1–4 in shaded columns; the backbone N–CA–C'(=O) with Hs, drawn like the strip game's chain; one-bond J couplings in Hz (NH 92, N–CA 11, N–CA(i-1) 8 via the 2-bond path, as in the PDF, N–C' 15, C'–CA 52, CA–CB 35, CH 129).
- **Controls:**
  - "HNCA": highlights the H→N→CA(i) and N→CA(i-1) transfer.
  - "HNcoCA": highlights H→N→C'→CA(i-1).
  - "Both": shows both pathways together.
- **Result strips** under the diagram, built as in the PDF: the HNCA strip has a strong red CA(i) and a weaker red CA(i-1), and the HNcoCA gives a black CA(i-1). Arrows show how a CA(i-1) in one strip is the CA(i) of the strip to its left, which is the rule the game uses.
- **A short caption per step.** The diagram's text stays minimal.

## Pane 3: Strip game

- Unchanged, apart from:
  - becoming a pane under the stepper;
  - a short rule card at the top, from `strip-game-7.pdf`: the red ← black key and the worked first two strips. The existing instruction line could serve as this.

## Files

```
index.html                 stepper shell + three panes (single file stays the goal)
assets/k7_hsqc.json        free K7 HN shifts from BMRB 15740 (generated)
assets/k7_ddx3_bound.json  DDX3-bound HN shifts (PLACEHOLDER until real data)
tools/fetch_bmrb.py        BMRB 15740 -> assets/k7_hsqc.json
```

## Order of work

1. Stepper shell and pane contract. Refactor `fitPuzzle()` into `fitPane()` with tokens per pane; the strip game becomes pane 3 with no visible change.
2. `tools/fetch_bmrb.py` and `assets/k7_hsqc.json`; the placeholder bound file.
3. Pane 1: spectrum, the four views, labels, CSP in Python.
4. Pane 2: the diagram, the pathway steps, the result strips.
5. Shared @n labels across panes 1 and 3.

## Verification

- At each window size (1920×1080 down to 1024×640): every pane fits with no scrollbars. Headless screenshots go to the scratchpad.
- **HSQC:** peak positions match the BMRB shifts (check a few, including Asp130 at 8.939/121.017). Axis directions are correct.
- **Pane 3 after the refactor:** circles, arrows, chain and drag still line up, using the same checks as the size-token work.
- Back/Next and the URL hash restore the right pane after a reload.

## Open items

- Gary to supply the real DDX3-bound shifts (and the CSP threshold used in the paper).
