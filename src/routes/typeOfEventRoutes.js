import { Router } from 'express';
import * as TypeOfEventController from '../controllers/typeOfEventController.js';

const router = Router();

router.get('/types-of-event', TypeOfEventController.getTypesOfEvent);
router.get('/types-of-event/:id', TypeOfEventController.getTypeOfEvent);
router.post('/types-of-event', TypeOfEventController.createTypeOfEvent);
router.put('/types-of-event/:id', TypeOfEventController.updateTypeOfEvent);
router.delete('/types-of-event/:id', TypeOfEventController.deleteTypeOfEvent);

export default router;
