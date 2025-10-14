# NMR Triple Resonance Strip Plot Game

A simple interactive game designed to demonstrate NMR triple resonance shift assignment in proteins. This educational tool helps students and researchers understand the process of sequential backbone assignment using simulated NMR strip plot data.

## Overview

This game simulates the process of assigning protein backbone resonances using NMR triple resonance experiments (HNCA, HNCO). Players must connect amino acid residues in the correct sequential order by matching chemical shift values between sequential residues.

## Features

- **Interactive Gameplay**: Click-to-connect interface for building residue sequences
- **Multiple Difficulty Levels**: 
  - Easy (4 residues)
  - Medium (6 residues)
  - Hard (8 residues)
- **Educational Content**: Built-in instructions explaining NMR concepts
- **Hint System**: Provides guidance to help users learn the assignment strategy
- **Score Tracking**: Monitor your progress and connections
- **Randomized Puzzles**: Each new game generates a unique puzzle

## How to Play

1. **Open the Game**: Simply open `index.html` in a web browser
2. **Understand the Data**: Each strip shows:
   - H and N chemical shifts (amide proton and nitrogen)
   - CA(i) and CO(i) - intraresidue carbon chemical shifts
   - CA(i-1) and CO(i-1) - sequential carbon chemical shifts from the previous residue
3. **Make Connections**: 
   - Click on a residue strip to select it
   - Click on another residue to connect them
   - Match CA(i) and CO(i) values with CA(i-1) and CO(i-1) values of the next residue
4. **Verify Your Solution**: Click "Check Answer" to see if you've correctly assigned the sequence
5. **Get Help**: Click "Show Hint" to identify the first residue in the sequence

## Installation

No installation required! This is a standalone web application that runs entirely in your browser.

### Running Locally

1. Clone this repository:
   ```bash
   git clone https://github.com/varioustoxins/Strip-Plot-Game.git
   cd Strip-Plot-Game
   ```

2. Open `index.html` in your web browser, or serve it with a simple HTTP server:
   ```bash
   python3 -m http.server 8000
   # Then visit http://localhost:8000
   ```

## Educational Context

### NMR Triple Resonance Experiments

This game simulates data from triple resonance NMR experiments commonly used for protein backbone assignment:

- **HNCA**: Correlates amide H and N with both intraresidue (i) and sequential (i-1) CA carbons
- **HNCO**: Correlates amide H and N with sequential (i-1) CO carbons

### Assignment Strategy

The key to solving the puzzle:
1. Find the residue with **no CA(i-1)** value - this is the first residue (N-terminus)
2. Look for the residue whose CA(i-1) matches the previous residue's CA(i)
3. Also verify that CO values match: current CO(i-1) = previous CO(i)
4. Continue building the chain until all residues are connected

## Technologies Used

- **HTML5**: Structure and content
- **CSS3**: Styling and animations
- **Vanilla JavaScript**: Game logic and interactivity
- **No external dependencies**: Runs entirely in the browser

## Files

- `index.html` - Main game interface
- `style.css` - Styling and visual design
- `game.js` - Game logic and functionality
- `README.md` - This file

## Browser Compatibility

Works in all modern browsers:
- Chrome/Edge (recommended)
- Firefox
- Safari
- Opera

## Contributing

Contributions are welcome! Feel free to submit issues or pull requests.

## License

This project is open source and available for educational purposes.

## Acknowledgments

Designed to help teach NMR spectroscopy and protein structure determination to students and researchers in structural biology.