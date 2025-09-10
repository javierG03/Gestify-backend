import pool from '../config/bd.js';

// Obtener todos los alimentos
export const getAllFood = async () => {
  const result = await pool.query(`SELECT * FROM food`);
  return result.rows;
};

// Obtener un alimento por ID
export const getFoodById = async (id_food) => {
  const result = await pool.query(`SELECT * FROM food WHERE id_food = $1`, [id_food]);
  return result.rows[0];
};

// Crear un nuevo alimento
export const createFood = async (name, description, quantity_available, price) => {
  const result = await pool.query(`
    INSERT INTO food (name, description, quantity_available, price)
    VALUES ($1, $2, $3, $4) RETURNING *
  `, [name, description, quantity_available, price]);
  return result.rows[0];
};

// Actualizar un alimento
export const updateFood = async (id_food, name, description, quantity_available, price) => {
  const result = await pool.query(`
    UPDATE food 
    SET name = $1, description = $2, quantity_available = $3, price = $4
    WHERE id_food = $5 RETURNING *
  `, [name, description, quantity_available, price, id_food]);
  return result.rows[0];
};

// Eliminar un alimento
export const deleteFood = async (id_food) => {
  const result = await pool.query(`DELETE FROM food WHERE id_food = $1 RETURNING *`, [id_food]);
  return result.rows[0];
};
