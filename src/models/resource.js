import pool from '../config/bd.js';

// Obtener todos los recursos
export const getAllResources = async () => {
  const result = await pool.query(`SELECT * FROM resources`);
  return result.rows;
};

// Obtener un recurso por ID
export const getResourceById = async (id_resource) => {
  const result = await pool.query(`SELECT * FROM resources WHERE id_resource = $1`, [id_resource]);
  return result.rows[0];
};

// Crear un nuevo recurso
export const createResource = async (name, description, quantity_available, price) => {
  const result = await pool.query(`
    INSERT INTO resources (name, description, quantity_available, price)
    VALUES ($1, $2, $3, $4) RETURNING *
  `, [name, description, quantity_available, price]);
  return result.rows[0];
};

// Actualizar un recurso
export const updateResource = async (id_resource, name, description, quantity_available, price) => {
  const result = await pool.query(`
    UPDATE resources 
    SET name = $1, description = $2, quantity_available = $3, price = $4
    WHERE id_resource = $5 RETURNING *
  `, [name, description, quantity_available, price, id_resource]);
  return result.rows[0];
};

// Eliminar un recurso
export const deleteResource = async (id_resource) => {
  const result = await pool.query(`DELETE FROM resources WHERE id_resource = $1 RETURNING *`, [id_resource]);
  return result.rows[0];
};
