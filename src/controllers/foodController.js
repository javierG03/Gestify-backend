import * as FoodModel from '../models/food.js';

// Obtener todos los alimentos
export const getFood = async (req, res) => {
  try {
    const food = await FoodModel.getAllFood();
    res.status(200).json(food);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los alimentos' });
  }
};

// Obtener un alimento por ID
export const getFoodById = async (req, res) => {
  try {
    const { id } = req.params;
    const food = await FoodModel.getFoodById(id);

    if (!food) {
      return res.status(404).json({ error: 'Alimento no encontrado' });
    }

    res.status(200).json(food);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener el alimento' });
  }
};


// Crear un alimento
export const createFood = async (req, res) => {
  try {
    const { name, description, quantity_available, price } = req.body;
    const newFood = await FoodModel.createFood(name, description, quantity_available, price);
    res.status(201).json(newFood);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al crear el alimento' });
  }
};

// Actualizar un alimento
export const updateFood = async (req, res) => {
    try {
      const { id } = req.params;
      const { name, description, quantity_available, price } = req.body;
  
      const updatedFood = await FoodModel.updateFood(id, name, description, quantity_available, price);
      
      if (!updatedFood) {
        return res.status(404).json({ error: 'Alimento no encontrado' });
      }
  
      res.status(200).json(updatedFood);
    } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error al actualizar el alimento' });
    }
};  
  
// Eliminar un alimento
export const deleteFood = async (req, res) => {
    try {
      const { id } = req.params;
      const deletedFood = await FoodModel.deleteFood(id);
      
      if (!deletedFood) {
        return res.status(404).json({ error: 'Alimento no encontrado' });
      }
  
      res.status(200).json({ mensaje: 'Alimento eliminado correctamente' });
    } catch (error) {
      console.error(error);
      res.status(500).json({ error: 'Error al eliminar el alimento' });
    }
};  
