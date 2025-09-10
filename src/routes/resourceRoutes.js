import { Router } from 'express';
import * as ResourceController from '../controllers/resourceController.js';

const router = Router();

router.get('/resources', ResourceController.getResources);
router.get('/resources/:id', ResourceController.getResource);
router.post('/resources', ResourceController.createResource);
router.put('/resources/:id', ResourceController.updateResource);
router.delete('/resources/:id', ResourceController.deleteResource);

export default router;
