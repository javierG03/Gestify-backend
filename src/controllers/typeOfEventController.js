import * as TypeOfEventModel from '../models/typeOfEvent.js';

// Función helper para convertir strings vacíos a null
const sanitizeValue = (value, type = 'string') => {
  if (value === '' || value === undefined || value === null) {
    return null;
  }
  
  switch (type) {
    case 'number':
      const num = parseFloat(value);
      return isNaN(num) ? null : num;
    case 'integer':
      const int = parseInt(value);
      return isNaN(int) ? null : int;
    case 'string':
    default:
      return value;
  }
};

// Función helper para validar y convertir timestamps
const validateAndConvertTimestamp = (timestamp) => {
  if (!timestamp) return null;
  
  try {
    // Si viene en formato ISO 8601, lo convertimos a Date para validar
    const date = new Date(timestamp);
    if (isNaN(date.getTime())) {
      return null; // Fecha inválida
    }
    
    // Retornamos el timestamp ISO tal como viene (la DB lo manejará)
    return timestamp;
  } catch (error) {
    return null;
  }
};

// Obtener todos los tipos de eventos
export const getTypesOfEvent = async (req, res) => {
  try {
    const types = await TypeOfEventModel.getAllTypesOfEvent();
    res.status(200).json(types);
  } catch (error) {
    console.error('Error en getTypesOfEvent:', error);
    res.status(500).json({ error: 'Error al obtener los tipos de eventos' });
  }
};

// Obtener un tipo de evento por ID
export const getTypeOfEvent = async (req, res) => {
  try {
    const { id } = req.params;
    const type = await TypeOfEventModel.getTypeOfEventById(id);
    if (!type) {
      return res.status(404).json({ error: 'Tipo de evento no encontrado' });
    }
    res.status(200).json(type);
  } catch (error) {
    console.error('Error en getTypeOfEvent:', error);
    res.status(500).json({ error: 'Error al obtener el tipo de evento' });
  }
};

// Crear un nuevo tipo de evento (CORREGIDO PARA TIMESTAMP)
export const createTypeOfEvent = async (req, res) => {
  try {
    const { 
      event_type, 
      description, 
      start_time, 
      end_time, 
      max_participants, 
      video_conference_link, 
      price, 
      category_id 
    } = req.body;

    // Validar campo obligatorio
    if (!event_type || event_type.trim() === '') {
      return res.status(400).json({ error: 'El tipo de evento es obligatorio' });
    }

    console.log('Datos recibidos en createTypeOfEvent:', req.body);

    // Sanitizar y convertir los datos
    const sanitizedData = {
      event_type: event_type.trim(),
      description: sanitizeValue(description),
      start_time: validateAndConvertTimestamp(start_time),
      end_time: validateAndConvertTimestamp(end_time),
      max_participants: sanitizeValue(max_participants, 'integer'),
      video_conference_link: sanitizeValue(video_conference_link),
      price: sanitizeValue(price, 'number'),
      category_id: sanitizeValue(category_id, 'integer')
    };

    console.log('Datos sanitizados:', sanitizedData);

    // Validación adicional de horarios (CORREGIDA)
    if (sanitizedData.start_time && sanitizedData.end_time) {
      const startDate = new Date(sanitizedData.start_time);
      const endDate = new Date(sanitizedData.end_time);
      
      // Verificar que las fechas son válidas
      if (isNaN(startDate.getTime())) {
        return res.status(400).json({ error: 'Formato de hora de inicio inválido. Use formato ISO 8601' });
      }
      if (isNaN(endDate.getTime())) {
        return res.status(400).json({ error: 'Formato de hora de fin inválido. Use formato ISO 8601' });
      }
      
      // Verificar que la hora de fin sea posterior a la de inicio
      if (endDate <= startDate) {
        return res.status(400).json({ error: 'La hora de fin debe ser posterior a la hora de inicio' });
      }
    }

    const newType = await TypeOfEventModel.createTypeOfEvent(
      sanitizedData.event_type,
      sanitizedData.description,
      sanitizedData.start_time,
      sanitizedData.end_time,
      sanitizedData.max_participants,
      sanitizedData.video_conference_link,
      sanitizedData.price,
      sanitizedData.category_id
    );

    console.log('Tipo de evento creado exitosamente:', newType);
    res.status(201).json(newType);
  } catch (error) {
    console.error('Error en createTypeOfEvent:', error);
    console.error('Error details:', error.message);
    
    // Manejo específico de errores de PostgreSQL
    if (error.code === '22007') { // invalid_datetime_format
      return res.status(400).json({ error: 'Formato de fecha/hora inválido. Use formato ISO 8601' });
    }
    if (error.code === '22P02') { // invalid_text_representation
      return res.status(400).json({ error: 'Formato de datos inválido' });
    }
    if (error.code === '23514') { // check_violation (constraint)
      return res.status(400).json({ error: 'La hora de fin debe ser posterior a la hora de inicio' });
    }
    
    res.status(500).json({ error: 'Error al crear el tipo de evento' });
  }
};

// Actualizar un tipo de evento (CORREGIDO PARA TIMESTAMP)
export const updateTypeOfEvent = async (req, res) => {
  try {
    const { id } = req.params;
    const { 
      event_type, 
      description, 
      start_time, 
      end_time, 
      max_participants, 
      video_conference_link, 
      price, 
      category_id 
    } = req.body;

    // Validar que el ID sea válido
    if (!id || isNaN(parseInt(id))) {
      return res.status(400).json({ error: 'ID de tipo de evento inválido' });
    }

    console.log('Actualizando tipo de evento ID:', id, 'con datos:', req.body);

    // Sanitizar y convertir los datos
    const sanitizedData = {
      event_type: event_type ? event_type.trim() : '',
      description: sanitizeValue(description),
      start_time: validateAndConvertTimestamp(start_time),
      end_time: validateAndConvertTimestamp(end_time),
      max_participants: sanitizeValue(max_participants, 'integer'),
      video_conference_link: sanitizeValue(video_conference_link),
      price: sanitizeValue(price, 'number'),
      category_id: sanitizeValue(category_id, 'integer')
    };

    // Validar campo obligatorio
    if (!sanitizedData.event_type) {
      return res.status(400).json({ error: 'El tipo de evento es obligatorio' });
    }

    // Validación de horarios (CORREGIDA)
    if (sanitizedData.start_time && sanitizedData.end_time) {
      const startDate = new Date(sanitizedData.start_time);
      const endDate = new Date(sanitizedData.end_time);
      
      if (isNaN(startDate.getTime()) || isNaN(endDate.getTime())) {
        return res.status(400).json({ error: 'Formato de horario inválido. Use formato ISO 8601' });
      }
      
      if (endDate <= startDate) {
        return res.status(400).json({ error: 'La hora de fin debe ser posterior a la hora de inicio' });
      }
    }

    const updatedType = await TypeOfEventModel.updateTypeOfEvent(
      id,
      sanitizedData.event_type,
      sanitizedData.description,
      sanitizedData.start_time,
      sanitizedData.end_time,
      sanitizedData.max_participants,
      sanitizedData.video_conference_link,
      sanitizedData.price,
      sanitizedData.category_id
    );

    if (!updatedType) {
      return res.status(404).json({ error: 'Tipo de evento no encontrado' });
    }

    console.log('Tipo de evento actualizado exitosamente:', updatedType);
    res.status(200).json(updatedType);
  } catch (error) {
    console.error('Error en updateTypeOfEvent:', error);
    
    if (error.code === '22007' || error.code === '22P02') {
      return res.status(400).json({ error: 'Formato de datos inválido' });
    }
    if (error.code === '23514') {
      return res.status(400).json({ error: 'La hora de fin debe ser posterior a la hora de inicio' });
    }
    
    res.status(500).json({ error: 'Error al actualizar el tipo de evento' });
  }
};

// Eliminar un tipo de evento
export const deleteTypeOfEvent = async (req, res) => {
  try {
    const { id } = req.params;
    
    if (!id || isNaN(parseInt(id))) {
      return res.status(400).json({ error: 'ID de tipo de evento inválido' });
    }

    const deletedType = await TypeOfEventModel.deleteTypeOfEvent(id);

    if (!deletedType) {
      return res.status(404).json({ error: 'Tipo de evento no encontrado' });
    }

    console.log('Tipo de evento eliminado:', deletedType);
    res.status(200).json({ mensaje: 'Tipo de evento eliminado correctamente' });
  } catch (error) {
    console.error('Error en deleteTypeOfEvent:', error);
    res.status(500).json({ error: 'Error al eliminar el tipo de evento' });
  }
};