<!-- ChatBot.vue -->
<!-- eslint-disable --> 
<template>
  <div class="chatbot-container">
    <div class="chatbot-header">
      <h3>UAV Log Assistant</h3>
      <button @click="toggleChat" class="minimize-btn">
        {{ isMinimized ? '▲' : '▼' }}
      </button>
    </div>
    
    <div v-if="!isMinimized" class="chatbot-content">
      <div class="chat-messages" ref="messagesContainer">
        <div 
          v-for="(message, index) in messages" 
          :key="index" 
          :class="['message', message.type]"
        >
          <div class="message-content">
            <strong v-if="message.type === 'user'">You:</strong>
            <strong v-else>Assistant:</strong>
            {{ message.text }}
          </div>
          <div class="message-time">{{ message.timestamp }}</div>
        </div>
        
        <div v-if="isTyping" class="message bot typing">
          <div class="message-content">
            <strong>Assistant:</strong>
            <span class="typing-indicator">
              <span></span>
              <span></span>
              <span></span>
            </span>
          </div>
        </div>
      </div>
      
      <div class="file-upload-container" v-if="!currentLogId">
        <input 
          type="file" 
          @change="handleFileUpload" 
          accept=".bin,.tlog"
          ref="fileInput"
          style="display: none"
        />
        <button @click="$refs.fileInput.click()" :disabled="isUploading" class="upload-btn">
          {{ isUploading ? 'Uploading...' : 'Upload Log File (.bin/.tlog)' }}
        </button>
      </div>
      
      <div class="log-info" v-if="currentLogId">
        <small>Analyzing log: {{ currentLogId }}</small>
        <button @click="clearLog" class="clear-log-btn">×</button>
      </div>
      
      <div class="chat-input-container">
        <input 
          v-model="currentMessage"
          @keypress.enter="sendMessage"
          type="text" 
          :placeholder="currentLogId ? 'Ask about this log file...' : 'Ask about UAV operations...'"
          class="chat-input"
          :disabled="isTyping"
        />
        <button @click="sendMessage" :disabled="isTyping || !currentMessage.trim()" class="send-btn">
          Send
        </button>
      </div>
    </div>
  </div>
</template>

<script>
export default {
  name: 'ChatBot',
  data() {
    return {
      isMinimized: false,
      currentMessage: '',
      isTyping: false,
      messages: [],
      currentLogId: null,
      isUploading: false
    }
  },
  mounted() {
    // Add initial message after component is mounted
    this.messages.push({
      type: 'bot',
      text: 'Hello! I\'m your UAV Log Assistant powered by AI. Upload a .bin or .tlog flight log file to analyze specific flight data, or ask me general questions about UAV operations and systems.',
      timestamp: this.getCurrentTime()
    })
  },
  methods: {
    toggleChat() {
      this.isMinimized = !this.isMinimized
    },
    
    async sendMessage() {
      if (!this.currentMessage.trim() || this.isTyping) return
      
      // Add user message
      this.messages.push({
        type: 'user',
        text: this.currentMessage,
        timestamp: this.getCurrentTime()
      })
      
      const userMessage = this.currentMessage
      this.currentMessage = ''
      
      // Show typing indicator
      this.isTyping = true
      
      try {
        // Call backend API
        const         response = await fetch('http://localhost:8000/chat', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
          },
          body: JSON.stringify({
            message: userMessage,
            log_id: this.currentLogId
          })
        })
        
        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`)
        }
        
        const data = await response.json()
        
        // Add bot response
        this.messages.push({
          type: 'bot',
          text: data.response,
          timestamp: this.getCurrentTime()
        })
        
      } catch (error) {
        console.error('Error calling chatbot API:', error)
        
        // Add error message
        this.messages.push({
          type: 'bot',
          text: 'Sorry, I\'m having trouble connecting to the AI service. Please make sure the backend is running and Ollama is available.',
          timestamp: this.getCurrentTime()
        })
      } finally {
        this.isTyping = false
        this.scrollToBottom()
      }
    },
    
    async handleFileUpload(event) {
      const file = event.target.files[0]
      if (!file) return
      
      this.isUploading = true
      
      try {
        const formData = new FormData()
        formData.append('file', file)
        
        const response = await fetch('http://localhost:8000/upload', {
          method: 'POST',
          body: formData
        })
        
        if (!response.ok) {
          throw new Error(`Upload failed: ${response.status}`)
        }
        
        const data = await response.json()
        this.currentLogId = data.log_id
        
        // Add success message
        this.messages.push({
          type: 'bot',
          text: `Log file uploaded successfully! Log ID: ${data.log_id}. You can now ask questions about this flight log.`,
          timestamp: this.getCurrentTime()
        })
        
      } catch (error) {
        console.error('Upload error:', error)
        this.messages.push({
          type: 'bot',
          text: 'Sorry, there was an error uploading your log file. Please try again.',
          timestamp: this.getCurrentTime()
        })
      } finally {
        this.isUploading = false
        // Clear the file input
        event.target.value = ''
      }
    },
    
    clearLog() {
      this.currentLogId = null
      this.messages.push({
        type: 'bot',
        text: 'Log file cleared. You can upload a new log file or ask general UAV questions.',
        timestamp: this.getCurrentTime()
      })
    },

    getCurrentTime () {
      return new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })
    },

    scrollToBottom () {
      this.$nextTick(() => {
        const container = this.$refs.messagesContainer
        if (container) {
          container.scrollTop = container.scrollHeight
        }
      })
    }
  },

  watch: {
    messages: {
      handler () {
        this.scrollToBottom()
      },
      deep: true
    }
  }
}
</script>

<style scoped>
.chatbot-container {
  position: fixed;
  bottom: 20px;
  right: 20px;
  width: 350px;
  max-height: 500px;
  background: white;
  border-radius: 10px;
  box-shadow: 0 4px 20px rgba(0, 0, 0, 0.15);
  z-index: 1000;
  font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
}

.chatbot-header {
  background: #2c3e50;
  color: white;
  padding: 15px;
  border-radius: 10px 10px 0 0;
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.chatbot-header h3 {
  margin: 0;
  font-size: 16px;
  font-weight: 600;
}

.minimize-btn {
  background: none;
  border: none;
  color: white;
  font-size: 14px;
  cursor: pointer;
  padding: 5px;
  border-radius: 3px;
  transition: background-color 0.2s;
}

.minimize-btn:hover {
  background-color: rgba(255, 255, 255, 0.1);
}

.chatbot-content {
  display: flex;
  flex-direction: column;
  height: 400px;
}

.chat-messages {
  flex: 1;
  overflow-y: auto;
  padding: 15px;
  background: #f8f9fa;
}

.message {
  margin-bottom: 15px;
  max-width: 85%;
}

.message.user {
  margin-left: auto;
}

.message.user .message-content {
  background: #007bff;
  color: white;
  border-radius: 18px 18px 5px 18px;
}

.message.bot .message-content {
  background: white;
  color: #333;
  border-radius: 18px 18px 18px 5px;
  border: 1px solid #e1e5e9;
}

.message-content {
  padding: 10px 15px;
  word-wrap: break-word;
  line-height: 1.4;
}

.message-content strong {
  font-weight: 600;
  margin-right: 5px;
}

.message-time {
  font-size: 11px;
  color: #6c757d;
  margin-top: 5px;
  text-align: right;
}

.message.user .message-time {
  text-align: right;
}

.message.bot .message-time {
  text-align: left;
}

.chat-input-container {
  display: flex;
  padding: 15px;
  background: white;
  border-radius: 0 0 10px 10px;
  border-top: 1px solid #e1e5e9;
}

.chat-input {
  flex: 1;
  padding: 10px 15px;
  border: 1px solid #ddd;
  border-radius: 25px;
  outline: none;
  font-size: 14px;
  margin-right: 10px;
}

.chat-input:focus {
  border-color: #007bff;
  box-shadow: 0 0 0 2px rgba(0, 123, 255, 0.25);
}

.send-btn {
  background: #007bff;
  color: white;
  border: none;
  padding: 10px 20px;
  border-radius: 25px;
  cursor: pointer;
  font-size: 14px;
  font-weight: 600;
  transition: background-color 0.2s;
}

.send-btn:hover:not(:disabled) {
  background: #0056b3;
}

.send-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.typing-indicator {
  display: inline-flex;
  align-items: center;
  margin-left: 5px;
}

.typing-indicator span {
  height: 6px;
  width: 6px;
  background: #007bff;
  border-radius: 50%;
  display: inline-block;
  margin: 0 1px;
  animation: typing 1.4s infinite ease-in-out;
}

.typing-indicator span:nth-child(1) {
  animation-delay: -0.32s;
}

.typing-indicator span:nth-child(2) {
  animation-delay: -0.16s;
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

/* Scrollbar styling */
.chat-messages::-webkit-scrollbar {
  width: 6px;
}

.chat-messages::-webkit-scrollbar-track {
  background: #f1f1f1;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb {
  background: #c1c1c1;
  border-radius: 3px;
}

.chat-messages::-webkit-scrollbar-thumb:hover {
  background: #a8a8a8;
}

/* File upload styles */
.file-upload-container {
  padding: 10px 15px;
  border-bottom: 1px solid #e1e5e9;
}

.upload-btn {
  width: 100%;
  background: #28a745;
  color: white;
  border: none;
  padding: 10px;
  border-radius: 5px;
  cursor: pointer;
  font-size: 14px;
  transition: background-color 0.2s;
}

.upload-btn:hover:not(:disabled) {
  background: #218838;
}

.upload-btn:disabled {
  background: #6c757d;
  cursor: not-allowed;
}

.log-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 8px 15px;
  background: #e8f5e8;
  border-bottom: 1px solid #e1e5e9;
  font-size: 12px;
  color: #2c3e50;
}

.clear-log-btn {
  background: none;
  border: none;
  color: #dc3545;
  cursor: pointer;
  font-size: 16px;
  font-weight: bold;
  padding: 2px 6px;
  border-radius: 3px;
  transition: background-color 0.2s;
}

.clear-log-btn:hover {
  background: rgba(220, 53, 69, 0.1);
}
</style>
