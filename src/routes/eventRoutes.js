import { Router } from 'express';
import * as EventController from '../controllers/eventController.js';
import { verifyAuth } from '../middleware/authMiddleware.js'; 


const router = Router();

router.get('/', EventController.getEvents);
router.get('/:id', EventController.getEvent);
router.get('/users/:id', verifyAuth, EventController.getEventByIdForUserId); 
router.get('/prices/:id', EventController.getPriceEventById);
router.post('/', EventController.createEvent);
router.put('/:id', EventController.uploadImage, EventController.updateEvent);
router.put('/:id/status', EventController.updateEventStatusController);
router.delete('/:id', EventController.deleteEvent);

export default router;
