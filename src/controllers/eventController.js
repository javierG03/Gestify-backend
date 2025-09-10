import * as EventModel from '../models/event.js';
import multer from 'multer';
import { S3Client, PutObjectCommand, GetObjectCommand } from '@aws-sdk/client-s3';
import { getSignedUrl } from '@aws-sdk/s3-request-presigner';
import dotenv from 'dotenv';

dotenv.config(); // Cargar las variables de entorno

// Configuración de multer para almacenar el archivo temporalmente en la memoria del servidor
const storage = multer.memoryStorage();
const upload = multer({ storage: storage });

// Configuración del cliente S3 para interactuar con Supabase
const s3Client = new S3Client({
  forcePathStyle: true,
  endpoint: process.env.SUPABASE_STORAGE_URL,  // Endpoint S3 de Supabase
  region: 'us-east-2',  // Región de Superbase
  credentials: {
    accessKeyId: process.env.SUPABASE_ACCESS_KEY,  // Usar variable de entorno para la clave de acceso
    secretAccessKey: process.env.SUPABASE_SECRET_KEY,  // Usar variable de entorno para la clave secreta
  },
});

/**
 * Subir un archivo a Supabase Storage usando el protocolo S3
 * @param {Object} file - Archivo recibido desde multer o similar
 * @returns {String} publicUrl - URL pública del archivo subido
 */
const uploadToSupabase = async (file) => {
  try {
    // Generar un nombre único para el archivo
    const fileName = `${Date.now()}-${file.originalname.replace(/\s+/g, '_')}`;
    //const bucketName = 'eventos'; // Nombre de tu bucket en Supabase
    const filePath = `event_images/${fileName}`; // Carpeta dentro del bucket

    console.log(`Intentando subir archivo: ${fileName} al bucket: ${process.env.SUPABASE_BUCKET_NAME}`);

    // Comando para subir el objeto al bucket correcto
    const putCommand = new PutObjectCommand({
      Bucket: process.env.SUPABASE_BUCKET_NAME,
      Key: filePath,
      Body: file.buffer,
      ContentType: file.mimetype,
    });

    // Ejecutar el comando de subida
    await s3Client.send(putCommand);
    console.log('Archivo subido exitosamente:', fileName);

    // Construir la URL pública del archivo
    /*const publicUrl = `https://${process.env.SUPABASE_PROJECT_ID}.supabase.co/storage/v1/object/public/${bucketName}/${filePath}`;
    console.log('URL pública del archivo:', publicUrl);*/
    const publicUrl = `${process.env.SUPABASE_STORAGE_URL}/object/public/${process.env.SUPABASE_BUCKET_NAME}/${filePath}`;
    console.log('URL pública del archivo:', publicUrl);

    return publicUrl;
  } catch (error) {
    console.error('Error detallado al subir la imagen:', error);
    if (error.$response) {
      console.error('Respuesta cruda:', error.$response);
    }
    throw new Error(`Error al subir la imagen: ${error.message}`);
  }
};

// Middleware para manejar la subida de imagen
export const uploadImage = upload.single('image');  // Definir middleware para subida de imagen

// Crear un nuevo evento
export const createEvent = async (req, res) => {
  try {
    // Usar el middleware para manejar la subida de la imagen
    uploadImage(req, res, async (err) => {
      if (err) {
        console.error('Error en middleware multer:', err);
        return res.status(400).json({ error: 'Error al procesar la imagen' });
      }

      const { name, event_state_id, user_id_created_by, location_id, type_of_event_id } = req.body;

      // Verificar campos obligatorios
      if (!user_id_created_by) {
        return res.status(400).json({ error: 'El campo user_id_created_by es obligatorio' });
      }

      let image_url = null;
      if (req.file) {
        try {
          image_url = await uploadToSupabase(req.file);
        } catch (uploadError) {
          console.error('Error al subir la imagen:', uploadError);
          return res.status(500).json({ error: uploadError.message });
        }
      }

      const image_url_array = image_url ? `{${image_url}}` : null;
      // array real
      //const image_url_array = image_url ? [image_url] : [];

      // Crear el evento con la URL de la imagen
      const newEvent = await EventModel.createEvent(name, event_state_id, user_id_created_by, image_url_array, location_id, type_of_event_id);
      res.status(201).json(newEvent);
    });
  } catch (error) {
    console.error('Error general en createEvent:', error);
    res.status(500).json({ error: 'Error al crear el evento' });
  }
};

// Obtener todos los eventos
export const getEvents = async (req, res) => {
  try {
    const events = await EventModel.getAllEvents();
    res.status(200).json(events);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los eventos' });
  }
};


// Obtener un evento por ID
export const getEvent = async (req, res) => {
  try {
    const { id } = req.params;
    const event = await EventModel.getEventById(id);
    if (!event) {
      return res.status(404).json({ error: 'Evento no encontrado' });
    }
    res.status(200).json(event);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener el evento' });
  }
};

// Obtener un evento por ID, validando que pertenece al usuario autenticado
export const getEventByIdForUserId = async (req, res) => {
  try {
    const userId = req.user.id_user; // Obtiene el ID del usuario autenticado
    const events = await EventModel.getEventByIdForUser(userId);

    if (events.length === 0) {
      return res.status(404).json({ error: 'No se encontraron eventos para este usuario' });
    }

    res.status(200).json(events);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los eventos del usuario' });
  }
};

// Obtener un evento por ID
export const getPriceEventById = async (req, res) => {
  try {
    const { id } = req.params;
    const event = await EventModel.getPriceEventById(id);
    if (!event) {
      return res.status(404).json({ error: 'Evento no encontrado' });
    }
    res.status(200).json(event);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener el evento' });
  }
};

// Actualizar un evento
export const updateEvent = async (req, res) => {
  try {
    const { id } = req.params;
    const { name, event_state_id, type_of_event_id, location_id } = req.body;

    if (!name || !event_state_id || !type_of_event_id || !location_id) {
      return res.status(400).json({ error: 'Faltan campos obligatorios para actualizar el evento' });
    }

    // Si el usuario sube una nueva imagen, la subimos a Supabase
    const image_url = req.file ? await uploadToSupabase(req.file) : null;

    const image_url_array = image_url ? `{${image_url}}` : null;

    // Actualizar el evento, incluyendo la URL de la imagen si fue proporcionada
    const updatedEvent = await EventModel.updateEvent(id, name, event_state_id, type_of_event_id, location_id, image_url_array);

    if (!updatedEvent) {
      return res.status(404).json({ error: 'Evento no encontrado' });
    }

    res.status(200).json(updatedEvent);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al actualizar el evento' });
  }
};


// Actualizar el estado de un evento
export const updateEventStatusController = async (req, res) => {
  const { event_state_id } = req.body;
  const { id } = req.params;

  if (!event_state_id) {
    return res.status(400).json({ message: 'Event State ID is required' });
  }

  try {
    const updatedEvent = await EventModel.updateEventStatus(id, event_state_id);

    if (!updatedEvent) {
      return res.status(404).json({ message: 'Event not found or no changes made' });
    }

    return res.status(200).json({
      message: 'Event status updated successfully',
      event: updatedEvent
    });
  } catch (error) {
    console.error(error);
    return res.status(500).json({ message: 'Internal server error' });
  }
};


// Eliminar un evento
export const deleteEvent = async (req, res) => {
  try {
    const { id } = req.params;
    const deletedEvent = await EventModel.deleteEvent(id);
    if (!deletedEvent) {
      return res.status(404).json({ error: 'Evento no encontrado' });
    }
    res.status(200).json({ mensaje: 'Evento eliminado correctamente' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al eliminar el evento' });
  }
};
