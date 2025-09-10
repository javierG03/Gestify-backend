import { Router } from 'express';
import * as EventResourceController from '../controllers/eventResourceController.js';

const router = Router();

router.get('/events/:id_event/resources', EventResourceController.getResourcesByEvent);
router.post('/event-resources', EventResourceController.handleAssignResourceToEvent);
// router.put('/events/:id_event/resources/:id_resource', EventResourceController.updateResourceInEvent);
router.delete('/events/:id_event/resources/:id_resource', EventResourceController.removeResourceFromEvent);

export default router;
