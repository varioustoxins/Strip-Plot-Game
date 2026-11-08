# Feedback round 2: plan

Each item is ticked when it is done and checked in the browser.

## Layout
- [x] White box the same height on every step and sub-step: panes fitted by bisection (the old straight-line estimate overshot when a text column was taller than a small pane), with a 20 px gap under each; refit whenever a pane's text changes.
- [x] Step 3 (Joining strips): the rule text ("Connect the black i-1 peak ...") goes under the title, left-justified with it.

## Step 2: HSQC
- [x] The a and b shift boxes sit twice as far from the edges of the spectrum.

## Step 3: Joining strips
- [x] Joined Cα atoms on the backbone chain: no green ring. Draw one sphere, half red and half black, the same size as the others.
- [x] Start again: scramble every strip back into the pool, including those already placed.
- [x] Hint: explain to the user what it does (it places the second strip after the first; it can be used once).

## Step 5: Binding
- [x] "+ DDX3 peptide": a key for the contour colours only: K7R apo (grey), K7R/DDX3 (black).
- [x] "Shift changes": buttons to step through its phases (our six, into the plot, all residues, secondary structure, structures).
- [x] CSP plot: the helix washes show over the blue cutoff wash and carry down over the sequence.
- [x] The secondary-structure line stops and starts at the ends of each helix (coils only within helices).
- [x] Helix positions as drawn in the paper's Fig. 6 (α1 27–43, α2 53–69, α3 71–82, α5 97–113, α6 126–132, α7 134–146).
- [x] Helix names on the CSP plot bigger.
- [x] Mark the helices on the structure pictures (STRUCT_LABELS in index.html: NMR picture from the paper's Fig. 6, crystal by eye; may need nudging).
- [x] Name the PDB codes of the structures: 2K36 (NMR) and 3JRV (with the DDX3 peptide), in PDB_CODES in index.html.

## Step 6
- [x] Remove step 6 (Structure): step 5 now ends with the structures.
