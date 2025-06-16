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

      <!-- Status Area -->
      <div class="status-section">
        <div v-if="!hasLogData" class="no-data-status">
          <div class="status-icon">📁</div>
          <p><strong>No flight data loaded</strong></p>
          <p class="status-hint">Upload a .bin file using the main interface to start analysis</p>
        </div>
        <div v-else class="data-ready-status">
          <div class="status-icon">✅</div>
          <div class="status-details">
            <p class="status-title">Flight data ready for analysis</p>
            <p class="status-meta">{{ flightSummary }}</p>
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
            <p v-if="!hasLogData">Upload a .bin log file in the main interface to get started!</p>
            <p v-else>Your flight data is ready! Ask me anything about the flight.</p>
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
        <div v-if="hasLogData" class="quick-actions">
          <button @click="askQuestion('What is the flight summary?')" class="quick-action-btn">
            📊 Summary
          </button>
          <button @click="askQuestion('What was the highest altitude?')" class="quick-action-btn">
            🏔️ Altitude
          </button>
          <button @click="askQuestion('Were there any GPS issues?')" class="quick-action-btn">
            📡 GPS Status
          </button>
          <button @click="askQuestion('How was the battery performance?')" class="quick-action-btn">
            🔋 Battery
          </button>
        </div>

        <!-- Message Input -->
        <div class="message-input-container">
          <textarea
            v-model="currentMessage"
            @keydown="handleKeyDown"
            :placeholder="hasLogData ? 'Ask about your flight log...' : 'Load flight data first...'"
            class="message-input"
            rows="2"
            :disabled="isLoading || !hasLogData"
          ></textarea>
          <button 
            @click="sendMessage" 
            class="send-btn" 
            :disabled="!currentMessage.trim() || isLoading || !hasLogData"
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
import { store } from './Globals.js'

export default {
  name: 'Chat',
  data() {
    return {
      state: store,
      isOpen: false,
      currentMessage: '',
      messages: [],
      isLoading: false,
      isTyping: false,
      typingText: 'Analyzing...',
      unreadCount: 0,
      logId: null
    }
  },
  computed: {
    hasLogData() {
      return this.state.processDone && 
             this.state.currentTrajectory && 
             this.state.currentTrajectory.length > 0
    },
    
    flightSummary() {
      if (!this.hasLogData) return ''
      
      try {
        const trajectory = this.state.currentTrajectory
        const duration = this.calculateFlightDuration()
        const maxAlt = this.calculateMaxAltitude()
        const points = trajectory.length
        
        return `${duration}s flight, ${maxAlt}m max altitude, ${points} GPS points`
      } catch (e) {
        return 'Flight data available'
      }
    }
  },
  watch: {
    'state.processDone'(newVal) {
      if (newVal && this.hasLogData) {
        this.sendLogDataToBackend()
      }
    }
  },
  mounted() {
    // Listen for flight data processing completion
    this.$eventHub.$on('messagesDoneLoading', this.onFlightDataReady)
    
    // Add global error handler
    window.addEventListener('error', this.handleGlobalError)
    window.addEventListener('unhandledrejection', this.handleUnhandledRejection)
  },
  
  beforeDestroy() {
    // Clean up event listeners
    this.$eventHub.$off('messagesDoneLoading', this.onFlightDataReady)
    window.removeEventListener('error', this.handleGlobalError)
    window.removeEventListener('unhandledrejection', this.handleUnhandledRejection)
  },
  methods: {
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

    onFlightDataReady() {
      if (this.hasLogData) {
        this.sendLogDataToBackend()
        this.addMessage('assistant', '✅ Flight data loaded! I can now analyze your flight. What would you like to know?')
      }
    },

    async sendLogDataToBackend() {
      try {
        // Create a summary of the flight data to send to the backend
        const flightData = this.extractFlightData()
        
        // Generate a unique log ID based on the data
        this.logId = this.generateLogId(flightData)
        
        console.log('Sending flight data to backend with logId:', this.logId)
        
        // Send the processed data to the backend for RAG processing
        const response = await fetch('/api/sync-flight-data', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json'
          },
          body: JSON.stringify({
            logId: this.logId,
            flightData: flightData
          })
        })

        if (!response.ok) {
          console.error('Failed to sync flight data with backend')
        } else {
          console.log('Flight data successfully synced with backend')
        }
      } catch (error) {
        console.error('Error sending flight data to backend:', error)
      }
    },

    extractFlightData() {
      // Extract comprehensive flight data from the global store
      const data = {
        trajectory: this.state.currentTrajectory.slice(), // Copy array
        flightModeChanges: this.state.flightModeChanges.slice(),
        events: this.state.events.slice(),
        textMessages: this.state.textMessages.slice(),
        timeAttitude: { ...this.state.timeAttitude },
        timeAttitudeQ: { ...this.state.timeAttitudeQ },
        timeTrajectory: { ...this.state.timeTrajectory },
        metadata: this.state.metadata,
        vehicle: this.state.vehicle,
        logType: this.state.logType,
        summary: {
          duration: this.calculateFlightDuration(),
          maxAltitude: this.calculateMaxAltitude(),
          totalDistance: this.calculateTotalDistance(),
          startTime: this.state.metadata?.startTime,
          trajectoryPoints: this.state.currentTrajectory.length
        }
      }
      
      return data
    },

    generateLogId(flightData) {
      // Generate a consistent ID based on flight data
      const dataString = JSON.stringify({
        points: flightData.trajectory.length,
        duration: flightData.summary.duration,
        startTime: flightData.summary.startTime
      })
      
      // Simple hash function
      let hash = 0
      for (let i = 0; i < dataString.length; i++) {
        const char = dataString.charCodeAt(i)
        hash = ((hash << 5) - hash) + char
        hash = hash & hash // Convert to 32-bit integer
      }
      
      return Math.abs(hash).toString(16).substring(0, 8)
    },

    calculateFlightDuration() {
      if (!this.state.currentTrajectory || this.state.currentTrajectory.length < 2) return 0
      
      const start = this.state.currentTrajectory[0][3] // time
      const end = this.state.currentTrajectory[this.state.currentTrajectory.length - 1][3]
      return ((end - start) / 1000).toFixed(1)
    },

    calculateMaxAltitude() {
      if (!this.state.currentTrajectory) return 0
      
      const altitudes = this.state.currentTrajectory.map(point => point[2]) // altitude
      return Math.max(...altitudes).toFixed(1)
    },

    calculateTotalDistance() {
      if (!this.state.currentTrajectory || this.state.currentTrajectory.length < 2) return 0
      
      let distance = 0
      for (let i = 1; i < this.state.currentTrajectory.length; i++) {
        const prev = this.state.currentTrajectory[i - 1]
        const curr = this.state.currentTrajectory[i]
        if (prev[1] && prev[0] && curr[1] && curr[0]) { // lat, lon
          distance += this.calculateDistance(prev[1], prev[0], curr[1], curr[0])
        }
      }
      return distance.toFixed(0)
    },

    calculateDistance(lat1, lon1, lat2, lon2) {
      const R = 6371000 // Earth's radius in meters
      const dLat = (lat2 - lat1) * Math.PI / 180
      const dLon = (lon2 - lon1) * Math.PI / 180
      const a = Math.sin(dLat/2) * Math.sin(dLat/2) +
                Math.cos(lat1 * Math.PI / 180) * Math.cos(lat2 * Math.PI / 180) *
                Math.sin(dLon/2) * Math.sin(dLon/2)
      const c = 2 * Math.atan2(Math.sqrt(a), Math.sqrt(1-a))
      return R * c
    },

    async sendMessage() {
      if (!this.currentMessage.trim() || this.isLoading || !this.hasLogData) return

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
        
        if (this.logId) {
          params.append('logId', this.logId)
        }

        const url = `/api/chat?${params}`

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

.status-section {
  padding: 12px;
  border-bottom: 1px solid #eee;
}

.no-data-status {
  display: flex;
  flex-direction: column;
  align-items: center;
  gap: 4px;
}

.status-icon {
  font-size: 24px;
  margin-bottom: 4px;
}

.status-hint {
  color: #666;
  font-size: 10px;
}

.data-ready-status {
  display: flex;
  align-items: center;
  gap: 8px;
  width: 100%;
}

.status-details {
  flex: 1;
  text-align: left;
}

.status-title {
  margin: 0;
  font-size: 12px;
  font-weight: 500;
  color: #333;
}

.status-meta {
  margin: 0;
  font-size: 10px;
  color: #666;
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