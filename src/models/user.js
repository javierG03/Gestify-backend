import pool from '../config/bd.js';

// Obtener todos los usuarios con su rol
export const getUsers = async () => {
  const result = await pool.query(`
    SELECT u.id_user, u.name, u.last_name, u.email, u.email_verified, u.created_at,
           r.id_role, r.name AS role_name
    FROM users u
    LEFT JOIN user_role ur ON u.id_user = ur.user_id
    LEFT JOIN roles r ON ur.role_id = r.id_role
    ORDER BY u.id_user ASC
  `);
  return result.rows;
};

// Crear un nuevo usuario y asignarle un rol
export const createUser = async (userData) => {
  const {
    name,
    last_name,
    email,
    email_verified = false,
    password,
    id_role, // El rol ahora se inserta en user_role
  } = userData;

  // Validar si falta el campo id_role
  if (!id_role) {
    throw new Error("Falta asignar rol");
  }

  // Insertar en la tabla `users`
  const userResult = await pool.query(
    `INSERT INTO users (name, last_name, email, email_verified, password, created_at)
     VALUES ($1, $2, $3, $4, $5, NOW())
     RETURNING id_user`,
    [name, last_name, email, email_verified, password]
  );

  const id_user = userResult.rows[0].id_user;

  // Insertar la relación en `user_role`
  await pool.query(
    `INSERT INTO user_role (user_id, role_id) VALUES ($1, $2)`,
    [id_user, id_role]
  );

  return { id_user, name, last_name, email, email_verified, id_role };
};

// Obtener usuario por email
export const getUserByEmail = async (email) => {
  const result = await pool.query(
    `SELECT u.id_user, u.name, u.last_name, u.email, u.email_verified, u.created_at,
            r.id_role, r.name AS role_name
     FROM users u
     LEFT JOIN user_role ur ON u.id_user = ur.user_id
     LEFT JOIN roles r ON ur.role_id = r.id_role
     WHERE u.email = $1`,
    [email]
  );
  return result.rows[0];
};

// // Verificar email
// export const verifyEmail = async (email) => {
//   const result = await pool.query(
//     'UPDATE users SET email_verified = true WHERE email = $1 RETURNING *',
//     [email]
//   );
//   return result.rows[0];
// };
export const verifyEmail = async (email) => {
  const result = await pool.query(
    'UPDATE users SET email_verified = true WHERE email = $1 RETURNING *',
    [email]
  );
  
  console.log('Resultado de la actualización:', result.rows); //  Ver qué retorna

  return result.rows[0];
};


// Obtener usuario por email con contraseña (para login)
export const getUserWithPassword = async (email) => {
  try {
    const result = await pool.query(
      `SELECT u.id_user, u.name, u.last_name, u.email, u.password, u.email_verified, 
              r.id_role, r.name AS role_name
       FROM users u
       LEFT JOIN user_role ur ON u.id_user = ur.user_id
       LEFT JOIN roles r ON ur.role_id = r.id_role
       WHERE u.email = $1`,
      [email],
    )

    if (result.rows.length === 0) {
      console.log("No se encontró usuario con email:", email)
      return null
    }

    console.log("Usuario encontrado:", result.rows[0].email)
    console.log("Contraseña almacenada:", result.rows[0].password)

    return result.rows[0]
  } catch (error) {
    console.error("Error al obtener usuario con contraseña:", error)
    throw error
  }
}


// Actualizar datos del usuario (excepto rol)
export const updateUser = async (email, userData) => {
  const validFields = Object.entries(userData).filter(([_, value]) => value !== undefined && value !== null);

  if (validFields.length === 0) {
    throw new Error('No se enviaron datos válidos para actualizar');
  }

  const fields = validFields.map(([key], index) => `${key} = $${index + 1}`).join(', ');
  const values = validFields.map(([_, value]) => value);

  const result = await pool.query(
    `UPDATE users SET ${fields} WHERE email = $${values.length + 1} RETURNING *`,
    [...values, email]
  );

  return result.rows[0];
};

// Actualizar rol de un usuario en `user_role`
export const updateUserRole = async (id_user, newRoleId) => {
  const result = await pool.query(
    `UPDATE user_role SET role_id = $1 WHERE user_id = $2 RETURNING *`,
    [newRoleId, id_user]
  );
  return result.rows[0];
};

// Eliminar usuario y su relación en `user_role`
export const deleteUserByEmail = async (email) => {
  // Obtener ID del usuario antes de eliminar
  const user = await getUserByEmail(email);
  if (!user) return null;

  const { id_user } = user;

  // Eliminar relación en `user_role`
  await pool.query('DELETE FROM user_role WHERE user_id = $1', [id_user]);

  // Eliminar usuario
  const result = await pool.query('DELETE FROM users WHERE email = $1 RETURNING *', [email]);

  return result.rows[0]; // Retorna el usuario eliminado
};


// Obtener usuario por ID con información de rol
export const getUserById = async (id_user) => {
  const result = await pool.query(
    `SELECT u.id_user, u.name, u.last_name, u.email, u.email_verified, u.created_at,
            r.id_role, r.name AS role_name
     FROM users u
     LEFT JOIN user_role ur ON u.id_user = ur.user_id
     LEFT JOIN roles r ON ur.role_id = r.id_role
     WHERE u.id_user = $1`,
    [id_user]
  );
  return result.rows[0];
};