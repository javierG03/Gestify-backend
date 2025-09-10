import * as RoleModel from '../models/role.js';

// Obtener todos los roles
export const getRoles = async (req, res) => {
  try {
    const roles = await RoleModel.getRoles();
    res.status(200).json({ roles });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los roles.' });
  }
};

// Obtener un rol por ID con sus permisos
export const getRoleById = async (req, res) => {
  try {
    const { id } = req.params;
    const role = await RoleModel.getRoleById(id);
    if (!role) return res.status(404).json({ error: 'Rol no encontrado.' });

    const permissions = await RoleModel.getRolePermissions(id);
    role.permissions = permissions;

    res.status(200).json({ role });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener el rol.' });
  }
};

// Crear un nuevo rol con permisos
export const createRole = async (req, res) => {
  try {
    const { role_name, description, permissions } = req.body;

    if (!role_name || !description) {
      return res.status(400).json({ error: 'El nombre y la descripción son obligatorios.' });
    }

    // Crear rol
    const newRole = await RoleModel.createRole(role_name, description);

    // Asignar permisos si se enviaron
    if (permissions && permissions.length > 0) {
      await RoleModel.assignPermissionsToRole(newRole.id_role, permissions);
    }

    res.status(201).json({ mensaje: 'Rol creado exitosamente.', role: newRole });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al crear el rol.' });
  }
};

// Editar un rol existente y actualizar permisos
export const updateRole = async (req, res) => {
  try {
    const { id } = req.params;
    const { role_name, description, permissions } = req.body;

    if (!role_name || !description) {
      return res.status(400).json({ error: 'El nombre y la descripción son obligatorios.' });
    }

    // Actualizar información del rol
    const updatedRole = await RoleModel.updateRole(id, role_name, description);
    if (!updatedRole) return res.status(404).json({ error: 'Rol no encontrado.' });

    // Actualizar permisos solo si se envían
    if (permissions) {
      await RoleModel.updateRolePermissions(id, permissions);
    }

    res.status(200).json({ mensaje: 'Rol actualizado correctamente.', role: updatedRole });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al actualizar el rol.' });
  }
};

// Eliminar un rol
export const deleteRole = async (req, res) => {
  try {
    const { id } = req.params;

    // Eliminar permisos asociados antes de borrar el rol
    await RoleModel.removePermissionsFromRole(id);

    // Eliminar rol
    const deletedRole = await RoleModel.deleteRole(id);
    if (!deletedRole) return res.status(404).json({ error: 'Rol no encontrado.' });

    res.status(200).json({ mensaje: 'Rol eliminado correctamente.' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al eliminar el rol.' });
  }
};

export const getRolesWithPermissions = async (req, res) => {
  try {
    const roles = await RoleModel.getRolesWithPermissions();
    res.status(200).json({ roles });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los roles con sus permisos.' });
  }
};
