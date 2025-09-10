import { Router } from 'express';
import { sendInvitation, validateInvitation, rejectInvitation } from '../controllers/invitationController.js';
import { verifyAuth } from '../middleware/authMiddleware.js';

const router = Router();

router.post('/invitacion', verifyAuth, sendInvitation); // Generar y enviar invitación (Solo gestores)
router.get('/invitacion/:token', validateInvitation); // Validar la invitación cuando el usuario accede al enlace
router.get('/invitacion/rechazar/:token', rejectInvitation); // Ruta para rechazar invitación

export default router;
