"""
eventos/views/ia_assistant.py
Vista para el asistente de IA que responde dudas sobre eventos usando Gemini.
"""
import os
import logging
import google.generativeai as genai
from django.conf import settings
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import AllowAny
from drf_spectacular.utils import extend_schema, OpenApiParameter
from ..models import Event
from usuarios.serializers import EmptySerializer
logger = logging.getLogger(__name__)

class EventQAView(APIView):
    """
    Recibe una pregunta sobre un evento y usa Gemini para responderla
    basándose en la descripción del evento.
    """
    permission_classes = [AllowAny] # Público para que cualquiera pregunte

    @extend_schema(
        tags=["IA Assistant"],
        summary="Preguntar a la IA sobre un evento",
        request=None, # O define un serializer { question: str }
        responses={200: {"answer": "str"}},
    )
    def post(self, request, event_id):
        # 1. Obtener la pregunta
        question = request.data.get("question")
        if not question:
            return Response(
                {"error": "Por favor escribe una pregunta."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        # 2. Buscar el evento
        event = get_object_or_404(Event, pk=event_id)

        # 3. Configurar Gemini
        api_key = os.getenv("GEMINI_API_KEY")
        if not api_key:
            logger.error("Falta GEMINI_API_KEY en variables de entorno")
            return Response(
                {"error": "El servicio de IA no está configurado."}, 
                status=status.HTTP_503_SERVICE_UNAVAILABLE
            )

        try:
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash') # Modelo rápido y barato

            # 4. Construir el Prompt (La magia)
            # Le damos contexto y reglas claras a la IA.
            prompt = f"""
            Actúa como un asistente útil y amable para el evento "{event.event_name}".
            
            Información del evento:
            - Descripción: {event.description}
            - Fecha Inicio: {event.start_datetime}
            - Ubicación: {event.location if event.location else event.city_text}
            - Edad Mínima: {event.min_age if event.min_age else "Todas las edades"}
            
            El usuario pregunta: "{question}"

            Instrucciones:
            1. Responde SOLO basándote en la información de arriba.
            2. Si la respuesta no está en la información, di amablemente que contacte al organizador. NO inventes datos.
            3. Sé breve y directo (máximo 2-3 frases).
            4. Usa un tono entusiasta.
            """

            # 5. Llamar a Gemini
            response = model.generate_content(prompt)
            
            return Response({
                "answer": response.text
            }, status=status.HTTP_200_OK)

        except Exception as e:
            logger.error(f"Error llamando a Gemini: {str(e)}")
            return Response(
                {"error": "Hubo un problema consultando a la IA. Intenta más tarde."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )