import pool from '../config/bd.js';

// Obtener todos los roles
export const getRoles = async () => {
  const result = await pool.query('SELECT * FROM roles ORDER BY id_role ASC');
  return result.rows;
};

// Obtener un rol por ID
export const getRoleById = async (id_role) => {
  const result = await pool.query('SELECT * FROM roles WHERE id_role = $1', [id_role]);
  return result.rows[0];
};

// Crear un nuevo rol
export const createRole = async (role_name, description) => {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Insertar el nuevo rol
    const result = await client.query(
      'INSERT INTO roles (name, description) VALUES ($1, $2) RETURNING *',
      [role_name, description]
    );

    await client.query('COMMIT');
    return result.rows[0];
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
};

// Editar un rol
export const updateRole = async (id_role, role_name, description) => {
  const result = await pool.query(
    'UPDATE roles SET name = $1, description = $2 WHERE id_role = $3 RETURNING *',
    [role_name, description, id_role]
  );
  return result.rows[0];
};

// Eliminar un rol (incluyendo sus permisos)
export const deleteRole = async (id_role) => {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Eliminar los permisos asociados al rol antes de eliminarlo
    await client.query('DELETE FROM role_permissions WHERE id_role = $1', [id_role]);

    // Eliminar el rol
    const result = await client.query('DELETE FROM roles WHERE id_role = $1 RETURNING *', [id_role]);

    await client.query('COMMIT');
    return result.rows[0];
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
};

// Obtener permisos de un rol
export const getRolePermissions = async (id_role) => {
  const result = await pool.query(
    `SELECT p.* FROM permissions p
     JOIN role_permissions rp ON p.id_permission = rp.permission_id
     WHERE rp.id_role = $1`,
    [id_role]
  );
  return result.rows;
};

// Asignar permisos a un rol (múltiples permisos)
export const assignPermissionsToRole = async (id_role, permissions) => {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Insertar permisos nuevos en la tabla intermedia
    const values = permissions.map((perm_id) => `(${id_role}, ${perm_id})`).join(", ");
    await client.query(`INSERT INTO role_permissions (id_role, permission_id) VALUES ${values}`);

    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
};

// Eliminar todos los permisos de un rol
export const removePermissionsFromRole = async (id_role) => {
  await pool.query('DELETE FROM role_permissions WHERE id_role = $1', [id_role]);
};

// Reasignar permisos de un rol (eliminar y asignar nuevos)
export const updateRolePermissions = async (id_role, newPermissions) => {
  const client = await pool.connect();
  try {
    await client.query('BEGIN');

    // Eliminar los permisos anteriores
    await client.query('DELETE FROM role_permissions WHERE id_role = $1', [id_role]);

    // Insertar los nuevos permisos
    if (newPermissions.length > 0) {
      const values = newPermissions.map((perm_id) => `(${id_role}, ${perm_id})`).join(", ");
      await client.query(`INSERT INTO role_permissions (id_role, permission_id) VALUES ${values}`);
    }

    await client.query('COMMIT');
  } catch (error) {
    await client.query('ROLLBACK');
    throw error;
  } finally {
    client.release();
  }
};

export const getRolesWithPermissions = async () => {
  const result = await pool.query(`
    SELECT r.id_role, r.name AS role_name, r.description AS role_description,
           json_agg(
             json_build_object('id_permission', p.id_permission, 'name', p.name, 'description', p.description)
           ) AS permissions
    FROM roles r
    LEFT JOIN role_permissions rp ON r.id_role = rp.id_role
    LEFT JOIN permissions p ON rp.permission_id = p.id_permission
    GROUP BY r.id_role, r.name, r.description
    ORDER BY r.id_role ASC;
  `);
  return result.rows;
};
