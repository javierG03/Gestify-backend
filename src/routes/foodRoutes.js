import { Router } from 'express';
import * as FoodController from '../controllers/foodController.js';

const router = Router();

router.get('/food', FoodController.getFood);
router.get('/food/:id', FoodController.getFoodById);
router.post('/food', FoodController.createFood);
router.put('/food/:id', FoodController.updateFood);
router.delete('/food/:id', FoodController.deleteFood);

export default router;
