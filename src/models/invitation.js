const invitationCache = new Map();
import pool from '../config/bd.js';

/**
 * Almacenar una invitación en memoria
 * @param {string} token - Token único de invitación
 * @param {number} id_event - ID del evento
 * @param {number} id_user - ID del usuario invitado
 */
export const storeInvitationToken = (token, id_event, id_user) => {
    invitationCache.set(token, { id_event, id_user, createdAt: Date.now() });
};

/**
 * Obtener una invitación almacenada en memoria
 * @param {string} token - Token de invitación
 * @returns {object | null} - Datos de la invitación o null si no existe
 */
export const getInvitationByToken = (token) => {
    return invitationCache.get(token) || null;
};

/**
 * Eliminar una invitación después de ser aceptada
 * @param {string} token - Token de invitación
 */
export const deleteInvitationToken = (token) => {
    invitationCache.delete(token);
};

// Verificar si un usuario ya está registrado en un evento
export const getParticipant = async (id_event, id_user) => {
    const result = await pool.query(
        'SELECT * FROM participants WHERE event_id = $1 AND user_id = $2',
        [id_event, id_user]
    );
    return result.rows[0]; // Retorna el participante o undefined
};

// Registrar un usuario en un evento con estado "Pendiente"
export const addParticipant = async (id_event, id_user) => {
    const result = await pool.query(
        'INSERT INTO participants (event_id, user_id, participant_status_id) VALUES ($1, $2, 1) RETURNING *',
        [id_event, id_user]
    );
    return result.rows[0]; // Retorna el participante recién registrado
};

export default invitationCache;
