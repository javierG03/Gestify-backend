import pool from '../config/bd.js';

// Obtener todos los tipos de eventos
export const getAllTypesOfEvent = async () => {
  const result = await pool.query(`SELECT * FROM type_of_event`);
  return result.rows;
};

// Obtener un tipo de evento por ID
export const getTypeOfEventById = async (id_type_of_event) => {
  const result = await pool.query(`SELECT * FROM type_of_event WHERE id_type_of_event = $1`, [id_type_of_event]);
  return result.rows[0];
};

// Crear un nuevo tipo de evento
export const createTypeOfEvent = async (event_type, description, start_time, end_time, max_participants, video_conference_link, price, category_id) => {
  const result = await pool.query(`
    INSERT INTO type_of_event (event_type, description, start_time, end_time, max_participants, video_conference_link, price, category_id)
    VALUES ($1, $2, $3, $4, $5, $6, $7, $8) RETURNING *
  `, [event_type, description, start_time, end_time, max_participants, video_conference_link, price, category_id]);
  return result.rows[0];
};

// Actualizar un tipo de evento
export const updateTypeOfEvent = async (id_type_of_event, event_type, description, start_time, end_time, max_participants, video_conference_link, price, category_id) => {
  const result = await pool.query(`
    UPDATE type_of_event 
    SET event_type = $1, description = $2, start_time = $3, end_time = $4, 
        max_participants = $5, video_conference_link = $6, price = $7, category_id = $8
    WHERE id_type_of_event = $9 RETURNING *
  `, [event_type, description, start_time, end_time, max_participants, video_conference_link, price, category_id, id_type_of_event]);
  return result.rows[0];
};

// Eliminar un tipo de evento
export const deleteTypeOfEvent = async (id_type_of_event) => {
  const result = await pool.query(`DELETE FROM type_of_event WHERE id_type_of_event = $1 RETURNING *`, [id_type_of_event]);
  return result.rows[0];
};
