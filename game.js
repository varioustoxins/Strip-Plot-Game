// NMR Strip Plot Game
class NMRGame {
    constructor() {
        this.residues = [];
        this.correctSequence = [];
        this.userConnections = [];
        this.selectedStrip = null;
        this.score = 0;
        this.difficulty = 'medium';
        this.init();
    }

    init() {
        this.setupEventListeners();
        this.newGame();
    }

    setupEventListeners() {
        document.getElementById('newGame').addEventListener('click', () => this.newGame());
        document.getElementById('checkAnswer').addEventListener('click', () => this.checkAnswer());
        document.getElementById('showHint').addEventListener('click', () => this.showHint());
        document.getElementById('toggleInstructions').addEventListener('click', () => this.toggleInstructions());
        document.getElementById('difficulty').addEventListener('change', (e) => {
            this.difficulty = e.target.value;
            this.newGame();
        });
    }

    toggleInstructions() {
        const instructions = document.getElementById('instructions');
        instructions.classList.toggle('hidden');
    }

    newGame() {
        this.score = 0;
        this.userConnections = [];
        this.selectedStrip = null;
        document.getElementById('feedback').classList.add('hidden');
        
        // Generate residues based on difficulty
        const numResidues = this.difficulty === 'easy' ? 4 : 
                           this.difficulty === 'medium' ? 6 : 8;
        
        this.generateResidues(numResidues);
        this.shuffleResidues();
        this.renderGameBoard();
        this.updateStatus('Click strips to connect residues in sequence');
        this.updateScore();
    }

    generateResidues(count) {
        const aminoAcids = ['ALA', 'GLY', 'VAL', 'LEU', 'ILE', 'SER', 'THR', 'ASP', 'GLU', 'LYS'];
        this.residues = [];
        this.correctSequence = [];

        // Generate realistic chemical shift values for protein backbone
        let prevCA = this.randomShift(50, 65);
        let prevCO = this.randomShift(172, 178);

        for (let i = 0; i < count; i++) {
            const residue = {
                id: i,
                name: aminoAcids[Math.floor(Math.random() * aminoAcids.length)],
                number: i + 1,
                CA_i: prevCA,
                CO_i: prevCO,
                CA_i_minus_1: i > 0 ? this.residues[i - 1].CA_i : null,
                CO_i_minus_1: i > 0 ? this.residues[i - 1].CO_i : null,
                H: this.randomShift(7.5, 9.0),
                N: this.randomShift(115, 130)
            };

            this.residues.push(residue);
            this.correctSequence.push(i);

            // Generate next residue's shifts
            prevCA = this.randomShift(50, 65);
            prevCO = this.randomShift(172, 178);
        }
    }

    randomShift(min, max) {
        return (Math.random() * (max - min) + min).toFixed(2);
    }

    shuffleResidues() {
        // Shuffle the display order while keeping track of correct sequence
        const shuffled = [...this.residues];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        this.residues = shuffled;
    }

    renderGameBoard() {
        const board = document.getElementById('gameBoard');
        board.innerHTML = '';

        this.residues.forEach((residue, index) => {
            const strip = document.createElement('div');
            strip.className = 'strip';
            strip.dataset.residueId = residue.id;
            strip.dataset.index = index;

            // Generate SVG contour plot
            const contourSVG = this.generateContourPlot(residue);

            strip.innerHTML = `
                <div class="strip-header">
                    <div class="residue-name">${residue.name}${residue.number}</div>
                </div>
                <div class="strip-plot">
                    ${contourSVG}
                </div>
            `;

            strip.addEventListener('click', () => this.handleStripClick(residue.id, index));
            board.appendChild(strip);
        });
    }

    generateContourPlot(residue) {
        const width = 150;
        const height = 300;
        const margin = { top: 10, right: 10, bottom: 25, left: 35 };
        const plotWidth = width - margin.left - margin.right;
        const plotHeight = height - margin.top - margin.bottom;

        // CA range: 50-65, CO range: 172-178
        const caMin = 48, caMax = 67;
        const coMin = 171, coMax = 179;

        // Scale function for CA (x-axis)
        const scaleCA = (val) => margin.left + ((val - caMin) / (caMax - caMin)) * plotWidth;
        
        // Scale function for CO (y-axis) - inverted because SVG y increases downward
        const scaleCO = (val) => margin.top + ((coMax - val) / (coMax - coMin)) * plotHeight;

        let svg = `<svg width="${width}" height="${height}" class="strip-svg">`;
        
        // Background
        svg += `<rect x="${margin.left}" y="${margin.top}" width="${plotWidth}" height="${plotHeight}" fill="#f8f9fa" stroke="#dee2e6"/>`;

        // Axis labels
        svg += `<text x="${width/2}" y="${height - 5}" text-anchor="middle" font-size="10" fill="#495057">C (ppm)</text>`;
        svg += `<text x="8" y="${height/2}" text-anchor="middle" font-size="10" fill="#495057" transform="rotate(-90, 8, ${height/2})">C=O (ppm)</text>`;

        // Tick marks and labels on axes
        // CA axis (bottom)
        for (let ca = 50; ca <= 65; ca += 5) {
            const x = scaleCA(ca);
            svg += `<line x1="${x}" y1="${margin.top + plotHeight}" x2="${x}" y2="${margin.top + plotHeight + 3}" stroke="#6c757d" stroke-width="0.5"/>`;
            svg += `<text x="${x}" y="${margin.top + plotHeight + 13}" text-anchor="middle" font-size="8" fill="#6c757d">${ca}</text>`;
        }

        // CO axis (left)
        for (let co = 172; co <= 178; co += 2) {
            const y = scaleCO(co);
            svg += `<line x1="${margin.left - 3}" y1="${y}" x2="${margin.left}" y2="${y}" stroke="#6c757d" stroke-width="0.5"/>`;
            svg += `<text x="${margin.left - 5}" y="${y + 3}" text-anchor="end" font-size="8" fill="#6c757d">${co}</text>`;
        }

        // Draw contour peaks
        const peaks = [];
        
        // CA(i) and CO(i) peak - always present
        peaks.push({
            ca: parseFloat(residue.CA_i),
            co: parseFloat(residue.CO_i),
            color: '#dc3545',
            label: 'i'
        });

        // CA(i-1) and CO(i-1) peak - if present
        if (residue.CA_i_minus_1 && residue.CO_i_minus_1) {
            peaks.push({
                ca: parseFloat(residue.CA_i_minus_1),
                co: parseFloat(residue.CO_i_minus_1),
                color: '#007bff',
                label: 'i-1'
            });
        }

        // Draw each peak as a series of concentric ellipses (contour lines)
        peaks.forEach(peak => {
            const cx = scaleCA(peak.ca);
            const cy = scaleCO(peak.co);
            
            // Draw 3 contour levels
            for (let level = 3; level >= 1; level--) {
                const rx = 3 + level * 2;
                const ry = 4 + level * 2.5;
                const opacity = 0.15 + (4 - level) * 0.15;
                
                svg += `<ellipse cx="${cx}" cy="${cy}" rx="${rx}" ry="${ry}" 
                        fill="${peak.color}" opacity="${opacity}" stroke="${peak.color}" 
                        stroke-width="0.5" stroke-opacity="${opacity + 0.2}"/>`;
            }

            // Center point
            svg += `<circle cx="${cx}" cy="${cy}" r="1.5" fill="${peak.color}"/>`;
            
            // Label
            svg += `<text x="${cx + 8}" y="${cy - 8}" font-size="9" font-weight="bold" fill="${peak.color}">${peak.label}</text>`;
        });

        svg += `</svg>`;
        return svg;
    }

    handleStripClick(residueId, index) {
        if (this.selectedStrip === null) {
            // First selection
            this.selectedStrip = { id: residueId, index: index };
            this.highlightStrip(index, 'selected');
            this.updateStatus(`Selected ${this.getResidueById(residueId).name}${this.getResidueById(residueId).number}. Click another strip to connect.`);
        } else if (this.selectedStrip.id === residueId) {
            // Deselect
            this.clearSelection();
            this.updateStatus('Selection cleared. Click a strip to start.');
        } else {
            // Second selection - create connection
            const fromResidue = this.getResidueById(this.selectedStrip.id);
            const toResidue = this.getResidueById(residueId);
            
            this.userConnections.push({
                from: this.selectedStrip.id,
                to: residueId
            });

            this.highlightStrip(index, 'connected');
            this.highlightStrip(this.selectedStrip.index, 'connected');
            
            this.updateStatus(`Connected ${fromResidue.name}${fromResidue.number} → ${toResidue.name}${toResidue.number}`);
            this.updateConnectionCount();
            
            this.selectedStrip = null;
        }
    }

    highlightStrip(index, className) {
        const strips = document.querySelectorAll('.strip');
        strips[index].classList.remove('selected', 'connected', 'incorrect');
        strips[index].classList.add(className);
    }

    clearSelection() {
        const strips = document.querySelectorAll('.strip');
        strips.forEach(strip => strip.classList.remove('selected'));
        this.selectedStrip = null;
    }

    getResidueById(id) {
        return this.residues.find(r => r.id === id);
    }

    checkAnswer() {
        if (this.userConnections.length === 0) {
            this.showFeedback('Make some connections first!', 'error');
            return;
        }

        // Build the sequence from user connections
        const userSequence = this.buildSequenceFromConnections();
        
        if (!userSequence) {
            this.showFeedback('Connections are incomplete or have breaks. Make sure to form a continuous chain!', 'error');
            return;
        }

        // Check if it matches the correct sequence
        const isCorrect = this.checkSequenceCorrectness(userSequence);

        if (isCorrect) {
            this.score += 100;
            this.updateScore();
            this.showFeedback('🎉 Perfect! You correctly assigned the sequence!', 'success');
            this.highlightAllStrips('connected');
        } else {
            this.showFeedback('❌ Not quite right. Check the CA and CO chemical shifts between residues.', 'error');
            this.highlightIncorrectConnections(userSequence);
        }
    }

    buildSequenceFromConnections() {
        if (this.userConnections.length === 0) return null;

        // Build adjacency map
        const nextMap = {};
        const prevMap = {};
        
        this.userConnections.forEach(conn => {
            nextMap[conn.from] = conn.to;
            prevMap[conn.to] = conn.from;
        });

        // Find the start (residue with no predecessor)
        let start = null;
        for (let i = 0; i < this.residues.length; i++) {
            if (nextMap[i] !== undefined && prevMap[i] === undefined) {
                start = i;
                break;
            }
        }

        if (start === null) {
            // Try to find any starting point
            start = this.userConnections[0].from;
        }

        // Build sequence
        const sequence = [start];
        let current = start;
        let visited = new Set([start]);

        while (nextMap[current] !== undefined && !visited.has(nextMap[current])) {
            current = nextMap[current];
            sequence.push(current);
            visited.add(current);
        }

        return sequence;
    }

    checkSequenceCorrectness(userSequence) {
        // Check if each connection is valid (i.e., CA(i) matches CA(i-1) of next residue)
        for (let i = 0; i < userSequence.length - 1; i++) {
            const currentResidue = this.getResidueById(userSequence[i]);
            const nextResidue = this.getResidueById(userSequence[i + 1]);

            // The current residue's CA(i) should match the next residue's CA(i-1)
            if (currentResidue.CA_i !== nextResidue.CA_i_minus_1 ||
                currentResidue.CO_i !== nextResidue.CO_i_minus_1) {
                return false;
            }
        }

        // Check if it's a complete sequence
        return userSequence.length === this.residues.length;
    }

    highlightIncorrectConnections(userSequence) {
        const strips = document.querySelectorAll('.strip');
        strips.forEach(strip => {
            const residueId = parseInt(strip.dataset.residueId);
            const isInSequence = userSequence.includes(residueId);
            
            if (isInSequence) {
                const sequenceIndex = userSequence.indexOf(residueId);
                if (sequenceIndex < userSequence.length - 1) {
                    const currentResidue = this.getResidueById(residueId);
                    const nextResidue = this.getResidueById(userSequence[sequenceIndex + 1]);
                    
                    if (currentResidue.CA_i !== nextResidue.CA_i_minus_1) {
                        strip.classList.add('incorrect');
                    }
                }
            }
        });
    }

    highlightAllStrips(className) {
        const strips = document.querySelectorAll('.strip');
        strips.forEach(strip => {
            strip.classList.remove('selected', 'connected', 'incorrect');
            strip.classList.add(className);
        });
    }

    showHint() {
        // Find the first residue (one with no CA(i-1))
        const firstResidue = this.residues.find(r => r.CA_i_minus_1 === null);
        
        if (firstResidue) {
            const hint = `Hint: Start with ${firstResidue.name}${firstResidue.number} - it has no CA(i-1) value, meaning it's the first residue in the sequence!`;
            this.showFeedback(hint, 'hint');
        }
    }

    showFeedback(message, type) {
        const feedback = document.getElementById('feedback');
        feedback.textContent = message;
        feedback.className = `feedback ${type}`;
        feedback.classList.remove('hidden');
    }

    updateStatus(message) {
        document.getElementById('status').textContent = message;
    }

    updateScore() {
        document.getElementById('score').textContent = this.score;
    }

    updateConnectionCount() {
        document.getElementById('connections').textContent = 
            `${this.userConnections.length}/${this.residues.length - 1}`;
    }
}

// Initialize the game when the page loads
document.addEventListener('DOMContentLoaded', () => {
    new NMRGame();
});
