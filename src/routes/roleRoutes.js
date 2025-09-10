import { Router } from 'express';
import { getRoles, getRoleById, createRole, updateRole, deleteRole, getRolesWithPermissions } from '../controllers/roleController.js';
import { verifyAuth } from '../middleware/authMiddleware.js'; // Protección con autenticación

const router = Router();

router.get('/roles/with-permissions', verifyAuth, getRolesWithPermissions);
router.get('/roles', verifyAuth, getRoles); // Obtener todos los roles
router.get('/roles/:id', verifyAuth, getRoleById); // Obtener un rol con permisos
router.post('/roles', verifyAuth, createRole); // Crear un nuevo rol
router.put('/roles/:id', verifyAuth, updateRole); // Editar un rol
router.delete('/roles/:id', verifyAuth, deleteRole); // Eliminar un rol


export default router;
