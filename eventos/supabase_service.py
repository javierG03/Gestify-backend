import os
from supabase import create_client, Client
from django.conf import settings

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
SUPABASE_BUCKET = os.getenv("SUPABASE_BUCKET")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

def upload_image_to_supabase(file_obj, file_name):
    """
    Sube una imagen al bucket de Supabase y retorna la URL pública.
    file_obj: archivo (InMemoryUploadedFile, File, etc.)
    file_name: nombre original del archivo (solo para obtener extensión)
    """
    import mimetypes
    import uuid
    from rest_framework.exceptions import ValidationError
    # Validar extensión y tipo MIME
    allowed_types = ["image/jpeg", "image/png", "image/gif", "image/webp"]
    allowed_exts = [".jpg", ".jpeg", ".png", ".gif", ".webp"]
    ext = os.path.splitext(file_name)[1].lower()
    content_type, _ = mimetypes.guess_type(file_name)
    if not content_type:
        content_type = "application/octet-stream"
    if ext not in allowed_exts or content_type not in allowed_types:
        raise ValidationError({"image_file": "Solo se permiten archivos de imagen: jpg, jpeg, png, gif, webp"})

    # Generar nombre único: eventimg_{uuid4}{ext}
    unique_name = f"eventimg_{uuid.uuid4().hex}{ext}"

    file_bytes = file_obj.read()
    res = supabase.storage.from_(SUPABASE_BUCKET).upload(
        unique_name,
        file_bytes,
        file_options={"content-type": content_type}
    )
    if getattr(res, 'error', None):
        raise Exception(f"Error al subir imagen: {res.error['message']}")
    public_url = supabase.storage.from_(SUPABASE_BUCKET).get_public_url(unique_name)
    return public_url
