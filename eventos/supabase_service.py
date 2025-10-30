import os
from supabase import create_client, Client
from django.conf import settings

SUPABASE_URL = settings.SUPABASE_URL
SUPABASE_KEY = settings.SUPABASE_KEY
SUPABASE_BUCKET = settings.SUPABASE_BUCKET

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image_to_supabase(file_obj, file_name):
    """
    Sube una imagen al bucket de Supabase y retorna la URL pública.
    file_obj: archivo (InMemoryUploadedFile, File, etc.)
    file_name: nombre con el que se guardará en el bucket
    """
    # Subir el archivo al bucket
    res = supabase.storage.from_(SUPABASE_BUCKET).upload(file_name, file_obj.read())
    if res.get('error'):
        raise Exception(f"Error al subir imagen: {res['error']['message']}")
    # Obtener la URL pública
    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(file_name)
    return public_url
