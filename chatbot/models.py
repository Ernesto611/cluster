from django.db import models
from django.core.exceptions import ValidationError
from usuarios.models import Usuario
import os
import uuid

def validar_extension_archivo(value):
    ext_permitidas = ['.pdf', '.docx', '.pptx', '.xlsx', '.jpg', '.jpeg', '.png', '.webp']
    ext = os.path.splitext(value.name)[1].lower()
    if ext not in ext_permitidas:
        raise ValidationError('Formato de archivo no permitido.')

class ChatbotConfig(models.Model):

    nombre = models.CharField(max_length=100, default="Prompt general")
    seccion_fija = models.TextField(
        default = (
            "**Actúa como:**\n\n"
            "Eres ClusterTIM IA, el asistente virtual diseñado para ayudar a los usuarios de RegistroClusterTIM, "
            "página de registro para los cursos, certificaciones, desayunos, networking del ClusterTIM. "
            "Tu identidad es la de un guía amigable, profesional y muy competente en todo lo relacionado con nuestra "
            "oferta educativa y de networking.\n\n"

            "**Tu Objetivo Principal:**\n\n"
            "Tu misión es asistir a los visitantes de nuestra página web, respondiendo de manera precisa y natural a "
            "todas sus preguntas sobre nuestros servicios. Debes facilitarles la información que buscan y motivarlos a "
            "formar parte de nuestra comunidad a través de nuestros cursos y eventos.\n\n"

            "**Base de Conocimiento:**\n\n"
            "Tu única fuente de verdad es la información contenida en nuestra base de datos local. Esta base incluye archivos "
            "como PDFs, documentos de texto, FAQs y calendarios de eventos. No debes inventar respuestas ni utilizar conocimientos "
            "externos. Solo responde en función de la información almacenada.\n\n"

            "**Áreas de Especialización:**\n\n"
            "1. Certificaciones: requisitos, inscripción, costos, beneficios y validez.\n"
            "2. Cursos: temario, duración, modalidad, instructores, precios y fechas.\n"
            "3. Eventos: desayunos de networking, agenda, ponentes, lugar, registro.\n"
            "4. El Sistema [Nombre del Sistema]: qué es, cómo funciona, ventajas e integración.\n\n"

            "**Reglas de Conversación y Comportamiento:**\n\n"
            "1. Tono y estilo:\n"
            "- Naturalidad: lenguaje claro, cercano y profesional.\n"
            "- Proactividad: guía al usuario con preguntas útiles si su duda es muy general.\n\n"

            "2. Llamada a la acción:\n"
            "- Si el usuario muestra interés en un tema, sugiere directamente inscribirse en un curso o certificación.\n"
            "- Ejemplo: \"Todo esto lo abordamos en nuestro Curso de Marketing Digital Avanzado. "
            "¿Te gustaría ver el temario completo o te facilito el enlace para inscribirte?\"\n"
            "- Otro ejemplo: \"Para dominar completamente el sistema, te recomiendo nuestra Certificación Oficial en [Nombre del Sistema].\"\n\n"

            "3. Preguntas fuera de alcance:\n"
            "- Nunca inventes una respuesta.\n"
            "- Si no encuentras la información, responde:\n"
            "\"Esa es una excelente pregunta. No tengo la información sobre ese tema en particular, "
            "pero puedo dirigir tu consulta a un miembro de nuestro equipo experto. ¿Te gustaría que lo hiciera?\"\n"
            "- Alternativamente:\n"
            "\"Hmm, no he encontrado una respuesta exacta para tu pregunta. Para darte la información más precisa, "
            "te recomiendo contactar directamente con nuestro departamento de admisiones:\n"
            "📧 contacto@clustertim.com.mx\n"
            "📱 (443) 416 7326\"\n\n"

            "**Resumen de tu personalidad:**\n"
            "Eres un asistente virtual que no solo da datos, sino que entiende las necesidades del usuario y lo guía "
            "hacia la mejor solución formativa que ClusterTIM puede ofrecerle. Eres el primer paso en su camino de aprendizaje con nosotros."
        ),
        help_text="ADVERTENCIA: No elimines reglas esenciales como no responder fuera de temas del sistema o no inventar información."
    )
    seccion_editable = models.TextField(
        default=(
            "Los usuarios deben crear una cuenta para comprar entradas o registrarse en eventos gratuitos.\n"
            "Cada cuenta tiene un código QR único que sirve como acceso a los eventos.\n"
            "Los métodos de pago disponibles son tarjeta de crédito/débito, PayPal o depósito bancario.\n"
            "Los eventos pueden incluir conferencistas, patrocinadores y stands. Algunos stands están asociados a patrocinadores."
        ),
        help_text="Puedes modificar esta sección según se requiera."
    )
    ultima_actualizacion = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Configuración del Chatbot ({self.id})"

    def generar_prompt_completo(self):

        return f"{self.seccion_fija}\n\n{self.seccion_editable}"

class ChatbotDocumento(models.Model):

    nombre = models.CharField(max_length=255, help_text="Nombre descriptivo del documento")
    archivo = models.FileField(
        upload_to="chatbox/documentos/",
        validators=[validar_extension_archivo],
        help_text="Archivo PDF, DOCX, PPTX, XLSX o imagen"
    )
    fecha_subida = models.DateTimeField(auto_now_add=True)
    activo = models.BooleanField(default=True, help_text="Si está activo se incluirá en el contexto")

    class Meta:
        verbose_name = "Documento del Chatbot"
        verbose_name_plural = "Documentos del Chatbot"

    def __str__(self):
        return self.nombre

class SesionConversacion(models.Model):
    usuario = models.ForeignKey(Usuario, null=True, blank=True, on_delete=models.SET_NULL)
    fecha_inicio = models.DateTimeField(auto_now_add=True)
    ultima_interaccion = models.DateTimeField(auto_now=True)
    uuid = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return f"Conversación #{self.id} - {self.usuario or 'Anónimo'}"

class ConversacionChatbot(models.Model):
    sesion = models.ForeignKey(SesionConversacion, on_delete=models.CASCADE, related_name='mensajes')
    rol = models.CharField(max_length=10, choices=[('user', 'Usuario'), ('assistant', 'Asistente')])
    mensaje = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
