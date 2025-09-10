import jwt from 'jsonwebtoken';
import * as UserModel from '../models/user.js';
import { createParticipant, confirmParticipant, getParticipant } from '../models/participants.js';
import * as EventModel from '../models/event.js';
import transporter from '../config/emailConfig.js';
import { storeInvitationToken, getInvitationByToken, deleteInvitationToken } from '../models/invitation.js';
import { getInvitationMailOptions } from '../helpers/invitationMailHelper.js';

// Generar y enviar una invitación a un usuario
export const sendInvitation = async (req, res) => {
    try {
        const { id_event, id_user } = req.body;
        const { id_role } = req.user; // Rol del usuario autenticado

        // Solo los Administradores (rol 1) y Gestores de Eventos (rol 2) pueden enviar invitaciones
        if (id_role !== 1 && id_role !== 2) {
            return res.status(403).json({ error: 'No tienes permisos para generar invitaciones.' });
        }

        // Verificar si el usuario existe
        const user = await UserModel.getUserById(id_user);
        if (!user) {
            return res.status(404).json({ error: 'Usuario no encontrado.' });
        }

        // Verificar si el evento existe
        const event = await EventModel.getEventById(id_event);
        if (!event) {
            return res.status(404).json({ error: 'Evento no encontrado.' });
        }

        // Generar token único
        const token = jwt.sign(
            { id_event, id_user },
            process.env.JWT_SECRET,
            { expiresIn: '7d' }
        );

        // Guardar invitación en memoria (o donde manejes los tokens)
        storeInvitationToken(token, id_event, id_user);

        // Registrar al usuario como participante
        const participant_status_id = 1; // Aquí defines el estado inicial del participante (por ejemplo, 1 = "invitado" o "pendiente")
        await createParticipant(id_user, id_event, participant_status_id);

        // Construir enlace de invitación
        const baseUrl = process.env.URL_FRONT_WEB_DEV;
        const invitationLink = `${baseUrl}/api/invitacion/${token}`;

        // Configurar y enviar el correo
        const mailOptions = getInvitationMailOptions(user.email, event.event_name, id_event, token);
        await transporter.sendMail(mailOptions);

        res.status(200).json({
            mensaje: 'Invitación enviada y participante registrado con éxito.',
            invitationLink
        });

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Error al enviar la invitación y registrar al participante.' });
    }
};


// 📌 Validar la invitación y registrar al usuario en la BD
export const validateInvitation = async (req, res) => {
    try {
        const { token } = req.params;
        
        // Buscar la invitación en memoria
        const invitation = getInvitationByToken(token);
        if (!invitation) {
            return res.status(404).json({ error: 'Invitación no válida o expirada.' });
        }

        const { id_event, id_user } = invitation;

        // Verificar si el usuario ya está registrado en el evento
        const existingParticipant = await getParticipant(id_event, id_user);
        if (existingParticipant) {
            // Cambiar el estado del Participante a "Confirmado"
            await confirmParticipant(id_event, id_user);

            // Eliminar la invitación de memoria
            deleteInvitationToken(token);

            res.status(200).json({ mensaje: 'Confirmacion aceptada para el evento' });
        }

    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Error al validar la invitación.' });
    }
};

// Rechazar invitación y marcar participante como Cancelado
export const rejectInvitation = async (req, res) => {
    try {
        const { token } = req.params;
        // Buscar la invitación en memoria
        const invitation = getInvitationByToken(token);
        if (!invitation) {
            return res.status(404).json({ error: 'Invitación no válida o expirada.' });
        }
        const { id_event, id_user } = invitation;
        // Verificar si el usuario ya está registrado en el evento
        const existingParticipant = await getParticipant(id_event, id_user);
        if (existingParticipant) {
            // Cambiar el estado del Participante a "Cancelado" (4)
            await confirmParticipant(id_event, id_user, 4); // Modifica confirmParticipant para aceptar el nuevo estado
            // Eliminar la invitación de memoria
            deleteInvitationToken(token);
            return res.status(200).json({ mensaje: 'Has rechazado la invitación al evento.' });
        }
        return res.status(404).json({ error: 'Participante no encontrado.' });
    } catch (error) {
        console.error(error);
        res.status(500).json({ error: 'Error al rechazar la invitación.' });
    }
};