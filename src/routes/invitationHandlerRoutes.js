import { Router } from 'express';
import { processInvitation } from '../controllers/invitationHandlerController.js';

const router = Router();

// Procesar la invitación y registrar al usuario si es necesario
router.get('/procesar-invitacion/:token', processInvitation);

export default router;
