class Chatbox {
  constructor() {
    this.isOpen = false
    this.isRecording = false
    this.voicePermissionGranted = false
    this.mediaRecorder = null
    this.currentStream = null
    this.audioChunks = []
    this.isProcessingVoice = false
    this.currentRecordingId = null
    this.voiceClickInProgress = false
    this.lastVoiceClickTime = 0 // Para debouncing
    this.voiceClickDebounceMs = 500 // 500ms de debounce

    this.initializeElements()
    this.loadChatHistory() // 🚀 Cargar historial al iniciar
    this.bindEvents()
    this.setupVoiceRecording()
  }

  initializeElements() {
    this.chatToggle = document.getElementById("chat-toggle")
    this.chatWindow = document.getElementById("chat-window")
    this.chatMessages = document.getElementById("chat-messages")
    this.chatInput = document.getElementById("chat-input")
    this.sendBtn = document.getElementById("send-btn")
    this.voiceBtn = document.getElementById("voice-btn")
    this.quickQuestions = document.querySelectorAll(".quick-question-item")

    this.chatIcon = this.chatToggle.querySelector(".chat-icon")
    this.closeIcon = this.chatToggle.querySelector(".close-icon")
    this.voiceIcon = this.voiceBtn.querySelector(".voice-icon")
    this.recordingIcon = this.voiceBtn.querySelector(".recording-icon")
  }

  bindEvents() {
    // Toggle del chat
    this.chatToggle.addEventListener("click", () => this.toggleChat())

    // Enviar mensaje
    this.sendBtn.addEventListener("click", () => this.sendMessage())
    this.chatInput.addEventListener("keypress", (e) => {
      if (e.key === "Enter") {
        this.sendMessage()
      }
    })

    // Preguntas frecuentes (sin simulación; usamos backend real)
    this.quickQuestions.forEach((item) => {
      item.addEventListener("click", (e) => {
        e.preventDefault()
        e.stopPropagation()

        // Prevenir múltiples clicks
        if (item.classList.contains("clicked")) return
        item.classList.add("clicked")

        const question = item.dataset.question
        this.addMessage(question, "user")

        // Llama al backend y muestra indicador durante la espera
        this.handleBotResponse(question)
          .finally(() => setTimeout(() => item.classList.remove("clicked"), 300))
      })
    })

    // Nota de voz - CON DEBOUNCING Y VALIDACIONES ESTRICTAS
    this.voiceBtn.addEventListener("click", (e) => {
      e.preventDefault()
      e.stopPropagation()
      e.stopImmediatePropagation()
      this.handleVoiceClick()
    }, { once: false, passive: false })

    // Prevenir eventos adicionales que puedan causar doble ejecución
    this.voiceBtn.addEventListener("touchstart", (e) => {
      e.preventDefault()
      e.stopPropagation()
    }, { passive: false })

    this.voiceBtn.addEventListener("touchend", (e) => {
      e.preventDefault()
      e.stopPropagation()
    }, { passive: false })

    // Cerrar chat al hacer click fuera
    document.addEventListener("click", (e) => {
      if (this.isOpen && !e.target.closest("#chatbox-container")) {
        this.closeChat()
      }
    })
  }

  // Método para manejar clicks del botón de voz con debouncing y validaciones estrictas
  async handleVoiceClick() {
    const currentTime = Date.now()
    
    // DEBOUNCING: Prevenir clicks muy rápidos
    if (currentTime - this.lastVoiceClickTime < this.voiceClickDebounceMs) {
      console.log("Click muy rápido, ignorando (debounce)...")
      return
    }
    
    this.lastVoiceClickTime = currentTime

    // Prevenir clicks múltiples
    if (this.voiceClickInProgress) {
      console.log("Click de voz ya en progreso, ignorando...")
      return
    }

    // Prevenir si ya se está procesando un mensaje de voz
    if (this.isProcessingVoice) {
      console.log("Ya se está procesando voz, ignorando click...")
      return
    }

    this.voiceClickInProgress = true
    console.log("Procesando click de voz... isRecording:", this.isRecording)

    try {
      // Verificar permisos
      if (!this.voicePermissionGranted) {
        const granted = await this.requestVoicePermission()
        if (!granted) {
          this.voiceClickInProgress = false
          return
        }
      }

      // Alternar entre iniciar y detener grabación
      if (this.isRecording) {
        await this.stopRecording()
      } else {
        await this.startRecording()
      }
    } catch (error) {
      console.error("Error en handleVoiceClick:", error)
      this.resetRecordingState()
    } finally {
      // Liberar la bandera después de un breve delay
      setTimeout(() => {
        this.voiceClickInProgress = false
        console.log("Click de voz completado")
      }, 300)
    }
  }

  toggleChat() {
    if (this.isOpen) {
      this.closeChat()
    } else {
      this.openChat()
    }
  }

  openChat() {
    this.isOpen = true
    this.chatWindow.classList.remove("hidden")
    setTimeout(() => {
      this.chatWindow.classList.add("show")
    }, 10)

    this.chatIcon.classList.add("hidden")
    this.closeIcon.classList.remove("hidden")

    // Focus en el input
    setTimeout(() => {
      this.chatInput.focus()
    }, 300)
  }

  closeChat() {
    this.isOpen = false
    this.chatWindow.classList.remove("show")
    setTimeout(() => {
      this.chatWindow.classList.add("hidden")
    }, 300)

    this.chatIcon.classList.remove("hidden")
    this.closeIcon.classList.add("hidden")
  }

  sendMessage(message = null) {
    const text = message || this.chatInput.value.trim()
    if (!text) return

    // Agregar mensaje del usuario
    this.addMessage(text, "user")

    // Limpiar input
    this.chatInput.value = ""

    // Respuesta REAL del bot con indicador mientras espera
    this.handleBotResponse(text)
  }

  addMessage(text, sender) {
    const messageDiv = document.createElement("div")
    messageDiv.className = `message ${sender}-message`

    const now = new Date()
    const timeString = now.toLocaleTimeString("es-ES", {
      hour: "2-digit",
      minute: "2-digit",
    })

    messageDiv.innerHTML = `
      <div class="message-content">${text}</div>
      <div class="message-time">${timeString}</div>
    `

    this.chatMessages.appendChild(messageDiv)
    this.scrollToBottom()
    this.saveChatHistory() // 🚀 Guardar historial después de cada mensaje
  }

  async handleBotResponse(userMessage) {
    try {
      this.showTypingIndicator()
      this.setSendingState(true)

      // Llamada al backend Django
      const response = await window.sendMessageToDjango(userMessage)
      let botReply = "⚠️ Lo siento, no pude procesar tu mensaje."

      if (response && response.success && response.response) {
        botReply = response.response
      } else if (response && response.error) {
        botReply = "⚠️ Error: " + response.error
      }

      this.addMessage(botReply, "bot")
    } catch (error) {
      console.error("Error al procesar respuesta:", error)
      this.addMessage("⚠️ Error de conexión con el servidor.", "bot")
    } finally {
      this.hideTypingIndicator()
      this.setSendingState(false)
    }
  }

  showTypingIndicator() {
    // Evita duplicados
    if (document.getElementById("typing-indicator")) return

    const typingDiv = document.createElement("div")
    typingDiv.className = "message bot-message"
    typingDiv.id = "typing-indicator"
    typingDiv.innerHTML = `
      <div class="typing-indicator" aria-live="polite" aria-label="El asistente está escribiendo">
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
        <div class="typing-dot"></div>
      </div>
    `
    this.chatMessages.appendChild(typingDiv)
    this.scrollToBottom()

    // Failsafe: si por cualquier razón no se oculta, retíralo tras 15s
    clearTimeout(this._typingTimeout)
    this._typingTimeout = setTimeout(() => this.hideTypingIndicator(), 15000)
  }

  hideTypingIndicator() {
    const typingIndicator = document.getElementById("typing-indicator")
    if (typingIndicator) {
      typingIndicator.remove()
    }
    clearTimeout(this._typingTimeout)
  }

  setSendingState(sending) {
    if (this.sendBtn) {
      this.sendBtn.disabled = sending
      this.sendBtn.style.opacity = sending ? "0.6" : ""
      this.sendBtn.style.pointerEvents = sending ? "none" : ""
    }
    if (this.chatInput) {
      this.chatInput.disabled = sending
    }
  }

  scrollToBottom() {
    this.chatMessages.scrollTop = this.chatMessages.scrollHeight
  }

  // 🚀 MÉTODOS DE HISTORIAL DE CHAT
  saveChatHistory() {
    const history = this.chatMessages.innerHTML
    sessionStorage.setItem("chatHistory", history)
  }

  loadChatHistory() {
    const history = sessionStorage.getItem("chatHistory")
    if (history) {
      this.chatMessages.innerHTML = history
      this.scrollToBottom()
    }
  }

  clearChatHistory() {
    sessionStorage.removeItem("chatHistory")
    this.chatMessages.innerHTML = ""
  }

  // Funcionalidad de grabación de voz - SIMPLIFICADA
  async setupVoiceRecording() {
    this.voicePermissionGranted = false
  }

  async requestVoicePermission() {
    if (this.voicePermissionGranted) return true

    try {
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.voicePermissionGranted = true
      
      // Detener el stream inmediatamente después de obtener permisos
      stream.getTracks().forEach((track) => track.stop())
      return true
    } catch (error) {
      console.log("Micrófono no disponible:", error)
      this.voiceBtn.style.display = "none"
      return false
    }
  }

  async startRecording() {
    try {
      // Verificaciones críticas para prevenir grabación múltiple
      if (this.isRecording) {
        console.log("Ya está grabando, saltando startRecording...")
        return
      }

      if (this.mediaRecorder && this.mediaRecorder.state === "recording") {
        console.log("MediaRecorder ya está en estado recording, saltando...")
        return
      }

      // Verificación adicional con ID de grabación
      if (this.currentRecordingId) {
        console.log("Ya existe un ID de grabación activo, saltando...")
        return
      }

      console.log("Iniciando grabación...")
      
      // Marcar como grabando INMEDIATAMENTE para prevenir llamadas múltiples
      this.isRecording = true
      
      // Generar ID único para esta grabación
      this.currentRecordingId = Date.now().toString() + "_" + Math.random().toString(36).substr(2, 9)
      
      // Limpiar estado anterior
      this.audioChunks = []
      this.cleanupPreviousRecording()
      
      // Obtener nuevo stream
      const stream = await navigator.mediaDevices.getUserMedia({ audio: true })
      this.currentStream = stream
      this.mediaRecorder = new MediaRecorder(stream, {
        mimeType: 'audio/webm' // Forzamos WebM para que coincida con la conversión
      })

      // Configurar eventos del MediaRecorder
      this.mediaRecorder.ondataavailable = (event) => {
        if (event.data.size > 0) {
          this.audioChunks.push(event.data)
        }
      }

      // Capturar el ID de grabación para el evento onstop
      const recordingId = this.currentRecordingId
      this.mediaRecorder.onstop = () => {
        console.log("MediaRecorder detenido para ID:", recordingId)
        // Solo procesar si es la grabación actual
        if (recordingId === this.currentRecordingId) {
          this.handleRecordingStop()
        } else {
          console.log("Evento onstop de grabación anterior, ignorando...")
        }
      }

      this.mediaRecorder.onerror = (error) => {
        console.error("Error en MediaRecorder:", error)
        this.resetRecordingState()
      }
      
      // Iniciar grabación
      this.mediaRecorder.start()
      this.updateVoiceButtonUI(true)
      
      console.log("Grabación iniciada con ID:", this.currentRecordingId)

    } catch (error) {
      console.error("Error al iniciar grabación:", error)
      this.resetRecordingState()
    }
  }

  async stopRecording() {
    console.log("Deteniendo grabación...")
    
    if (!this.isRecording || !this.mediaRecorder) {
      console.log("No hay grabación activa para detener")
      return
    }

    // Marcar como no grabando ANTES de detener
    this.isRecording = false
    this.updateVoiceButtonUI(false)

    // Detener MediaRecorder
    if (this.mediaRecorder.state === "recording") {
      this.mediaRecorder.stop()
      console.log("MediaRecorder.stop() llamado")
    }
  }

  handleRecordingStop() {
    console.log("Manejando detención de grabación...")
    
    // Prevenir procesamiento múltiple
    if (this.isProcessingVoice) {
      console.log("Ya se está procesando audio, ignorando...")
      return
    }

    // Verificar que hay audio para procesar
    if (this.audioChunks.length === 0) {
      console.log("No hay audio para procesar")
      this.cleanupPreviousRecording()
      return
    }

    // Marcar como procesando
    this.isProcessingVoice = true
    
    // Crear blob y procesar
    const audioBlob = new Blob(this.audioChunks, { type: "audio/wav" })
    console.log("Blob creado, tamaño:", audioBlob.size)
    
    // Procesar el mensaje de voz
    this.processVoiceMessage(audioBlob)
    
    // Limpiar recursos
    this.cleanupPreviousRecording()
  }

  async processVoiceMessage(audioBlob) {
    console.log("Procesando mensaje de voz...")

    if (!audioBlob || audioBlob.size === 0) {
      console.log("Blob inválido o vacío")
      this.isProcessingVoice = false
      return
    }

    // Mostrar mensaje de usuario
    this.addMessage("🎤 Mensaje de voz enviado", "user")

    try {
      this.showTypingIndicator()
      this.setSendingState(true)

      // Enviar audio al backend
      const response = await window.sendMessageToDjango("", audioBlob)
      let botReply = "Lo siento, no pude procesar tu mensaje de voz."

      if (response && response.success && response.response) {
        botReply = response.response
      } else if (response && response.error) {
        botReply = "⚠️ Error: " + response.error
      }

      this.addMessage(botReply, "bot")
    } catch (error) {
      console.error("Error al procesar voz:", error)
      this.addMessage("⚠️ Error de conexión con el servidor.", "bot")
    } finally {
      this.isProcessingVoice = false
      this.currentRecordingId = null
      this.hideTypingIndicator()
      this.setSendingState(false)
      console.log("Procesamiento de voz completado")
    }
  }

  // Método para limpiar recursos de grabación anterior
  cleanupPreviousRecording() {
    if (this.currentStream) {
      this.currentStream.getTracks().forEach((track) => track.stop())
      this.currentStream = null
    }
    this.mediaRecorder = null
  }

  // Método para actualizar UI del botón de voz
  updateVoiceButtonUI(isRecording) {
    if (isRecording) {
      this.voiceBtn.classList.add("recording")
      this.voiceIcon.classList.add("hidden")
      this.recordingIcon.classList.remove("hidden")
      this.voiceBtn.title = "Detener grabación"
    } else {
      this.voiceBtn.classList.remove("recording")
      this.voiceIcon.classList.remove("hidden")
      this.recordingIcon.classList.add("hidden")
      this.voiceBtn.title = "Nota de voz"
    }
  }

  resetRecordingState() {
    console.log("Reseteando estado de grabación...")
    
    this.isRecording = false
    this.isProcessingVoice = false
    this.audioChunks = []
    this.currentRecordingId = null
    this.voiceClickInProgress = false
    this.lastVoiceClickTime = 0 // Resetear también el tiempo de debounce
    this.cleanupPreviousRecording()
    
    // Resetear UI
    this.updateVoiceButtonUI(false)
  }

  // Método adicional para enviar audio al servidor (opcional)
  async sendAudioToServer(audioBlob) {
    try {
      const formData = new FormData()
      formData.append('audio', audioBlob, 'voice_message.wav')
      formData.append('csrfmiddlewaretoken', window.CSRF_TOKEN)

      const response = await fetch('/chat/message/', {
        method: 'POST',
        body: formData,
        headers: {
          'X-CSRFToken': window.CSRF_TOKEN
        }
      })

      const data = await response.json()
      return data
    } catch (error) {
      console.error('Error enviando audio:', error)
      return { error: 'Error de conexión' }
    }
  }
}

// Inicializar el chatbox cuando el DOM esté listo
document.addEventListener("DOMContentLoaded", () => {
  window.chatboxInstance = new Chatbox()
})

// Funciones adicionales para integración con Django
window.ChatboxAPI = {
  // Función para enviar mensaje desde código externo
  sendMessage: (message) => {
    if (window.chatboxInstance) {
      window.chatboxInstance.sendMessage(message)
    }
  },

  // Función para abrir el chat desde código externo
  openChat: () => {
    if (window.chatboxInstance) {
      window.chatboxInstance.openChat()
    }
  },

  // Función para cerrar el chat desde código externo
  closeChat: () => {
    if (window.chatboxInstance) {
      window.chatboxInstance.closeChat()
    }
  },

  // 🚀 Nueva función para limpiar historial desde código externo
  clearHistory: () => {
    if (window.chatboxInstance) {
      window.chatboxInstance.clearChatHistory()
    }
  }
}
