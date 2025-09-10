import * as PermissionModel from '../models/permission.js';

export const getPermissions = async (req, res) => {
    try {
      console.log('Usuario autenticado:', req.user); //Verifica qué usuario está accediendo

      const { id_role } = req.user; // 🔹 Se obtiene el rol del usuario autenticado

      if (id_role !== 1) { //SOLO Superadmin (ID 1) puede ver todos los permisos
        return res.status(403).json({ error: 'No tienes permisos suficientes.' });
      }

      const permissions = await PermissionModel.getPermissions();
      res.status(200).json({ permissions });
    } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error al obtener los permisos.' });
    }
};

// Obtener permisos de un rol específico
export const getRolePermissions = async (req, res) => {
  try {
    const { id_role } = req.params; 
    const permissions = await PermissionModel.getRolePermissions(id_role);

    if (!permissions.length) {
      return res.status(404).json({ error: 'No se encontraron permisos para este rol.' });
    }

    res.status(200).json({ permissions });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los permisos del rol.' });
  }
};


// Asignar permisos a un rol
export const assignPermissionsToRole = async (req, res) => {
  try {
    const { id_role, permissions } = req.body; 

    if (!id_role || !permissions || !permissions.length) {
      return res.status(400).json({ error: 'Se requiere un rol y al menos un permiso.' });
    }

    await PermissionModel.removePermissionsFromRole(id_role);
    await PermissionModel.assignPermissionsToRole(id_role, permissions);

    res.status(200).json({ mensaje: 'Permisos asignados correctamente.' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al asignar permisos al rol.' });
  }
};


