"""
eventos/views/ia_assistant.py
Vista para el asistente de IA que responde dudas sobre eventos usando Gemini.
"""
import os
import re
import json
import logging
import unicodedata
from datetime import datetime, timedelta
from difflib import get_close_matches

import google.generativeai as genai
from django.conf import settings
from django.db import models
from django.shortcuts import get_object_or_404
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status, serializers
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
    permission_classes = [AllowAny]  # Público para que cualquiera pregunte

    @extend_schema(
        tags=["IA Assistant"],
        summary="Preguntar a la IA sobre un evento",
        request=None,  # O define un serializer { question: str }
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
            model = genai.GenerativeModel('gemini-2.0-flash')  # Modelo rápido y barato

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


class ChatMessageSerializer(serializers.Serializer):
    message = serializers.CharField()
    history = serializers.ListField(
        child=serializers.DictField(), 
        required=False, 
        help_text="Historial de mensajes previos (opcional)"
    )


class ChatBotView(APIView):
    """
    Chatbot general para recomendaciones de eventos y FAQ
    """
    permission_classes = [AllowAny]
    
    # Cache de ciudades y departamentos
    _ciudades_col = None
    _departamentos_col = None
    
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Cargar ciudades y departamentos desde el fixture (solo una vez)
        if ChatBotView._ciudades_col is None:
            try:
                fixture_path = os.path.join(
                    os.path.dirname(__file__), 
                    '../fixtures/departamentos_ciudades.json'
                )
                with open(fixture_path, encoding='utf-8') as f:
                    data = json.load(f)
                ChatBotView._ciudades_col = [
                    self.normalizar(x['fields']['name']) 
                    for x in data if x['model'].endswith('city')
                ]
                ChatBotView._departamentos_col = [
                    self.normalizar(x['fields']['name']) 
                    for x in data if x['model'].endswith('department')
                ]
            except Exception as e:
                logger.error(f"Error cargando fixture: {str(e)}")
                ChatBotView._ciudades_col = []
                ChatBotView._departamentos_col = []

    @staticmethod
    def normalizar(texto):
        """Normaliza texto removiendo acentos y convirtiendo a minúsculas"""
        return unicodedata.normalize('NFKD', texto).encode('ascii', 'ignore').decode('utf-8').lower()

    @extend_schema(
        tags=["IA Assistant"],
        summary="Chat con el asistente de eventos",
        request=ChatMessageSerializer,
        responses={200: {"answer": "str"}},
    )
    def post(self, request):
        user_message = request.data.get("message", "").strip()
        history = request.data.get("history", [])
        if not user_message:
            return Response(
                {"error": "Por favor escribe un mensaje."}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        lower_msg = self.normalizar(user_message)
        palabras_usuario = lower_msg.split()

        # --- Si el usuario pregunta solo por la hora y hay historial de eventos ---
        if re.search(r"hora|a que hora|¿a qué hora|cuando|¿cuando|cuándo|¿cuándo", lower_msg) and history:
            # Buscar en el historial la última respuesta con eventos
            eventos_previos = []
            for h in reversed(history):
                # Busca una respuesta que contenga eventos listados (por el formato '- nombre: ...')
                if isinstance(h, dict) and 'answer' in h and '-' in h['answer']:
                    # Extraer líneas de eventos
                    for linea in h['answer'].split('\n'):
                        if linea.strip().startswith('-'):
                            # Intentar extraer nombre y fecha/hora si está presente
                            eventos_previos.append(linea.strip('- ').strip())
                    break
            if eventos_previos:
                return Response({
                    "answer": "Aquí tienes los horarios de los eventos que mencioné antes:\n" + '\n'.join(eventos_previos)
                })

        # --- Categorías ---
        categorias_dict = {
            "musica": ["musica", "música"],
            "deporte": ["deporte", "deportes"],
            "educacion": ["educacion", "educación"],
            "tecnologia": ["tecnologia", "tecnología"],
            "arte": ["arte"],
            "otros": ["otros"]
        }
        palabras_recomendacion = [
            "recomienda", "sugerencia", "evento", "interesa", 
            "buscar", "hay", "donde", "cuáles", "cuales"
        ]

        # --- Fuzzy matching categoría ---
        cat = None
        for palabra in palabras_usuario:
            for key, variantes in categorias_dict.items():
                coincidencias = get_close_matches(
                    palabra, 
                    [self.normalizar(v) for v in variantes], 
                    n=1, 
                    cutoff=0.7
                )
                if coincidencias:
                    cat = key
                    break
            if cat:
                break

        # --- Fuzzy matching ciudad ---
        ciudad = None
        for palabra in palabras_usuario:
            coincidencias = get_close_matches(
                palabra, 
                self._ciudades_col, 
                n=1, 
                cutoff=0.7
            )
            if coincidencias:
                ciudad = coincidencias[0]
                break

        # --- Fuzzy matching departamento (y obtener nombre real) ---
        departamento = None
        departamento_real = None
        if ChatBotView._departamentos_col:
            # Cargar mapeo normalizado -> real
            if not hasattr(self, '_departamento_map'):
                fixture_path = os.path.join(
                    os.path.dirname(__file__), 
                    '../fixtures/departamentos_ciudades.json'
                )
                with open(fixture_path, encoding='utf-8') as f:
                    data = json.load(f)
                self._departamento_map = {
                    self.normalizar(x['fields']['name']): x['fields']['name']
                    for x in data if x['model'].endswith('department')
                }
            for palabra in palabras_usuario:
                coincidencias = get_close_matches(
                    palabra, 
                    list(self._departamento_map.keys()), 
                    n=1, 
                    cutoff=0.7
                )
                if coincidencias:
                    departamento = coincidencias[0]
                    departamento_real = self._departamento_map[departamento]
                    break

        # --- Reconocimiento de fechas ---
        hoy = datetime.now().date()
        fecha_inicio = None
        fecha_fin = None
        
        if re.search(r"hoy|esta noche", lower_msg):
            fecha_inicio = hoy
            fecha_fin = hoy
        elif re.search(r"mañana", lower_msg):
            fecha_inicio = hoy + timedelta(days=1)
            fecha_fin = fecha_inicio
        elif re.search(r"fin de semana", lower_msg):
            fecha_inicio = hoy + timedelta((5-hoy.weekday()) % 7)  # Sábado
            fecha_fin = fecha_inicio + timedelta(days=1)  # Domingo
        elif re.search(r"\ben (\w+)\b", lower_msg):
            # Buscar mes por nombre
            meses = [
                "enero", "febrero", "marzo", "abril", "mayo", "junio",
                "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"
            ]
            match = re.search(r"en (\w+)", lower_msg)
            if match and match.group(1) in meses:
                mes_idx = meses.index(match.group(1)) + 1
                fecha_inicio = datetime(hoy.year, mes_idx, 1).date()
                if mes_idx == 12:
                    fecha_fin = datetime(hoy.year+1, 1, 1).date() - timedelta(days=1)
                else:
                    fecha_fin = datetime(hoy.year, mes_idx+1, 1).date() - timedelta(days=1)

        # --- Soporte y FAQ ---
        problemas_soporte = [
            r"no (me )?llego.*(ticket|entrada|correo)",
            r"problema.*(pago|comprar|ticket|entrada)",
            r"no puedo (comprar|pagar)",
            r"error.*(pago|ticket|entrada)",
            r"devoluci[oó]n|reembolso",
            r"olvide.*(contrase[nñ]a|password)"
        ]
        
        for patron in problemas_soporte:
            if re.search(patron, lower_msg):
                return Response({
                    "answer": "Lamentamos el inconveniente. Por favor revisa tu carpeta de spam. "
                             "Si no encuentras tu entrada o tienes problemas con el pago, contáctanos en "
                             "soporte@gestify.com y te ayudaremos lo antes posible."
                })

        # --- FAQ específicas ---
        if re.search(r"devoluci[oó]n|reembolso", lower_msg):
            return Response({
                "answer": "Para solicitar una devolución o reembolso, por favor escribe a "
                         "soporte@gestify.com indicando tu número de compra y el motivo. "
                         "Nuestro equipo te responderá pronto."
            })
        
        if re.search(r"m[eé]todos? de pago|formas? de pago", lower_msg):
            return Response({
                "answer": "Aceptamos tarjetas de crédito, débito y otros métodos electrónicos. "
                         "Si tienes dudas, consulta en la página de pago o escríbenos a soporte@gestify.com."
            })
        
        if re.search(r"c[oó]mo usar (la )?app|ayuda app|funciona app", lower_msg):
            return Response({
                "answer": "Puedes descargar la app de Gestify desde la tienda de tu dispositivo. "
                         "Si tienes dudas sobre su uso, revisa la sección de ayuda en la app o contáctanos."
            })

        # --- Intención de recomendación (categoría/ciudad/fecha) ---
        if (
            any(word in lower_msg for word in palabras_recomendacion)
            or (cat and len(palabras_usuario) <= 3)
            or ciudad or departamento or fecha_inicio
        ):
            # Si NO hay ningún filtro, primero pregunta la categoría
            if not (cat or ciudad or departamento or fecha_inicio):
                return Response({
                    "answer": "¿Qué tipo de eventos te interesan? (música, tecnología, deportes, educación, arte, otros)"
                })
            
            eventos = Event.objects.all()
            
            if cat:
                eventos = eventos.filter(category__icontains=cat)
            if ciudad:
                eventos = eventos.filter(
                    models.Q(location__name__icontains=ciudad) | 
                    models.Q(city_text__icontains=ciudad)
                )
            if departamento_real:
                eventos = eventos.filter(
                    models.Q(location__department__name__iexact=departamento_real) |
                    models.Q(department_text__iexact=departamento_real)
                )
            elif departamento:
                # fallback si no se encontró el nombre real
                eventos = eventos.filter(
                    models.Q(location__department__name__icontains=departamento) |
                    models.Q(department_text__icontains=departamento)
                )
            if fecha_inicio:
                eventos = eventos.filter(start_datetime__date__gte=fecha_inicio)
            if fecha_fin:
                eventos = eventos.filter(start_datetime__date__lte=fecha_fin)
            
            eventos = eventos.order_by('start_datetime')[:5]
            
            if not eventos:
                sugerencia = ""
                if cat and not ciudad:
                    sugerencia = "¿Te gustaría probar con otra ciudad?"
                elif ciudad and not cat:
                    sugerencia = "¿Te gustaría probar con otra categoría?"
                elif not cat and not ciudad:
                    sugerencia = "¿Te gustaría probar con otra búsqueda?"
                else:
                    sugerencia = "¿Quieres buscar en otra ciudad o categoría?"
                return Response({
                    "answer": f"No encontré eventos para tu búsqueda. {sugerencia}"
                })
            
            eventos_info = "\n".join([
                f"- {e.event_name}: {e.description[:60]}... el {e.start_datetime.strftime('%d/%m/%Y')} a las {e.start_datetime.strftime('%H:%M')} en {e.location or e.city_text}"
                for e in eventos
            ])

            # Si el usuario pregunta explícitamente por la hora
            if re.search(r"hora|a qué hora|¿cuándo|cuando", lower_msg):
                respuesta_horas = "\n".join([
                    f"{e.event_name}: {e.start_datetime.strftime('%d/%m/%Y')} a las {e.start_datetime.strftime('%H:%M')}"
                    for e in eventos
                ])
                return Response({
                    "answer": f"Estos son los horarios de los eventos encontrados:\n{respuesta_horas}"
                })

            prompt = f"""
Eres un asistente de eventos de Gestify. Solo puedes responder sobre eventos, tickets, recomendaciones y dudas del sistema. 
Si te preguntan algo fuera de ese contexto, responde: 'Solo puedo ayudarte con temas de eventos en Gestify.'

El usuario busca eventos{f" de la categoría '{cat}'" if cat else ""}. Estos son los eventos disponibles:
{eventos_info}

Recomiéndale 2 o 3 eventos de la lista, con una frase breve y entusiasta. Si no hay suficientes, sugiere que vuelva a consultar pronto.
"""
            
            return self._call_gemini(prompt)

        # --- Preguntas fuera del negocio ---
        if any(word in lower_msg for word in ["presidente", "clima", "noticia", "dólar", "dolar", "fútbol", "futbol", "gobierno"]):
            return Response({
                "answer": "Solo puedo ayudarte con temas de eventos, tickets o recomendaciones en Gestify."
            })

        # --- Saludo o inicio de chat ---
        if any(word in lower_msg for word in ["hola", "buenas", "ayuda", "iniciar", "empezar", "chat"]):
            user = request.user if hasattr(request, 'user') and request.user and request.user.is_authenticated else None
            nombre = user.first_name if user and user.first_name else (user.username if user else None)
            saludo = f"¡Hola{f' {nombre}' if nombre else ''}! 👋 Soy tu asistente de eventos Gestify.\n"
            return Response({
                "answer": (
                    saludo +
                    "Puedo recomendarte eventos, ayudarte con tus tickets o resolver tus dudas.\n"
                    "Por ejemplo, puedes preguntarme:\n"
                    "- ¿Qué eventos hay este fin de semana?\n"
                    "- ¿Hay eventos de música en Bogotá?\n"
                    "- ¿Cómo puedo comprar un ticket?\n\n"
                    "¿Sobre qué te gustaría saber hoy?"
                )
            })

        # --- Por defecto, delegar a Gemini con contexto limitado ---
        prompt = f"""
Eres un asistente de eventos de Gestify. Solo puedes responder sobre eventos, tickets, recomendaciones y dudas del sistema. 
Si te preguntan algo fuera de ese contexto, responde: 'Solo puedo ayudarte con temas de eventos en Gestify.'

El usuario dice: '{user_message}'
"""
        return self._call_gemini(prompt)

    def _call_gemini(self, prompt):
        """Método auxiliar para llamar a Gemini"""
        try:
            api_key = os.getenv("GEMINI_API_KEY")
            if not api_key:
                return Response(
                    {"answer": "El servicio de IA no está disponible."}, 
                    status=status.HTTP_503_SERVICE_UNAVAILABLE
                )
            
            genai.configure(api_key=api_key)
            model = genai.GenerativeModel('gemini-2.0-flash')
            response = model.generate_content(prompt)
            
            return Response({"answer": response.text})
        
        except Exception as e:
            logger.error(f"Error Gemini: {str(e)}")
            return Response(
                {"answer": "Hubo un problema consultando a la IA. Intenta más tarde."}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )