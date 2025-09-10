import pool from '../config/bd.js';

// Obtener todos los permisos
export const getPermissions = async () => {
  const result = await pool.query('SELECT * FROM permissions ORDER BY id_permission ASC');
  return result.rows;
};

// Obtener permisos de un rol específico
export const getRolePermissions = async (id_role) => {
  const result = await pool.query(
    `SELECT p.*, r.name AS role_name, r.description AS role_description
      FROM permissions p
      JOIN role_permissions rp ON p.id_permission = rp.permission_id
      JOIN roles r ON rp.id_role = r.id_role
      WHERE rp.id_role = $1;`,
    [id_role]
  );
  return result.rows;
};

// Asignar permisos a un rol
export const assignPermissionsToRole = async (id_role, permissions) => {
  const values = permissions.map((perm_id) => `(${id_role}, ${perm_id})`).join(", ");
  await pool.query(`INSERT INTO role_permissions (id_role, permission_id) VALUES ${values}`);
};

// Eliminar todos los permisos de un rol
export const removePermissionsFromRole = async (id_role) => {
  await pool.query('DELETE FROM role_permissions WHERE id_role = $1', [id_role]);
};
