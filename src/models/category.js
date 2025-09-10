import pool from '../config/bd.js';

// Obtener todas las categorías
export const getAllCategories = async () => {
  const result = await pool.query(`SELECT * FROM categories`);
  return result.rows;
};

// Obtener una categoría por ID
export const getCategoryById = async (id_category) => {
  const result = await pool.query(`SELECT * FROM categories WHERE id_category = $1`, [id_category]);
  return result.rows[0];
};

// Crear una nueva categoría
export const createCategory = async (name, description) => {
  const result = await pool.query(`
    INSERT INTO categories (name, description)
    VALUES ($1, $2) RETURNING *
  `, [name, description]);
  return result.rows[0];
};

// Actualizar una categoría
export const updateCategory = async (id_category, name, description) => {
  const result = await pool.query(`
    UPDATE categories 
    SET name = $1, description = $2
    WHERE id_category = $3 RETURNING *
  `, [name, description, id_category]);
  return result.rows[0];
};

// Eliminar una categoría
export const deleteCategory = async (id_category) => {
  const result = await pool.query(`DELETE FROM categories WHERE id_category = $1 RETURNING *`, [id_category]);
  return result.rows[0];
};
