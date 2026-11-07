# NMR Strip Plot Teaching Game - Implementation Plan

## Context

This is an interactive teaching game for NMR protein assignment (HNCA experiment). Students learn to arrange strip plots in the correct sequential order based on peak connectivity patterns. The game teaches the fundamental principle: **"BLACK on the right connects to RED on the left"** where black HNcoCA peaks (CA(i-1)) and red HNCA peaks (CA(i)) show sequential backbone connectivity.

The puzzle consists of 6 strips representing residues ASP130-ASP131-ASN132-ILE133-ASN134-ILE135. Students must arrange scrambled strips into the correct sequence.

## Architecture

**Deployment Target**: Static GitHub Pages site (single HTML file)
**Technology Stack**:
- HTML5 with embedded CSS and JavaScript
- Pyodide (Python in browser) for game logic and validation
- Pre-converted PNG images for strip plots
- Native drag-and-drop API

**Key Design Decisions**:
1. **Single-file architecture**: Everything embedded in one HTML file for easy deployment and potential standalone distribution
2. **Pre-converted images**: Strip plots extracted as PNG from PDFs, allowing flexible UI rendering (scales, labels, boxes drawn in code)
3. **Pyodide from start**: Python handles validation logic, peak matching, and game state
4. **Minimal initial scope**: Just the draggable strips puzzle; reference materials (HSQC, sequence grid, theory) can be added later

## Implementation Steps

### 1. Asset Preparation

**Extract strip images from PDFs**:
- Convert strip-game-1.pdf and strip-game-2.pdf into 6 individual PNG images
- Each image shows ONLY the NMR strip plot portion (peaks and 13C axis)
- **Exclude dotted connection lines** - these will be drawn dynamically in-game
- High resolution (300 DPI) for crisp display
- Transparent background for flexible compositing

**Strip data** (measured from the dotted circles with `tools/measure_strips.py`; lives in the Python block of `index.html`).
Red contours = HNCA, CA(i); black blobs = HNcoCA, CA(i-1). Strips link when left CA(i) ≈ right CA(i-1) within 0.3 ppm.

| header  | residue | 1H    | 15N    | CA(i) red | CA(i-1) black |
|---------|---------|-------|--------|-----------|---------------|
| red     | ASP130  | 8.939 | 121.01 | 58.84     | 60.68         |
| blue    | ASP131  | 8.346 | 116.43 | 57.13     | 58.86         |
| green   | ASN132  | 7.526 | 120.96 | 55.39     | 57.37         |
| orange  | ILE133  | 8.963 | 122.49 | 67.06     | 55.44         |
| crimson | ASN134  | 7.793 | 117.06 | 56.63     | 66.97         |
| cyan    | ILE135  | 7.821 | 118.66 | 65.63     | 56.62         |

**Correct sequence**: red, blue, green, orange, crimson, cyan

**Assets**: `tools/build_strips.py` converts the PDFs to SVG (pdftocairo), deletes the dotted circles and grey
leader lines, crops each strip to the 49.8–71.0 ppm plot area and rasterises to `assets/<colour>.png`.

**Initial game state**:
- Strip1 (ASP130) pre-loaded in position 0 (leftmost)
- Strips 2-6 scrambled in the pool

### 2. HTML Structure

Single-page app with:
- Strip pool (initial scrambled strips)
- Assembly zone (6 drop zones)
- Control buttons (Check Answer, Reset, Hint)
- Feedback display

### 3. CSS Styling

**Strip card structure**:
```
┌─────────────┐
│ COLOR HEADER│  ← Colored bar (matches PDF colors)
├─────────────┤
│             │
│   NMR PLOT  │  ← PNG image of strip plot
│   WITH      │
│   PEAKS     │
│             │
├─────────────┤
│ ???         │  ← Residue type (hidden initially)
│ HN: 8.963   │  ← Chemical shifts
│ N: 122.49   │
└─────────────┘
```

### 4. JavaScript Drag-and-Drop

- Native HTML5 drag-and-drop API
- Visual feedback during drag
- Snap-to-grid behavior
- Allow rearranging strips

### 5. Pyodide Integration

Python validation logic:
- Check sequence correctness
- Validate peak connectivity
- Provide specific hints
- Generate feedback messages

### 6. Game Features

- **Initial State**: Strip1 (ASP130) pre-loaded in leftmost position
- **Hint Button**: Places Strip2 (ASP131) in second position (one-time helper)
- **Check Answer**: Validates sequence, shows success/hints
- **Reset**: Returns to initial state (red ASP130 strip in position 0, others shuffled in pool)
- **Dynamic Connectors**: 
  - Draw dotted circles + a line from CA(i) (red) on the left strip to CA(i-1) (black) on the right strip
  - Green line for correct connections
  - Red line for incorrect connections
  - Dotted line while dragging to preview connection

## Files to Create

```
Strip-Plot-Game/
├── index.html              (main game file)
├── assets/
│   ├── red.png
│   ├── blue.png
│   ├── green.png
│   ├── orange.png
│   ├── crimson.png
│   └── cyan.png
├── tools/
│   └── build_strips.py     (PDF -> clean strip PNGs)
│   └── measure_strips.py   (peak positions, needs PyMuPDF)
└── README.md               (updated with game instructions)
```

## Advantages of Chosen Approach

**Pre-converted images**:
- ✅ Faster load time (no PDF parsing)
- ✅ Simpler code (standard img tags)
- ✅ Flexible UI (draw headers/labels in code)
- ✅ Better mobile support
- ✅ GitHub Pages friendly

**Pyodide benefits**:
- ✅ Validation logic in Python (natural for science)
- ✅ Future extensibility (peak analysis, custom puzzles)
- ✅ Educational value (visible Python code)
- ✅ Single-file distribution possible

## Verification

**Testing checklist**:
1. Load in browser (Chrome, Firefox, Safari)
2. All 6 strips appear scrambled
3. Drag strips to arrange in correct order
4. Check Answer shows success with residue labels
5. Wrong order shows helpful hints
6. Hint system works progressively
7. Mobile touch drag-and-drop works
8. Offline functionality (after first Pyodide load)
9. Works as standalone downloaded file


