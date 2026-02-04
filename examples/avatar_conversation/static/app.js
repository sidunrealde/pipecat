/**
 * Avatar Conversation - Client Application
 * Handles WebSocket communication, avatar display, audio, and chat
 */

class AvatarApp {
    constructor() {
        // State
        this.ws = null;
        this.isConnected = false;
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.audioContext = null;
        this.analyser = null;
        this.currentAvatarImage = null;
        
        // DOM Elements
        this.elements = {
            status: document.getElementById('connection-status'),
            statusText: document.querySelector('#connection-status .text'),
            avatarCanvas: document.getElementById('avatar-canvas'),
            avatarOverlay: document.getElementById('avatar-overlay'),
            uploadArea: document.getElementById('upload-area'),
            fileInput: document.getElementById('file-input'),
            uploadStatus: document.getElementById('upload-status'),
            settingsToggle: document.getElementById('settings-toggle'),
            settingsPanel: document.getElementById('settings-panel'),
            chatHistory: document.getElementById('chat-history'),
            recordBtn: document.getElementById('record-btn'),
            visualizer: document.getElementById('visualizer'),
            textInput: document.getElementById('text-input'),
            sendBtn: document.getElementById('send-btn'),
            footer: document.querySelector('.footer #status-text')
        };
        
        // Canvas context
        this.ctx = this.elements.avatarCanvas.getContext('2d');
        this.vizCtx = this.elements.visualizer.getContext('2d');
        
        // Initialize
        this.init();
    }
    
    async init() {
        this.log('Initializing...');
        
        // Setup event listeners
        this.setupEventListeners();
        
        // Connect WebSocket
        this.connectWebSocket();
        
        // Request audio permissions
        await this.setupAudio();
        
        // Load existing avatar if any
        await this.loadCurrentAvatar();
        
        // Draw placeholder if no avatar
        if (!this.currentAvatarImage) {
            this.drawPlaceholderAvatar();
        }
        
        // Start visualizer animation
        this.animateVisualizer();
        
        this.log('Ready');
    }
    
    // =========================================================================
    // WebSocket Connection
    // =========================================================================
    
    connectWebSocket() {
        const wsUrl = `ws://${window.location.host}/ws`;
        
        try {
            this.ws = new WebSocket(wsUrl);
            
            this.ws.onopen = () => {
                this.isConnected = true;
                this.setStatus('connected', 'Connected');
                this.enableControls(true);
                this.log('Connected to server');
            };
            
            this.ws.onclose = () => {
                this.isConnected = false;
                this.setStatus('disconnected', 'Disconnected');
                this.enableControls(false);
                this.log('Disconnected');
                
                // Reconnect after 3 seconds
                setTimeout(() => this.connectWebSocket(), 3000);
            };
            
            this.ws.onerror = (err) => {
                this.log(`WebSocket error: ${err}`, 'error');
            };
            
            this.ws.onmessage = (event) => {
                this.handleMessage(JSON.parse(event.data));
            };
            
        } catch (err) {
            this.log(`Connection error: ${err.message}`, 'error');
        }
    }
    
    handleMessage(msg) {
        switch (msg.type) {
            case 'avatar':
                // Received avatar image
                this.displayAvatarFromBase64(msg.data);
                break;
                
            case 'video':
                // Received video frame
                this.displayFrameFromBase64(msg.data);
                break;
                
            case 'audio':
                // Received audio data
                this.playAudio(msg.data, msg.sample_rate);
                break;
                
            case 'text':
                // Received text response
                this.addMessage(msg.role || 'assistant', msg.content);
                break;
                
            case 'status':
                // Status message
                this.log(msg.message);
                break;
                
            case 'error':
                this.log(msg.message, 'error');
                break;
                
            default:
                console.log('Unknown message type:', msg.type);
        }
    }
    
    // =========================================================================
    // Avatar Display
    // =========================================================================
    
    async loadCurrentAvatar() {
        try {
            const resp = await fetch('/current-avatar');
            const data = await resp.json();
            
            if (data.avatar) {
                this.displayAvatarFromDataUrl(data.avatar);
            }
        } catch (err) {
            console.error('Failed to load avatar:', err);
        }
    }
    
    displayAvatarFromBase64(base64Data) {
        const dataUrl = `data:image/png;base64,${base64Data}`;
        this.displayAvatarFromDataUrl(dataUrl);
    }
    
    displayAvatarFromDataUrl(dataUrl) {
        const img = new Image();
        img.onload = () => {
            this.currentAvatarImage = img;
            this.drawAvatar(img);
            this.log('Avatar loaded');
        };
        img.src = dataUrl;
    }
    
    displayFrameFromBase64(base64Data) {
        const dataUrl = `data:image/jpeg;base64,${base64Data}`;
        const img = new Image();
        img.onload = () => {
            this.ctx.drawImage(img, 0, 0, 512, 512);
        };
        img.src = dataUrl;
    }
    
    drawAvatar(img) {
        this.ctx.clearRect(0, 0, 512, 512);
        
        // Calculate aspect ratio preserving dimensions
        const canvas = this.elements.avatarCanvas;
        const scale = Math.min(canvas.width / img.width, canvas.height / img.height);
        const x = (canvas.width - img.width * scale) / 2;
        const y = (canvas.height - img.height * scale) / 2;
        
        this.ctx.drawImage(img, x, y, img.width * scale, img.height * scale);
    }
    
    drawPlaceholderAvatar() {
        const ctx = this.ctx;
        const canvas = this.elements.avatarCanvas;
        
        // Background gradient
        const gradient = ctx.createLinearGradient(0, 0, 512, 512);
        gradient.addColorStop(0, '#1a1a2e');
        gradient.addColorStop(1, '#16213e');
        ctx.fillStyle = gradient;
        ctx.fillRect(0, 0, 512, 512);
        
        // Placeholder circle (head)
        ctx.beginPath();
        ctx.arc(256, 200, 80, 0, Math.PI * 2);
        ctx.fillStyle = '#4a4a6a';
        ctx.fill();
        
        // Body silhouette
        ctx.beginPath();
        ctx.ellipse(256, 420, 100, 80, 0, 0, Math.PI * 2);
        ctx.fillStyle = '#4a4a6a';
        ctx.fill();
        
        // Text
        ctx.fillStyle = '#888';
        ctx.font = '16px sans-serif';
        ctx.textAlign = 'center';
        ctx.fillText('Upload an avatar image', 256, 480);
    }
    
    // =========================================================================
    // File Upload
    // =========================================================================
    
    async uploadAvatar(file) {
        if (!file) return;
        
        this.showUploadStatus('Uploading...', 'info');
        
        try {
            const formData = new FormData();
            formData.append('file', file);
            
            const resp = await fetch('/upload-avatar', {
                method: 'POST',
                body: formData
            });
            
            const data = await resp.json();
            
            if (data.success) {
                this.showUploadStatus('Avatar uploaded successfully!', 'success');
                
                // Display the uploaded image
                const reader = new FileReader();
                reader.onload = (e) => {
                    this.displayAvatarFromDataUrl(e.target.result);
                };
                reader.readAsDataURL(file);
            } else {
                this.showUploadStatus(data.message || 'Upload failed', 'error');
            }
            
        } catch (err) {
            this.showUploadStatus(`Error: ${err.message}`, 'error');
        }
    }
    
    showUploadStatus(message, type = 'info') {
        const el = this.elements.uploadStatus;
        el.textContent = message;
        el.className = `upload-status ${type}`;
        
        // Clear after 3 seconds
        setTimeout(() => {
            el.textContent = '';
            el.className = 'upload-status';
        }, 3000);
    }
    
    // =========================================================================
    // Audio
    // =========================================================================
    
    async setupAudio() {
        try {
            const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
            
            this.audioContext = new (window.AudioContext || window.webkitAudioContext)();
            const source = this.audioContext.createMediaStreamSource(stream);
            this.analyser = this.audioContext.createAnalyser();
            this.analyser.fftSize = 256;
            source.connect(this.analyser);
            
            this.mediaRecorder = new MediaRecorder(stream, {
                mimeType: 'audio/webm'
            });
            
            this.mediaRecorder.ondataavailable = (e) => {
                this.audioChunks.push(e.data);
            };
            
            this.mediaRecorder.onstop = () => {
                this.sendAudio();
            };
            
            this.log('Microphone ready');
            return true;
            
        } catch (err) {
            this.log(`Microphone error: ${err.message}`, 'error');
            return false;
        }
    }
    
    startRecording() {
        if (!this.mediaRecorder) {
            this.log('Microphone not available', 'error');
            return;
        }
        
        this.audioChunks = [];
        this.mediaRecorder.start(100); // Collect in 100ms chunks
        this.isRecording = true;
        
        this.elements.recordBtn.textContent = '⏹️ Stop';
        this.elements.recordBtn.classList.add('recording');
        this.log('Recording...');
    }
    
    stopRecording() {
        if (!this.isRecording) return;
        
        this.mediaRecorder.stop();
        this.isRecording = false;
        
        this.elements.recordBtn.textContent = '🎤 Record';
        this.elements.recordBtn.classList.remove('recording');
        this.log('Processing...');
    }
    
    async sendAudio() {
        if (this.audioChunks.length === 0) return;
        
        const blob = new Blob(this.audioChunks, { type: 'audio/webm' });
        const buffer = await blob.arrayBuffer();
        const base64 = btoa(String.fromCharCode(...new Uint8Array(buffer)));
        
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'audio',
                data: base64
            }));
            this.log('Audio sent');
        }
    }
    
    playAudio(base64Data, sampleRate = 16000) {
        // Decode and play audio
        try {
            const binary = atob(base64Data);
            const bytes = new Uint8Array(binary.length);
            for (let i = 0; i < binary.length; i++) {
                bytes[i] = binary.charCodeAt(i);
            }
            
            // Create audio blob and play
            const blob = new Blob([bytes], { type: 'audio/wav' });
            const url = URL.createObjectURL(blob);
            const audio = new Audio(url);
            audio.play();
            
        } catch (err) {
            console.error('Failed to play audio:', err);
        }
    }
    
    // =========================================================================
    // Chat
    // =========================================================================
    
    addMessage(role, content) {
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const text = document.createElement('p');
        text.textContent = content;
        messageDiv.appendChild(text);
        
        this.elements.chatHistory.appendChild(messageDiv);
        this.elements.chatHistory.scrollTop = this.elements.chatHistory.scrollHeight;
    }
    
    sendTextMessage(text) {
        if (!text.trim()) return;
        
        // Add to chat
        this.addMessage('user', text);
        
        // Send via WebSocket
        if (this.ws && this.isConnected) {
            this.ws.send(JSON.stringify({
                type: 'text',
                content: text
            }));
        }
        
        // Clear input
        this.elements.textInput.value = '';
    }
    
    // =========================================================================
    // Event Listeners
    // =========================================================================
    
    setupEventListeners() {
        // Upload area - click
        this.elements.uploadArea.addEventListener('click', () => {
            this.elements.fileInput.click();
        });
        
        // Upload area - file selected
        this.elements.fileInput.addEventListener('change', (e) => {
            if (e.target.files.length > 0) {
                this.uploadAvatar(e.target.files[0]);
            }
        });
        
        // Upload area - drag and drop
        this.elements.uploadArea.addEventListener('dragover', (e) => {
            e.preventDefault();
            this.elements.uploadArea.classList.add('dragover');
        });
        
        this.elements.uploadArea.addEventListener('dragleave', () => {
            this.elements.uploadArea.classList.remove('dragover');
        });
        
        this.elements.uploadArea.addEventListener('drop', (e) => {
            e.preventDefault();
            this.elements.uploadArea.classList.remove('dragover');
            
            if (e.dataTransfer.files.length > 0) {
                this.uploadAvatar(e.dataTransfer.files[0]);
            }
        });
        
        // Settings toggle
        this.elements.settingsToggle?.addEventListener('click', () => {
            this.elements.settingsPanel?.classList.toggle('hidden');
        });
        
        // Record button
        this.elements.recordBtn.addEventListener('click', () => {
            if (this.isRecording) {
                this.stopRecording();
            } else {
                this.startRecording();
            }
        });
        
        // Text input - Enter key
        this.elements.textInput.addEventListener('keypress', (e) => {
            if (e.key === 'Enter') {
                this.sendTextMessage(this.elements.textInput.value);
            }
        });
        
        // Send button
        this.elements.sendBtn.addEventListener('click', () => {
            this.sendTextMessage(this.elements.textInput.value);
        });
    }
    
    // =========================================================================
    // UI Helpers
    // =========================================================================
    
    setStatus(type, text) {
        this.elements.status.className = `status ${type}`;
        if (this.elements.statusText) {
            this.elements.statusText.textContent = text;
        }
    }
    
    enableControls(enabled) {
        this.elements.recordBtn.disabled = !enabled;
        this.elements.textInput.disabled = !enabled;
        this.elements.sendBtn.disabled = !enabled;
    }
    
    log(message, type = 'info') {
        console.log(`[Avatar] ${message}`);
        if (this.elements.footer) {
            this.elements.footer.textContent = message;
        }
    }
    
    animateVisualizer() {
        if (!this.analyser) {
            requestAnimationFrame(() => this.animateVisualizer());
            return;
        }
        
        const canvas = this.elements.visualizer;
        const ctx = this.vizCtx;
        const bufferLength = this.analyser.frequencyBinCount;
        const dataArray = new Uint8Array(bufferLength);
        
        this.analyser.getByteFrequencyData(dataArray);
        
        ctx.fillStyle = '#1a1a2e';
        ctx.fillRect(0, 0, canvas.width, canvas.height);
        
        const barWidth = (canvas.width / bufferLength) * 2.5;
        let x = 0;
        
        for (let i = 0; i < bufferLength; i++) {
            const barHeight = (dataArray[i] / 255) * canvas.height;
            
            ctx.fillStyle = this.isRecording ? '#ff4444' : '#4a90d9';
            ctx.fillRect(x, canvas.height - barHeight, barWidth, barHeight);
            
            x += barWidth + 1;
        }
        
        requestAnimationFrame(() => this.animateVisualizer());
    }
}

// Initialize app when DOM is ready
document.addEventListener('DOMContentLoaded', () => {
    window.app = new AvatarApp();
});
