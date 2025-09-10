import * as ResourceModel from '../models/resource.js';

// Obtener todos los recursos
export const getResources = async (req, res) => {
  try {
    const resources = await ResourceModel.getAllResources();
    res.status(200).json(resources);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los recursos' });
  }
};

// Obtener un recurso por ID
export const getResource = async (req, res) => {
  try {
    const { id } = req.params;
    const resource = await ResourceModel.getResourceById(id);
    if (!resource) {
      return res.status(404).json({ error: 'Recurso no encontrado' });
    }
    res.status(200).json(resource);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener el recurso' });
  }
};

// Crear un nuevo recurso
export const createResource = async (req, res) => {
  try {
    const { name, description, quantity_available, price } = req.body;
    const newResource = await ResourceModel.createResource(name, description, quantity_available, price);
    res.status(201).json(newResource);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al crear el recurso' });
  }
};

// Actualizar un recurso
export const updateResource = async (req, res) => {
  try {
    const { id } = req.params;
    const { name, description, quantity_available, price } = req.body;

    const updatedResource = await ResourceModel.updateResource(id, name, description, quantity_available, price);
    
    if (!updatedResource) {
      return res.status(404).json({ error: 'Recurso no encontrado' });
    }

    res.status(200).json(updatedResource);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al actualizar el recurso' });
  }
};

// Eliminar un recurso
export const deleteResource = async (req, res) => {
  try {
    const { id } = req.params;
    const deletedResource = await ResourceModel.deleteResource(id);
    
    if (!deletedResource) {
      return res.status(404).json({ error: 'Recurso no encontrado' });
    }

    res.status(200).json({ mensaje: 'Recurso eliminado correctamente' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al eliminar el recurso' });
  }
};
