import express from 'express';
import { 
  registerParticipant, 
  getParticipants,
  getParticipantsByEvent, 
  updateParticipant, 
  deleteParticipant,
  getParticipant 
} from '../controllers/participantsController.js';

const router = express.Router();

router.post('/participants/register', registerParticipant);
router.get('/participants/list', getParticipants);
router.get('/participants/event/:event_id', getParticipantsByEvent);
router.get('/participants/:id', getParticipant); // Obtener un participante por su ID
router.put('/participants/update/:user_id', updateParticipant); // Actualizar solo el estado de un participante
router.delete('/participants/delete/:user_id', deleteParticipant);


export default router;
