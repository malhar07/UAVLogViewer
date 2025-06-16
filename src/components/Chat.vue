<template>
  <div class="chat-widget">
    <!-- Chat Toggle Button -->
    <div 
      v-if="!isOpen" 
      class="chat-toggle" 
      @click="toggleChat"
    >
      <div class="chat-icon">
        <svg width="24" height="24" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg">
          <path d="M20 2H4C2.9 2 2 2.9 2 4V22L6 18H20C21.1 18 22 17.1 22 16V4C22 2.9 21.1 2 20 2Z" fill="currentColor"/>
        </svg>
      </div>
      <div v-if="unreadCount > 0" class="notification-badge">{{ unreadCount }}</div>
    </div>

    <!-- Enhanced Chat Dialog -->
          <div v-if="isOpen" class="chat-dialog">
      <!-- Header -->
      <div class="chat-header">
        <div class="header-content">
          <h3>UAV Log Assistant</h3>
          <div class="ai-capabilities">
            <span class="capability-badge active">Enhanced AI</span>
            <span class="capability-badge active">RAG Analysis</span>
          </div>
        </div>
        <div class="header-controls">
          <button @click="toggleChat" class="close-btn">×</button>
        </div>
      </div>

      <!-- Upload Area -->
      <div class="upload-section">
        <div 
          class="upload-area" 
          :class="{ 'drag-over': isDragOver, 'has-file': uploadedFile }"
          @drop="handleDrop"
          @dragover.prevent="handleDragOver"
          @dragleave="handleDragLeave"
          @click="triggerFileInput"
        >
          <input 
            ref="fileInput" 
            type="file" 
            accept=".bin" 
            @change="handleFileSelect" 
            style="display: none"
          >
          <div v-if="!uploadedFile" class="upload-placeholder">
            <div class="upload-icon">📁</div>
            <p><strong>Drop .bin log file here</strong></p>
            <p class="upload-hint">or click to browse</p>
          </div>
          <div v-else class="uploaded-file-info">
            <div class="file-icon">✅</div>
            <div class="file-details">
              <p class="file-name">{{ uploadedFile.name }}</p>
              <p class="file-meta">{{ formatFileSize(uploadedFile.size) }} • Ready for analysis</p>
            </div>
            <button @click.stop="clearFile" class="clear-file-btn">×</button>
          </div>
        </div>
      </div>

      <!-- Messages Area -->
      <div class="messages-container" ref="messagesContainer">
        <div v-if="messages.length === 0" class="welcome-message">
          <div class="ai-avatar">👾</div>
          <div class="message-content">
            <h4>Welcome to UAV Log Assistant!</h4>
            <p>I can help you analyze your UAV flight logs with:</p>
            <ul class="capabilities-list">
              <li>📊 <strong>Flight Analysis:</strong> Duration, altitude, GPS status</li>
              <li>🔋 <strong>Battery Performance:</strong> Voltage and consumption analysis</li>
              <li>📡 <strong>GPS Issues:</strong> Signal loss and accuracy problems</li>
              <li>⚠️ <strong>Error Detection:</strong> Flight issues and warnings</li>
            </ul>
            <p>Upload a .bin log file to get started!</p>
          </div>
        </div>

        <div v-for="(message, index) in messages" :key="index" class="message" :class="message.type">
          <div class="message-avatar">
            <span v-if="message.type === 'user'">👤</span>
            <span v-else>👾</span>
          </div>
          <div class="message-content">
            <div class="message-text" v-html="formatMessage(message.text)"></div>
            <div class="message-timestamp">{{ formatTimestamp(message.timestamp) }}</div>
          </div>
        </div>

        <div v-if="isTyping" class="typing-indicator">
          <div class="typing-avatar">👾</div>
          <div class="typing-content">
            <div class="typing-dots">
              <span></span>
              <span></span>
              <span></span>
            </div>
            <div class="typing-text">{{ typingText }}</div>
          </div>
        </div>
      </div>

      <!-- Input Area -->
      <div class="input-area">
        <!-- Quick Actions -->
        <div v-if="uploadedFile" class="quick-actions">
          <button @click="askQuestion('What is the flight summary?')" class="quick-action-btn">
            📊 Summary
          </button>
          <button @click="askQuestion('What was the highest altitude?')" class="quick-action-btn">
            🏔️ Altitude
          </button>
          <button @click="askQuestion('Were there any GPS issues?')" class="quick-action-btn">
            📡 GPS Status
          </button>
        </div>

        <!-- Message Input -->
        <div class="message-input-container">
          <textarea
            v-model="currentMessage"
            @keydown="handleKeyDown"
            placeholder="Ask about your flight log..."
            class="message-input"
            rows="2"
            :disabled="isLoading"
          ></textarea>
          <button 
            @click="sendMessage" 
            class="send-btn" 
            :disabled="!currentMessage.trim() || isLoading"
            :class="{ 'loading': isLoading }"
          >
            <span v-if="isLoading" class="loading-spinner"></span>
            <span v-else>🚀</span>
          </button>
        </div>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'Chat',
  data() {
    return {
      isOpen: false,
      isDragOver: false,
      currentMessage: '',
      messages: [],
      isLoading: false,
      isTyping: false,
      typingText: 'Analyzing...',
      unreadCount: 0,
      uploadedFile: null,
      logId: null
    }
  },
  mounted() {
    // Prevent default drag and drop behavior on the entire window
    window.addEventListener('dragover', this.preventDefaults, false)
    window.addEventListener('drop', this.preventDefaults, false)
    
    // Add global error handler
    window.addEventListener('error', this.handleGlobalError)
    window.addEventListener('unhandledrejection', this.handleUnhandledRejection)
  },
  
  beforeDestroy() {
    // Clean up event listeners
    window.removeEventListener('dragover', this.preventDefaults, false)
    window.removeEventListener('drop', this.preventDefaults, false)
    window.removeEventListener('error', this.handleGlobalError)
    window.removeEventListener('unhandledrejection', this.handleUnhandledRejection)
  },
  methods: {
    preventDefaults(e) {
      e.preventDefault()
      e.stopPropagation()
    },
    
    handleGlobalError(event) {
      console.error('Global error:', event.error)
    },
    
    handleUnhandledRejection(event) {
      console.error('Unhandled promise rejection:', event.reason)
      event.preventDefault()
    },
    toggleChat() {
      this.isOpen = !this.isOpen
      if (this.isOpen) {
        this.unreadCount = 0
        this.$nextTick(() => {
          this.scrollToBottom()
        })
      }
    },

    async handleFileSelect(event) {
      try {
        const file = event.target.files[0]
        if (file) {
          await this.uploadFile(file)
        }
      } catch (error) {
        console.error('File select error:', error)
        this.addMessage('assistant', `❌ File selection error: ${error.message}`)
      }
    },

    async handleDrop(event) {
      event.preventDefault()
      event.stopPropagation()
      this.isDragOver = false
      
      const files = event.dataTransfer.files
      if (files.length > 0) {
        await this.uploadFile(files[0])
      }
    },

    handleDragOver(event) {
      event.preventDefault()
      event.stopPropagation()
      this.isDragOver = true
    },

    handleDragLeave(event) {
      event.preventDefault()
      event.stopPropagation()
      this.isDragOver = false
    },

    triggerFileInput() {
      this.$refs.fileInput.click()
    },

    clearFile() {
      this.uploadedFile = null
      this.logId = null
      this.$refs.fileInput.value = ''
      this.addMessage('assistant', 'Log file cleared. Upload a new .bin file to continue analysis.')
    },

    async uploadFile(file) {
      if (!file.name.toLowerCase().endsWith('.bin')) {
        this.addMessage('assistant', '❌ Please upload a .bin log file for analysis.')
        return
      }

      this.isLoading = true
      this.setTyping('Uploading and processing log file...')

      try {
        const formData = new FormData()
        formData.append('file', file)

        const response = await fetch('/api/upload', {
          method: 'POST',
          body: formData
        })

        const result = await response.json()

        if (response.ok) {
          this.uploadedFile = file
          this.logId = result.log_id
          
          console.log('Upload successful, logId set to:', this.logId) // Debug log
          
          let message = `✅ **Log uploaded successfully!**\n\n`
          message += `📊 **Analysis Complete:**\n`
          message += `• File: ${result.filename}\n`
          message += `• Size: ${this.formatFileSize(result.size)}\n`
          message += `• Log ID: ${result.log_id}\n\n`
          
          if (result.basic_analysis) {
            message += `**Quick Summary:**\n`
            message += `• Duration: ${result.basic_analysis.duration_seconds || 0}s\n`
            message += `• Messages: ${result.basic_analysis.total_messages || 0}\n`
            message += `• Types: ${result.basic_analysis.message_types?.length || 0} different message types\n\n`
          }
          
          message += `🚀 **Ready for analysis!** Try asking:\n`
          message += `• "Give me flight summary"\n`
          message += `• "What was the highest altitude?"\n`
          message += `• "Were there any GPS issues?"`

          this.addMessage('assistant', message)
        } else {
          this.addMessage('assistant', `❌ Upload failed: ${result.detail || 'Unknown error'}`)
        }
      } catch (error) {
        this.addMessage('assistant', `❌ Upload error: ${error.message}`)
      } finally {
        this.isLoading = false
        this.clearTyping()
      }
    },

    async sendMessage() {
      if (!this.currentMessage.trim() || this.isLoading) return

      const message = this.currentMessage.trim()
      this.addMessage('user', message)
      this.currentMessage = ''
      
      await this.processMessage(message)
    },

    async askQuestion(question) {
      this.addMessage('user', question)
      await this.processMessage(question)
    },

    async processMessage(message) {
      this.isLoading = true
      this.setTyping('Analyzing with AI...')

      try {
        const params = new URLSearchParams({
          msg: message
        })
        
        console.log('Current logId:', this.logId) // Debug log
        
        if (this.logId) {
          params.append('logId', this.logId)
        }

        const url = `/api/chat?${params}`
        console.log('Chat request URL:', url) // Debug log

        const response = await fetch(url, {
          method: 'POST'
        })

        const result = await response.json()

        if (response.ok) {
          this.addMessage('assistant', result.response || result.answer || 'No response received')
        } else {
          this.addMessage('assistant', `❌ Error: ${result.detail || 'Unknown error'}`)
        }
      } catch (error) {
        this.addMessage('assistant', `❌ Connection error: ${error.message}`)
      } finally {
        this.isLoading = false
        this.clearTyping()
      }
    },

    addMessage(type, text) {
      const message = {
        type,
        text,
        timestamp: new Date()
      }
      
      this.messages.push(message)
      
      if (!this.isOpen && type === 'assistant') {
        this.unreadCount++
      }
      
      this.$nextTick(() => {
        this.scrollToBottom()
      })
    },

    formatMessage(text) {
      return text
        .replace(/\*\*(.*?)\*\*/g, '<strong>$1</strong>')
        .replace(/\*(.*?)\*/g, '<em>$1</em>')
        .replace(/`(.*?)`/g, '<code>$1</code>')
        .replace(/\n/g, '<br>')
        .replace(/• /g, '• ')
    },

    formatFileSize(bytes) {
      if (bytes === 0) return '0 Bytes'
      const k = 1024
      const sizes = ['Bytes', 'KB', 'MB', 'GB']
      const i = Math.floor(Math.log(bytes) / Math.log(k))
      return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
    },

    formatTimestamp(timestamp) {
      return new Date(timestamp).toLocaleTimeString([], { 
        hour: '2-digit', 
        minute: '2-digit' 
      })
    },

    setTyping(text) {
      this.isTyping = true
      this.typingText = text
    },

    clearTyping() {
      this.isTyping = false
      this.typingText = ''
    },

    scrollToBottom() {
      const container = this.$refs.messagesContainer
      if (container) {
        container.scrollTop = container.scrollHeight
      }
    },

    handleKeyDown(event) {
      if (event.key === 'Enter' && !event.shiftKey) {
        event.preventDefault()
        this.sendMessage()
      }
    }
  }
}
</script>

<style scoped>
/* Enhanced styles with new capabilities */
.chat-toggle {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 60px;
  height: 60px;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  cursor: pointer;
  box-shadow: 0 8px 25px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
  z-index: 1000;
}

.chat-toggle:hover {
  transform: translateY(-2px);
  box-shadow: 0 12px 35px rgba(102, 126, 234, 0.4);
}

.chat-icon {
  color: white;
  font-size: 24px;
}

.notification-badge {
  position: absolute;
  top: -5px;
  right: -5px;
  background: #ff4757;
  color: white;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: bold;
}

.chat-dialog {
  position: fixed;
  bottom: 90px;
  right: 20px;
  width: 420px;
  height: 600px;
  background: white;
  border-radius: 16px;
  box-shadow: 0 20px 60px rgba(0, 0, 0, 0.15);
  display: flex;
  flex-direction: column;
  z-index: 999;
  animation: slideIn 0.3s ease-out;
}

@keyframes slideIn {
  from {
    opacity: 0;
    transform: translateY(20px) scale(0.95);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}

.chat-header {
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
  color: white;
  padding: 16px;
  border-radius: 16px 16px 0 0;
  cursor: move;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-content h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.ai-capabilities {
  display: flex;
  gap: 6px;
  margin-top: 4px;
}

.capability-badge {
  background: rgba(255, 255, 255, 0.2);
  padding: 2px 8px;
  border-radius: 12px;
  font-size: 10px;
  font-weight: 500;
}

.capability-badge.active {
  background: rgba(255, 255, 255, 0.3);
}

.close-btn {
  background: none;
  border: none;
  color: white;
  font-size: 24px;
  cursor: pointer;
  padding: 0;
  width: 24px;
  height: 24px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-section {
  padding: 12px;
  border-bottom: 1px solid #eee;
}

.upload-area {
  border: 2px dashed #ddd;
  border-radius: 8px;
  padding: 12px;
  text-align: center;
  cursor: pointer;
  transition: all 0.2s ease;
  min-height: 60px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.upload-area.drag-over {
  border-color: #667eea;
  background: rgba(102, 126, 234, 0.05);
}

.upload-area.has-file {
  border-color: #2ed573;
  background: rgba(46, 213, 115, 0.05);
}

.upload-placeholder {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.upload-icon {
  font-size: 24px;
  margin-bottom: 4px;
}

.upload-placeholder p {
  margin: 0;
  font-size: 12px;
}

.upload-hint {
  color: #666;
  font-size: 10px;
}

.uploaded-file-info {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.file-icon {
  font-size: 20px;
}

.file-details {
  flex: 1;
  text-align: left;
}

.file-name {
  margin: 0;
  font-size: 12px;
  font-weight: 500;
  color: #333;
}

.file-meta {
  margin: 0;
  font-size: 10px;
  color: #666;
}

.clear-file-btn {
  background: #ff4757;
  color: white;
  border: none;
  border-radius: 50%;
  width: 20px;
  height: 20px;
  cursor: pointer;
  font-size: 12px;
  display: flex;
  align-items: center;
  justify-content: center;
}

.messages-container {
  flex: 1;
  overflow-y: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.welcome-message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.ai-avatar {
  font-size: 24px;
}

.welcome-message .message-content h4 {
  margin: 0 0 8px 0;
  color: #333;
  font-size: 14px;
}

.welcome-message .message-content p {
  margin: 0 0 8px 0;
  font-size: 12px;
  color: #666;
}

.capabilities-list {
  margin: 8px 0;
  padding-left: 16px;
  font-size: 11px;
}

.capabilities-list li {
  margin-bottom: 4px;
  color: #555;
}

.message {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.message.user {
  flex-direction: row-reverse;
}

.message-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  flex-shrink: 0;
}

.message.user .message-avatar {
  background: #667eea;
  color: white;
}

.message.assistant .message-avatar {
  background: #f8f9fa;
  border: 2px solid #e9ecef;
}

.message-content {
  flex: 1;
  max-width: calc(100% - 44px);
}

.message.user .message-content {
  text-align: right;
}

.message-text {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 12px;
  font-size: 13px;
  line-height: 1.4;
  word-wrap: break-word;
}

.message.user .message-text {
  background: #667eea;
  color: white;
}

.message-timestamp {
  font-size: 10px;
  color: #999;
  margin-top: 4px;
}

.message.user .message-timestamp {
  text-align: right;
}

.typing-indicator {
  display: flex;
  gap: 12px;
  align-items: flex-start;
}

.typing-avatar {
  width: 32px;
  height: 32px;
  border-radius: 50%;
  background: #f8f9fa;
  border: 2px solid #e9ecef;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
}

.typing-content {
  background: #f8f9fa;
  padding: 12px;
  border-radius: 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.typing-dots {
  display: flex;
  gap: 4px;
}

.typing-dots span {
  width: 6px;
  height: 6px;
  background: #667eea;
  border-radius: 50%;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-dots span:nth-child(2) {
  animation-delay: 0.2s;
}

.typing-dots span:nth-child(3) {
  animation-delay: 0.4s;
}

@keyframes typing {
  0%, 80%, 100% {
    transform: scale(0.8);
    opacity: 0.5;
  }
  40% {
    transform: scale(1);
    opacity: 1;
  }
}

.typing-text {
  font-size: 11px;
  color: #666;
  font-style: italic;
}

.input-area {
  padding: 12px;
  border-top: 1px solid #eee;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.quick-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.quick-action-btn {
  background: #f8f9fa;
  border: 1px solid #dee2e6;
  color: #495057;
  padding: 6px 10px;
  border-radius: 16px;
  font-size: 11px;
  cursor: pointer;
  transition: all 0.2s ease;
}

.quick-action-btn:hover {
  background: #e9ecef;
  transform: translateY(-1px);
}

.message-input-container {
  display: flex;
  gap: 8px;
  align-items: flex-end;
}

.message-input {
  flex: 1;
  border: 1px solid #dee2e6;
  border-radius: 20px;
  padding: 10px 16px;
  font-size: 13px;
  resize: none;
  outline: none;
  transition: border-color 0.2s ease;
}

.message-input:focus {
  border-color: #667eea;
}

.send-btn {
  width: 40px;
  height: 40px;
  border-radius: 50%;
  background: #667eea;
  color: white;
  border: none;
  cursor: pointer;
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 16px;
  transition: all 0.2s ease;
}

.send-btn:hover:not(:disabled) {
  background: #5a67d8;
  transform: translateY(-1px);
}

.send-btn:disabled {
  background: #dee2e6;
  cursor: not-allowed;
}

.loading-spinner {
  width: 16px;
  height: 16px;
  border: 2px solid rgba(255, 255, 255, 0.3);
  border-top: 2px solid white;
  border-radius: 50%;
  animation: spin 1s linear infinite;
}

@keyframes spin {
  0% { transform: rotate(0deg); }
  100% { transform: rotate(360deg); }
}

/* Responsive adjustments */
@media (max-width: 480px) {
  .chat-dialog {
    width: calc(100vw - 40px);
    height: calc(100vh - 140px);
    right: 20px;
    bottom: 90px;
  }
}
</style> 