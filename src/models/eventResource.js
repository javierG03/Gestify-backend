import pool from '../config/bd.js';

// Obtener los recursos asignados a un evento
export const getResourcesByEvent = async (id_event) => {
  const result = await pool.query(`
    SELECT er.id_event, r.id_resource, r.name, r.quantity_available, r.price, r.description

    FROM event_resources er
    JOIN resources r ON er.id_resource = r.id_resource
    WHERE er.id_event = $1
  `, [id_event]);
  return result.rows;
};

// Asignar un recurso a un evento
export const assignResourceToEvent = async (id_event, id_resource) => {
  const result = await pool.query(`
    INSERT INTO event_resources (id_event, id_resource)
    VALUES ($1, $2) RETURNING *
  `, [id_event, id_resource]);
  return result.rows[0];
};

// Actualizar el recurso de un evento (cambiar `id_resource`)
// export const updateResourceInEvent = async (id_event, id_resource, new_id_resource) => {
//   const result = await pool.query(`
//     UPDATE event_resources 
//     SET id_resource = $1
//     WHERE id_event = $2 AND id_resource = $3 RETURNING *
//   `, [new_id_resource, id_event, id_resource]);
//   return result.rows[0];
// };

// Eliminar un recurso de un evento
export const removeResourceFromEvent = async (id_event, id_resource) => {
  const result = await pool.query(`
    DELETE FROM event_resources 
    WHERE id_event = $1 AND id_resource = $2 RETURNING *
  `, [id_event, id_resource]);
  return result.rows[0];
};
