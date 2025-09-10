import jwt from 'jsonwebtoken';
import * as InvitationModel from '../models/invitation.js';
import * as InvitationHandlerModel from '../models/invitationHandler.js';

/**
 * Procesar la invitación: verificar usuario y registrarlo en el evento.
 * @param {object} req - Petición HTTP.
 * @param {object} res - Respuesta HTTP.
 */
export const processInvitation = async (req, res) => {
    try {
        const { token } = req.params;

        // Descomponer el token para obtener datos del usuario y evento
        const invitation = InvitationModel.getInvitationByToken(token);
        if (!invitation) {
            return res.status(404).json({ error: 'Invitación no válida o expirada.' });
        }

        const { id_event, id_user, email, name, last_name } = invitation;

        // Verificar si el usuario ya está registrado
        let user = await InvitationHandlerModel.checkUserExists(email);

        if (!user) {
            // Si el usuario no existe, lo registramos
            const newUser = {
                name,
                last_name,
                email,
                email_verified: true,  // Lo verificamos automáticamente al aceptar la invitación
                password: 'temp1234',  // Se puede obligar a cambiar la contraseña luego
                id_role: 3  // Rol por defecto
            };
            user = await InvitationHandlerModel.registerUser(newUser);
        }

        // Verificar si el usuario ya está inscrito en el evento
        const existingParticipant = await InvitationHandlerModel.checkParticipantExists(id_event, user.id_user);
        if (existingParticipant) {
            return res.status(400).json({ error: 'El usuario ya está registrado en este evento.' });
        }

        // Registrar al usuario en la tabla `participants`
        const participant = await InvitationHandlerModel.registerParticipant(id_event, user.id_user);

        // Eliminar la invitación de memoria
        InvitationModel.deleteInvitationToken(token);

        res.status(200).json({
            mensaje: 'Invitación aceptada y usuario registrado en el evento.',
            usuario: user,
            participante: participant
        });

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Error al procesar la invitación.' });
    }
};
