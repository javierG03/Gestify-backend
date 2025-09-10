import pool from '../config/bd.js';

// Obtener todas las ubicaciones
export const getAllLocations = async () => {
  const result = await pool.query(`SELECT * FROM location`);
  return result.rows;
};

// Obtener una ubicación por ID
export const getLocationById = async (id_location) => {
  const result = await pool.query(`SELECT * FROM location WHERE id_location = $1`, [id_location]);
  return result.rows[0];
};

// Crear una nueva ubicación
export const createLocation = async (name, description, price, address) => {
  const result = await pool.query(`
    INSERT INTO location (name, description, price, address)
    VALUES ($1, $2, $3, $4) RETURNING *
  `, [name, description, price, address]);
  return result.rows[0];
};

// Actualizar una ubicación
export const updateLocation = async (id_location, name, description, price, address) => {
  const result = await pool.query(`
    UPDATE location 
    SET name = $1, description = $2, price = $3, address = $4
    WHERE id_location = $5 RETURNING *
  `, [name, description, price, address, id_location]);
  return result.rows[0];
};

// Eliminar una ubicación
export const deleteLocation = async (id_location) => {
  const result = await pool.query(`DELETE FROM location WHERE id_location = $1 RETURNING *`, [id_location]);
  return result.rows[0];
};
