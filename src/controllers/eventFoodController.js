import * as EventFoodModel from '../models/eventFood.js';

// Obtener comida de un evento
export const getFoodByEvent = async (req, res) => {
  try {
    const { id_event } = req.params;
    const food = await EventFoodModel.getFoodByEvent(id_event);
    res.status(200).json(food);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los alimentos del evento' });
  }
};

// Asignar comida a un evento
export const assignFoodToEvent = async (req, res) => {
  try {
    const { id_event, id_food } = req.body;
    console.log(req.body)
    const assignedFood = await EventFoodModel.assignFoodToEvent(id_event, id_food);
    res.status(201).json(assignedFood);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al asignar comida al evento' });
  }
};

// Actualizar cantidad y tipo de comida en un evento
// export const updateFoodInEvent = async (req, res) => {
//     try {
//       const { id_event, id_food } = req.params;
//       const { new_id_food } = req.body; // Nuevo id_food y cantidad
  
//       const updatedFood = await EventFoodModel.updateFoodInEvent(id_event, id_food, new_id_food);
  
//       if (!updatedFood) {
//         return res.status(404).json({ error: 'Alimento en evento no encontrado o no se pudo actualizar' });
//       }
  
//       res.status(200).json(updatedFood);
//     } catch (error) {
//       console.error(error);
//       res.status(500).json({ error: 'Error al actualizar la comida en el evento' });
//     }
// };        
  
// Eliminar un alimento de un evento
export const removeFoodFromEvent = async (req, res) => {
    try {
      const { id_event, id_food } = req.params;
      const deletedFood = await EventFoodModel.removeFoodFromEvent(id_event, id_food);
  
      if (!deletedFood) {
        return res.status(404).json({ error: 'Alimento en evento no encontrado' });
      }
  
      res.status(200).json({ mensaje: 'Alimento eliminado del evento correctamente' });
    } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error al eliminar el alimento del evento' });
    }
  };
  
  