import { Router } from 'express';
import { getStatistics } from '../controllers/statisticsController.js';

const router = Router();

// Ruta de solo lectura para obtener estadísticas
router.get('/statistics', getStatistics);

export default router;
