import pool from '../config/bd.js';

// Registrar un nuevo participante
export const createParticipant = async (user_id, event_id, participant_status_id) => {
  const result = await pool.query(
    `INSERT INTO participants (user_id, event_id, participant_status_id) 
     VALUES ($1, $2, $3) RETURNING *`,
    [user_id, event_id, participant_status_id]
  );
  return result.rows[0];
};

// Obtener todos los participantes
export const getAllParticipants = async () => {
  const result = await pool.query(
    `SELECT p.id_participants,
            p.user_id,  
            u.name AS user_name,
            u.last_name AS user_last_name,  
            e.name AS event_name, 
            e.image_url AS event_image_url, 
            e.type_of_event_id, 
            tof.start_time AS event_start_time,
            ps.status_name 
     FROM participants p
     JOIN users u ON p.user_id = u.id_user
     JOIN events e ON p.event_id = e.id_event
     JOIN type_of_event tof ON e.type_of_event_id = tof.id_type_of_event
     JOIN participant_status ps ON p.participant_status_id = ps.id_participant_status
     ORDER BY p.id_participants ASC`
  );
  return result.rows;
};
// Obtener un participante por ID
export const getParticipantById = async (id) => {
  const result = await pool.query(
    `SELECT * FROM participants WHERE id_participants = $1`,
    [id]
  );
  return result.rows[0];
};


// Verificar si un usuario ya está registrado en un evento
export const getParticipant = async (event_id, user_id) => {
  const result = await pool.query(
    `SELECT * FROM participants 
     WHERE event_id = $1 AND user_id = $2`,
    [event_id, user_id]
  );
  return result.rows[0]; 
};


// Actualizar un participante
export const updateParticipantById = async (id, event_id, participant_status_id) => {
  // Si event_id es null/undefined, actualiza solo participant_status_id
  const query = event_id 
    ? `UPDATE participants 
       SET event_id = $1, participant_status_id = $2 
       WHERE id_participants = $3 RETURNING *`
    : `UPDATE participants 
       SET participant_status_id = $1 
       WHERE id_participants = $2 RETURNING *`;

  const values = event_id 
    ? [event_id, participant_status_id, id] 
    : [participant_status_id, id];

  const result = await pool.query(query, values);
  return result.rows[0];
};

// Eliminar un participante
export const deleteParticipantById = async (id) => {
  const result = await pool.query(
    `DELETE FROM participants WHERE id_participants = $1 RETURNING *`, 
    [id]
  );
  return result.rows[0];
};



// Actualizar el estado de un participante basado en user_id y event_id
export const confirmParticipant = async (event_id, user_id, participant_status_id = 2) => {
  const result = await pool.query(
    `UPDATE participants 
     SET participant_status_id = $3 
     WHERE event_id = $1 AND user_id = $2 
     RETURNING *`,
    [event_id, user_id, participant_status_id]
  );
  return result.rows[0];
};
