import { Router } from 'express';
import { getPermissions, getRolePermissions, assignPermissionsToRole } from '../controllers/permissionController.js';
import { verifyAuth } from '../middleware/authMiddleware.js';

const router = Router();

router.get('/permissions', verifyAuth, getPermissions); // Ver todos los permisos
router.get('/permissions/role/:id', verifyAuth, getRolePermissions); // Ver permisos de un rol
router.post('/permissions/assign', verifyAuth, assignPermissionsToRole); // Asignar permisos a un rol

export default router;
