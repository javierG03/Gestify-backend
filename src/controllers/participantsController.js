import { 
    createParticipant, 
    getAllParticipants, 
    getParticipantById,
    updateParticipantById, 
    deleteParticipantById 
  } from '../models/participants.js';
  
  import { getUserByEmail } from '../models/user.js';
  import pool from '../config/bd.js';
  
  // Función para verificar permisos por `user_id`
  const hasPermissionByUserId = async (user_id) => {
    const result = await pool.query(
      `SELECT r.id_role 
       FROM user_role ur
       JOIN roles r ON ur.role_id = r.id_role
       WHERE ur.user_id = $1`, 
      [user_id]
    );
  
    if (result.rows.length === 0) return false;
    
    const role_id = result.rows[0].id_role;
    return role_id === 1 || role_id === 2; // Solo administradores y moderadores pueden hacer cambios
  };

  export const registerParticipant = async (req, res) => {
    try {
      const { user_email, participant_email, event_id, participant_status_id } = req.body;
  
      // Obtener `user_id` del usuario que hace la acción (debe tener role_id 1 o 2)
      const requestingUser = await getUserByEmail(user_email);
      if (!requestingUser) {
        return res.status(404).json({ message: "Usuario autenticado no encontrado" });
      }
  
      if (!(await hasPermissionByUserId(requestingUser.id_user))) {
        return res.status(403).json({ message: "Acceso denegado. No puedes registrar participantes." });
      }
  
      // Obtener `user_id` del usuario que será registrado
      const participantUser = await getUserByEmail(participant_email);
      if (!participantUser) {
        return res.status(404).json({ message: "Usuario a registrar no encontrado" });
      }
  
      // Insertar participante en la base de datos (no importa su role_id)
      const participant = await createParticipant(participantUser.id_user, event_id, participant_status_id);
      res.status(201).json(participant);
    } catch (error) {
      res.status(500).json({ message: "Error al registrar participante", error });
    }
  };

  export const getParticipants = async (req, res) => {
    try {
      // Obtener todos los participantes (sin restricciones de permisos)
      const participants = await getAllParticipants();
      res.status(200).json(participants);
    } catch (error) {
      res.status(500).json({ message: "Error al obtener participantes", error });
    }
  };
  
  
  export const updateParticipant = async (req, res) => {
    try {
      const { user_id } = req.params;
      const { participant_status_id } = req.body;
  
      // Pasa null para event_id si no es relevante
      const updatedParticipant = await updateParticipantById(user_id, null, participant_status_id);
      
      if (!updatedParticipant) {
        return res.status(404).json({ message: "Participante no encontrado" });
      }
      res.status(200).json(updatedParticipant);
    } catch (error) {
      res.status(500).json({ message: "Error al actualizar", error: error.message });
    }
  };
  
  export const deleteParticipant = async (req, res) => {
    try {
      const { user_id } = req.params; // Usuario que hace la acción
      const { id_participants } = req.body; // Participante a eliminar
  
      // Verificar permisos del usuario que realiza la acción
      if (!(await hasPermissionByUserId(user_id))) {
        return res.status(403).json({ message: "Acceso denegado. No puedes eliminar este participante." });
      }
  
      // Buscar el participante en la BD
      const participant = await getParticipantById(id_participants);
      if (!participant) {
        return res.status(404).json({ message: "Participante no encontrado" });
      }
  
      // Eliminar el participante
      await deleteParticipantById(id_participants);
      res.status(200).json({ message: "Participante eliminado correctamente." });
    } catch (error) {
      res.status(500).json({ message: "Error al eliminar participante", error });
    }
  };
      

  export const getParticipantsByEvent = async (req, res) => {
    try {
      const { event_id } = req.params;
  
      // Obtener los participantes inscritos en el evento
      const result = await pool.query(
        `SELECT p.id_participants, p.user_id, u.name AS user_name, u.last_name AS user_last_name, u.email, ps.status_name 
         FROM participants p
         JOIN users u ON p.user_id = u.id_user
         JOIN participant_status ps ON p.participant_status_id = ps.id_participant_status
         WHERE p.event_id = $1
         ORDER BY p.id_participants ASC`,
        [event_id]
      );
  
      res.status(200).json(result.rows);
    } catch (error) {
      res.status(500).json({ message: "Error al obtener participantes del evento", error });
    }
  };
  

  // Obtener un participante por ID
  export const getParticipant = async (req, res) => {
    try {
      const { id } = req.params;
  
      const participant = await getParticipantById(id);
  
      if (!participant) {
        return res.status(404).json({ message: "Participante no encontrado" });
      }
  
      res.status(200).json(participant);
    } catch (error) {
      res.status(500).json({ message: "Error al obtener participante", error });
    }
  };
  
  