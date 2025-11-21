# check_models.py
import google.generativeai as genai
import os

# Asegúrate de tener tu API KEY configurada aquí o en las variables de entorno
api_key = ("AIzaSyAPs1YmrI8T06HyLk5yFmGPC-3Dct1N2DE") 

if not api_key:
    print("❌ Error: No se encontró la variable de entorno GEMINI_API_KEY.")
    print("Por favor, configura tu API Key antes de ejecutar este script.")
else:
    try:
        genai.configure(api_key=api_key)
        print(f"✅ API Key configurada. Consultando modelos disponibles...")
        
        available_models = []
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods:
                print(f"- {m.name}")
                available_models.append(m.name)
        
        if not available_models:
            print("⚠️ No se encontraron modelos disponibles para generar contenido.")
            print("Verifica que tu API Key tenga permisos y que la API 'Generative Language API' esté habilitada en Google Cloud/AI Studio.")
        else:
            print(f"\n✨ ¡Listo! Usa uno de los nombres de arriba (sin el prefijo 'models/') en tu vista.")

    except Exception as e:
        print(f"❌ Ocurrió un error al conectar con Google: {e}")