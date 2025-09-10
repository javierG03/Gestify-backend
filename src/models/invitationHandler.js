import pool from '../config/bd.js';
import * as UserModel from '../models/user.js';
import * as ParticipantModel from '../models/participants.js';

/**
 * Verificar si el usuario ya está registrado en la base de datos.
 * @param {string} email - Email del usuario.
 * @returns {object|null} - Datos del usuario si existe, null si no.
 */
export const checkUserExists = async (email) => {
    return await UserModel.getUserByEmail(email);
};

/**
 * Crear un nuevo usuario en la base de datos.
 * @param {object} userData - Datos del usuario.
 * @returns {object} - Datos del usuario creado.
 */
export const registerUser = async (userData) => {
    return await UserModel.createUser(userData);
};

/**
 * Verificar si un usuario ya está inscrito en un evento.
 * @param {number} id_event - ID del evento.
 * @param {number} id_user - ID del usuario.
 * @returns {object|null} - Datos de la inscripción si existe, null si no.
 */
export const checkParticipantExists = async (id_event, id_user) => {
    return await ParticipantModel.getParticipant(id_event, id_user);
};

/**
 * Inscribir un usuario en un evento en `participants`.
 * @param {number} id_event - ID del evento.
 * @param {number} id_user - ID del usuario.
 * @returns {object} - Datos de la inscripción creada.
 */
export const registerParticipant = async (id_event, id_user) => {
    return await ParticipantModel.addParticipant(id_event, id_user);
};
