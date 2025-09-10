import * as CategoryModel from '../models/category.js';

// Obtener todas las categorías
export const getCategories = async (req, res) => {
  try {
    const categories = await CategoryModel.getAllCategories();
    res.status(200).json(categories);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener las categorías' });
  }
};

// Obtener una categoría por ID
export const getCategory = async (req, res) => {
  try {
    const { id } = req.params;
    const category = await CategoryModel.getCategoryById(id);
    if (!category) {
      return res.status(404).json({ error: 'Categoría no encontrada' });
    }
    res.status(200).json(category);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener la categoría' });
  }
};

// Crear una nueva categoría
export const createCategory = async (req, res) => {
  try {
    const { name, description } = req.body;
    const newCategory = await CategoryModel.createCategory(name, description);
    res.status(201).json(newCategory);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al crear la categoría' });
  }
};

// Actualizar una categoría
export const updateCategory = async (req, res) => {
  try {
    const { id } = req.params;
    const { name, description } = req.body;

    const updatedCategory = await CategoryModel.updateCategory(id, name, description);

    if (!updatedCategory) {
      return res.status(404).json({ error: 'Categoría no encontrada' });
    }

    res.status(200).json(updatedCategory);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al actualizar la categoría' });
  }
};

// Eliminar una categoría
export const deleteCategory = async (req, res) => {
  try {
    const { id } = req.params;
    const deletedCategory = await CategoryModel.deleteCategory(id);

    if (!deletedCategory) {
      return res.status(404).json({ error: 'Categoría no encontrada' });
    }

    res.status(200).json({ mensaje: 'Categoría eliminada correctamente' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al eliminar la categoría' });
  }
};
