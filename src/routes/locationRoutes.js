import { Router } from 'express';
import * as LocationController from '../controllers/locationController.js';

const router = Router();

router.get('/', LocationController.getLocations);
router.get('/:id', LocationController.getLocation);
router.post('/', LocationController.createLocation);
router.put('/:id', LocationController.updateLocation);
router.delete('/:id', LocationController.deleteLocation);

export default router;
