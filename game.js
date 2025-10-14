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

            strip.innerHTML = `
                <div class="strip-header">
                    <div class="residue-name">${residue.name}${residue.number}</div>
                </div>
                <div class="strip-data">
                    <div class="data-row">
                        <span class="data-label">H:</span>
                        <span class="data-value">${residue.H}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">N:</span>
                        <span class="data-value">${residue.N}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">CA(i):</span>
                        <span class="data-value">${residue.CA_i}</span>
                    </div>
                    <div class="data-row">
                        <span class="data-label">CO(i):</span>
                        <span class="data-value">${residue.CO_i}</span>
                    </div>
                    ${residue.CA_i_minus_1 ? `
                    <div class="data-row">
                        <span class="data-label">CA(i-1):</span>
                        <span class="data-value">${residue.CA_i_minus_1}</span>
                    </div>
                    ` : ''}
                    ${residue.CO_i_minus_1 ? `
                    <div class="data-row">
                        <span class="data-label">CO(i-1):</span>
                        <span class="data-value">${residue.CO_i_minus_1}</span>
                    </div>
                    ` : ''}
                </div>
            `;

            strip.addEventListener('click', () => this.handleStripClick(residue.id, index));
            board.appendChild(strip);
        });
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
