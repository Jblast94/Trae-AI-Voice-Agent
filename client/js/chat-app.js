/**
 * Trae AI Chat Application
 * Modern conversational interface with voice, screen sharing, and multimodal support
 */

class TraeAIChat {
    constructor() {
        this.ws = null;
        this.currentConversationId = 'default';
        this.isRecording = false;
        this.mediaRecorder = null;
        this.audioChunks = [];
        this.isTyping = false;
        this.typingTimeout = null;
        
        // Initialize the application
        this.init();
    }

    async init() {
        this.setupEventListeners();
        this.connectWebSocket();
        this.setupKeyboardShortcuts();
        this.autoResizeTextarea();
        
        // Check for browser capabilities
        this.checkBrowserSupport();
        
        console.log('Trae AI Chat initialized');
    }

    setupEventListeners() {
        // Send button and enter key
        document.getElementById('sendBtn').addEventListener('click', () => this.sendMessage());
        document.getElementById('messageInput').addEventListener('keydown', (e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                this.sendMessage();
            }
        });

        // Voice recording
        document.getElementById('voiceBtn').addEventListener('click', () => this.toggleVoiceRecording());

        // Screen sharing
        document.getElementById('screenBtn').addEventListener('click', () => this.shareScreen());

        // Image upload
        document.getElementById('imageBtn').addEventListener('click', () => this.uploadImage());
        document.getElementById('fileInput').addEventListener('change', (e) => this.handleFileUpload(e));

        // Settings toggles
        document.getElementById('voiceToggle').addEventListener('click', (e) => this.toggleSetting(e.target));
        document.getElementById('screenToggle').addEventListener('click', (e) => this.toggleSetting(e.target));
        document.getElementById('scrollToggle').addEventListener('click', (e) => this.toggleSetting(e.target));

        // Typing indicator
        document.getElementById('messageInput').addEventListener('input', () => this.handleTyping());
    }

    setupKeyboardShortcuts() {
        document.addEventListener('keydown', (e) => {
            // Ctrl/Cmd + Enter to send
            if ((e.ctrlKey || e.metaKey) && e.key === 'Enter') {
                this.sendMessage();
            }
            
            // Ctrl/Cmd + M for voice
            if ((e.ctrlKey || e.metaKey) && e.key === 'm') {
                e.preventDefault();
                this.toggleVoiceRecording();
            }
            
            // Ctrl/Cmd + Shift + S for screen share
            if ((e.ctrlKey || e.metaKey) && e.shiftKey && e.key === 'S') {
                e.preventDefault();
                this.shareScreen();
            }
        });
    }

    autoResizeTextarea() {
        const textarea = document.getElementById('messageInput');
        textarea.addEventListener('input', function() {
            this.style.height = 'auto';
            this.style.height = Math.min(this.scrollHeight, 120) + 'px';
        });
    }

    connectWebSocket() {
        const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:';
        const wsUrl = `${protocol}//${window.location.host}/ws/client_${Date.now()}`;
        
        this.ws = new WebSocket(wsUrl);
        
        this.ws.onopen = () => {
            console.log('WebSocket connected');
            this.updateStatus('Connected', true);
        };
        
        this.ws.onmessage = (event) => {
            const data = JSON.parse(event.data);
            this.handleWebSocketMessage(data);
        };
        
        this.ws.onclose = () => {
            console.log('WebSocket disconnected');
            this.updateStatus('Disconnected', false);
            // Attempt to reconnect after 3 seconds
            setTimeout(() => this.connectWebSocket(), 3000);
        };
        
        this.ws.onerror = (error) => {
            console.error('WebSocket error:', error);
            this.updateStatus('Connection Error', false);
        };
    }

    handleWebSocketMessage(data) {
        switch (data.type) {
            case 'chat_response':
                this.addMessage(data.data.response, 'assistant');
                break;
            case 'new_message':
                this.addMessage(data.data.content, data.data.role);
                break;
            case 'typing':
                this.showTypingIndicator(data.data.isTyping);
                break;
            case 'screen_analysis':
                this.addMessage(`Screen Analysis: ${data.data.analysis}`, 'assistant');
                break;
        }
    }

    async sendMessage() {
        const input = document.getElementById('messageInput');
        const message = input.value.trim();
        
        if (!message) return;
        
        // Add user message to chat
        this.addMessage(message, 'user');
        
        // Clear input
        input.value = '';
        input.style.height = 'auto';
        
        // Show typing indicator
        this.showTypingIndicator(true);
        
        try {
            // Send via WebSocket if connected, otherwise use HTTP
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'chat',
                    data: {
                        message: message,
                        conversation_id: this.currentConversationId
                    }
                }));
            } else {
                // Fallback to HTTP API
                const response = await fetch('/chat', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        message: message,
                        conversation_id: this.currentConversationId
                    })
                });
                
                const data = await response.json();
                this.showTypingIndicator(false);
                this.addMessage(data.response, 'assistant');
            }
        } catch (error) {
            console.error('Error sending message:', error);
            this.showTypingIndicator(false);
            this.addMessage('Sorry, I encountered an error. Please try again.', 'assistant');
        }
    }

    addMessage(content, role, type = 'text') {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = `message ${role}`;
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = role === 'user' ? 'You' : 'AI';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        
        // Process content based on type
        if (type === 'code') {
            messageContent.innerHTML = `<div class="code-block">${this.escapeHtml(content)}</div>`;
        } else if (content.includes('```')) {
            // Handle code blocks in markdown-style
            messageContent.innerHTML = this.formatCodeBlocks(content);
        } else {
            messageContent.textContent = content;
        }
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        
        messagesContainer.appendChild(messageDiv);
        
        // Auto-scroll if enabled
        if (document.getElementById('scrollToggle').classList.contains('active')) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    formatCodeBlocks(content) {
        return content.replace(/```([\s\S]*?)```/g, '<div class="code-block">$1</div>');
    }

    escapeHtml(text) {
        const div = document.createElement('div');
        div.textContent = text;
        return div.innerHTML;
    }

    showTypingIndicator(show) {
        const messagesContainer = document.getElementById('chatMessages');
        let typingIndicator = document.getElementById('typingIndicator');
        
        if (show && !typingIndicator) {
            typingIndicator = document.createElement('div');
            typingIndicator.id = 'typingIndicator';
            typingIndicator.className = 'message assistant';
            typingIndicator.innerHTML = `
                <div class="message-avatar">AI</div>
                <div class="typing-indicator">
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                    <div class="typing-dot"></div>
                </div>
            `;
            messagesContainer.appendChild(typingIndicator);
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        } else if (!show && typingIndicator) {
            typingIndicator.remove();
        }
    }

    async toggleVoiceRecording() {
        const voiceBtn = document.getElementById('voiceBtn');
        
        if (!this.isRecording) {
            try {
                const stream = await navigator.mediaDevices.getUserMedia({ audio: true });
                this.mediaRecorder = new MediaRecorder(stream);
                this.audioChunks = [];
                
                this.mediaRecorder.ondataavailable = (event) => {
                    this.audioChunks.push(event.data);
                };
                
                this.mediaRecorder.onstop = () => {
                    this.processAudioRecording();
                };
                
                this.mediaRecorder.start();
                this.isRecording = true;
                voiceBtn.classList.add('recording');
                voiceBtn.textContent = '⏹️';
                
                this.updateStatus('Recording...', true);
            } catch (error) {
                console.error('Error accessing microphone:', error);
                alert('Could not access microphone. Please check permissions.');
            }
        } else {
            this.mediaRecorder.stop();
            this.isRecording = false;
            voiceBtn.classList.remove('recording');
            voiceBtn.textContent = '🎤';
            
            // Stop all tracks
            this.mediaRecorder.stream.getTracks().forEach(track => track.stop());
            
            this.updateStatus('Processing audio...', true);
        }
    }

    async processAudioRecording() {
        const audioBlob = new Blob(this.audioChunks, { type: 'audio/wav' });
        const formData = new FormData();
        formData.append('file', audioBlob, 'recording.wav');
        
        try {
            const response = await fetch('/speech-to-text', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            if (data.text && data.text.trim()) {
                document.getElementById('messageInput').value = data.text;
                this.updateStatus('Connected', true);
            } else {
                this.updateStatus('No speech detected', true);
                setTimeout(() => this.updateStatus('Connected', true), 2000);
            }
        } catch (error) {
            console.error('Error processing speech:', error);
            this.updateStatus('Speech processing failed', false);
            setTimeout(() => this.updateStatus('Connected', true), 2000);
        }
    }

    async shareScreen() {
        try {
            const stream = await navigator.mediaDevices.getDisplayMedia({
                video: { mediaSource: 'screen' }
            });
            
            // Capture a frame from the stream
            const video = document.createElement('video');
            video.srcObject = stream;
            video.play();
            
            video.onloadedmetadata = () => {
                const canvas = document.createElement('canvas');
                canvas.width = video.videoWidth;
                canvas.height = video.videoHeight;
                
                const ctx = canvas.getContext('2d');
                ctx.drawImage(video, 0, 0);
                
                const imageData = canvas.toDataURL('image/png');
                
                // Stop the stream
                stream.getTracks().forEach(track => track.stop());
                
                // Send screen capture via WebSocket
                if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                    this.ws.send(JSON.stringify({
                        type: 'screen_share',
                        data: {
                            screen: imageData
                        }
                    }));
                }
                
                // Add preview to chat
                this.addScreenPreview(imageData);
            };
        } catch (error) {
            console.error('Error sharing screen:', error);
            alert('Could not access screen. Please check permissions.');
        }
    }

    addScreenPreview(imageData) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = 'You';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = `
            <div>Shared screen:</div>
            <img src="${imageData}" class="screen-preview" alt="Screen capture">
        `;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        if (document.getElementById('scrollToggle').classList.contains('active')) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    uploadImage() {
        document.getElementById('fileInput').click();
    }

    async handleFileUpload(event) {
        const file = event.target.files[0];
        if (!file) return;
        
        const formData = new FormData();
        formData.append('file', file);
        formData.append('conversation_id', this.currentConversationId);
        
        try {
            const response = await fetch('/upload-image', {
                method: 'POST',
                body: formData
            });
            
            const data = await response.json();
            
            // Add image preview to chat
            this.addImagePreview(data.image_data, file.name);
            
            // Add AI analysis if available
            if (data.description) {
                setTimeout(() => {
                    this.addMessage(`Image Analysis: ${data.description}`, 'assistant');
                }, 500);
            }
        } catch (error) {
            console.error('Error uploading image:', error);
            alert('Failed to upload image. Please try again.');
        }
        
        // Clear the file input
        event.target.value = '';
    }

    addImagePreview(imageData, fileName) {
        const messagesContainer = document.getElementById('chatMessages');
        const messageDiv = document.createElement('div');
        messageDiv.className = 'message user';
        
        const avatar = document.createElement('div');
        avatar.className = 'message-avatar';
        avatar.textContent = 'You';
        
        const messageContent = document.createElement('div');
        messageContent.className = 'message-content';
        messageContent.innerHTML = `
            <div>Uploaded: ${fileName}</div>
            <img src="${imageData}" class="image-preview" alt="Uploaded image">
        `;
        
        messageDiv.appendChild(avatar);
        messageDiv.appendChild(messageContent);
        messagesContainer.appendChild(messageDiv);
        
        if (document.getElementById('scrollToggle').classList.contains('active')) {
            messagesContainer.scrollTop = messagesContainer.scrollHeight;
        }
    }

    toggleSetting(toggle) {
        toggle.classList.toggle('active');
    }

    handleTyping() {
        if (!this.isTyping) {
            this.isTyping = true;
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'typing',
                    data: { isTyping: true }
                }));
            }
        }
        
        clearTimeout(this.typingTimeout);
        this.typingTimeout = setTimeout(() => {
            this.isTyping = false;
            if (this.ws && this.ws.readyState === WebSocket.OPEN) {
                this.ws.send(JSON.stringify({
                    type: 'typing',
                    data: { isTyping: false }
                }));
            }
        }, 1000);
    }

    updateStatus(text, isConnected) {
        document.getElementById('statusText').textContent = text;
        const statusDot = document.querySelector('.status-dot');
        
        if (isConnected) {
            statusDot.style.background = '#34a853';
        } else {
            statusDot.style.background = '#ea4335';
        }
    }

    checkBrowserSupport() {
        // Check for required APIs
        const features = {
            webSocket: 'WebSocket' in window,
            mediaDevices: 'mediaDevices' in navigator,
            getUserMedia: 'getUserMedia' in navigator.mediaDevices,
            getDisplayMedia: 'getDisplayMedia' in navigator.mediaDevices,
            mediaRecorder: 'MediaRecorder' in window
        };
        
        console.log('Browser support:', features);
        
        // Disable features that aren't supported
        if (!features.getUserMedia || !features.mediaRecorder) {
            document.getElementById('voiceBtn').disabled = true;
            document.getElementById('voiceBtn').title = 'Voice input not supported';
        }
        
        if (!features.getDisplayMedia) {
            document.getElementById('screenBtn').disabled = true;
            document.getElementById('screenBtn').title = 'Screen sharing not supported';
        }
    }
}

// Initialize the chat application when the page loads
document.addEventListener('DOMContentLoaded', () => {
    window.traeChat = new TraeAIChat();
});

// Export for potential external use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = TraeAIChat;
}