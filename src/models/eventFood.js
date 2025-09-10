import pool from '../config/bd.js';

// Obtener todos los alimentos de un evento
export const getFoodByEvent = async (id_event) => {
  const result = await pool.query(`
    SELECT ef.id_event, f.id_food, f.name, f.quantity_available, f.price, f.description
    FROM event_food ef
    JOIN food f ON ef.id_food = f.id_food
    WHERE ef.id_event = $1
  `, [id_event]);
  return result.rows;
};

// Asignar comida a un evento
export const assignFoodToEvent = async (id_event, id_food) => {
  const result = await pool.query(`
    INSERT INTO event_food (id_event, id_food)
    VALUES ($1, $2) RETURNING *
  `, [id_event, id_food]);
  return result.rows[0];
};

// Actualizar cantidad y tipo de comida en un evento
// export const updateFoodInEvent = async (id_event, id_food, new_id_food) => {
//     const result = await pool.query(`
//       UPDATE event_food 
//       SET id_food = $1
//       WHERE id_event = $2 AND id_food = $3 RETURNING *
//     `, [new_id_food, id_event, id_food]);
  
//     return result.rows[0];
// };  

// Eliminar un alimento de un evento
export const removeFoodFromEvent = async (id_event, id_food) => {
  const result = await pool.query(`
    DELETE FROM event_food 
    WHERE id_event = $1 AND id_food = $2 RETURNING *
  `, [id_event, id_food]);
  return result.rows[0];
};
