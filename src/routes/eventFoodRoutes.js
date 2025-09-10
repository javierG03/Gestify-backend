import { Router } from 'express';
import * as EventFoodController from '../controllers/eventFoodController.js';

const router = Router();

router.get('/events/:id_event/food', EventFoodController.getFoodByEvent);
router.post('/events/food', EventFoodController.assignFoodToEvent);
// router.put('/events/:id_event/food/:id_food', EventFoodController.updateFoodInEvent); // Modificado
router.delete('/events/:id_event/food/:id_food', EventFoodController.removeFoodFromEvent);

export default router;
