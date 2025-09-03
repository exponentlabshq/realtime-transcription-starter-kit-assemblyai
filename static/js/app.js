class TranscriptionApp {
    constructor() {
        this.socket = io();
        this.isTranscribing = false;
        this.transcriptBuffer = [];
        this.sessionStartTime = null;
        this.liveLineEl = null; // single interim line element
        
        this.initializeElements();
        this.setupEventListeners();
        this.setupSocketListeners();
    }
    
    initializeElements() {
        this.startBtn = document.getElementById('startBtn');
        this.stopBtn = document.getElementById('stopBtn');
        this.clearBtn = document.getElementById('clearBtn');
        this.statusIndicator = document.getElementById('statusIndicator');
        this.statusText = document.getElementById('statusText');
        this.statusDot = document.querySelector('.status-dot');
        this.transcription = document.getElementById('transcription');
        this.sessionId = document.getElementById('sessionId');
        this.duration = document.getElementById('duration');

        // Create a single live/interim line at the bottom
        this.ensureLiveLine();
    }
    
    setupEventListeners() {
        this.startBtn.addEventListener('click', () => this.startTranscription());
        this.stopBtn.addEventListener('click', () => this.stopTranscription());
        this.clearBtn.addEventListener('click', () => this.clearTranscription());
    }
    
    setupSocketListeners() {
        this.socket.on('transcription_started', (data) => {
            this.updateStatus('Recording...', 'recording');
            this.startBtn.disabled = true;
            this.stopBtn.disabled = false;
            this.isTranscribing = true;
            this.sessionStartTime = Date.now();
            this.updateDuration();
        });
        
        this.socket.on('transcription_stopped', (data) => {
            this.updateStatus('Stopped', 'ready');
            this.startBtn.disabled = false;
            this.stopBtn.disabled = true;
            this.isTranscribing = false;
        });
        
        this.socket.on('session_started', (data) => {
            this.sessionId.textContent = data.session_id;
        });
        
        this.socket.on('transcript_update', (data) => {
            this.addTranscript(data.transcript, data.is_final);
        });
        
        this.socket.on('session_terminated', (data) => {
            this.updateStatus('Session ended', 'ready');
            this.startBtn.disabled = false;
            this.stopBtn.disabled = true;
            this.isTranscribing = false;
            this.duration.textContent = `${data.duration.toFixed(1)}s`;
        });
        
        this.socket.on('error', (data) => {
            this.showError(data.message);
            this.updateStatus('Error', 'error');
            this.startBtn.disabled = false;
            this.stopBtn.disabled = true;
            this.isTranscribing = false;
        });
    }
    
    startTranscription() {
        this.socket.emit('start_transcription');
        this.clearTranscription();
    }
    
    stopTranscription() {
        this.socket.emit('stop_transcription');
    }
    
    clearTranscription() {
        this.transcription.innerHTML = '<p class="placeholder">Transcription will appear here...</p>';
        this.transcriptBuffer = [];
        this.sessionId.textContent = '-';
        this.duration.textContent = '0s';
        this.liveLineEl = null;
        this.ensureLiveLine();
    }
    
    updateStatus(text, type) {
        this.statusText.textContent = text;
        this.statusDot.className = `status-dot ${type}`;
    }
    
    addTranscript(text, isFinal) {
        const trimmed = text.trim();
        if (!trimmed) return;

        // Ensure placeholder removed
        const placeholder = this.transcription.querySelector('.placeholder');
        if (placeholder) placeholder.remove();

        // Ensure live line exists
        this.ensureLiveLine();

        if (!isFinal) {
            // Update a single interim line only
            this.liveLineEl.querySelector('.text').textContent = trimmed;
            // keep view pinned to bottom
            this.transcription.scrollTop = this.transcription.scrollHeight;
            return;
        }

        // On final: append one finalized item and clear the live line
        const finalItem = document.createElement('div');
        finalItem.className = 'transcript-item final';
        const timestamp = new Date().toLocaleTimeString();
        finalItem.innerHTML = `
            <div class="timestamp">${timestamp}</div>
            <div class="text">${trimmed}</div>
        `;
        this.transcription.insertBefore(finalItem, this.liveLineEl);

        // Clear the live line text for the next interim updates
        this.liveLineEl.querySelector('.text').textContent = '';

        // Auto-scroll to bottom
        this.transcription.scrollTop = this.transcription.scrollHeight;

        // Persist only finals
        this.transcriptBuffer.push({ text: trimmed, timestamp, isFinal: true });
    }

    ensureLiveLine() {
        // Create or reuse a dedicated interim element at the end
        if (this.liveLineEl && this.liveLineEl.parentElement === this.transcription) return;
        const live = document.createElement('div');
        live.className = 'transcript-item';
        live.innerHTML = `
            <div class="timestamp">Live</div>
            <div class="text"></div>
        `;
        this.transcription.appendChild(live);
        this.liveLineEl = live;
    }
    
    showError(message) {
        const errorDiv = document.createElement('div');
        errorDiv.className = 'error-message';
        errorDiv.textContent = message;
        
        // Insert at the top of transcription container
        const container = this.transcription.parentElement;
        container.insertBefore(errorDiv, this.transcription);
        
        // Remove error after 5 seconds
        setTimeout(() => {
            if (errorDiv.parentElement) {
                errorDiv.parentElement.removeChild(errorDiv);
            }
        }, 5000);
    }
    
    updateDuration() {
        if (!this.isTranscribing || !this.sessionStartTime) return;
        
        const elapsed = (Date.now() - this.sessionStartTime) / 1000;
        this.duration.textContent = `${elapsed.toFixed(1)}s`;
        
        if (this.isTranscribing) {
            requestAnimationFrame(() => this.updateDuration());
        }
    }
}

// Initialize the app when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    new TranscriptionApp();
});
