import { Router } from 'express';
import * as CategoryController from '../controllers/categoryController.js';

const router = Router();

router.get('/categories', CategoryController.getCategories);
router.get('/categories/:id', CategoryController.getCategory);
router.post('/categories', CategoryController.createCategory);
router.put('/categories/:id', CategoryController.updateCategory);
router.delete('/categories/:id', CategoryController.deleteCategory);

export default router;
