import * as LocationModel from '../models/location.js';

// Obtener todas las ubicaciones
export const getLocations = async (req, res) => {
  try {
    const locations = await LocationModel.getAllLocations();
    res.status(200).json(locations);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener las ubicaciones' });
  }
};

// Obtener una ubicación por ID
export const getLocation = async (req, res) => {
  try {
    const { id } = req.params;
    const location = await LocationModel.getLocationById(id);
    if (!location) {
      return res.status(404).json({ error: 'Ubicación no encontrada' });
    }
    res.status(200).json(location);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener la ubicación' });
  }
};

// Crear una nueva ubicación
export const createLocation = async (req, res) => {
  try {
    const { name, description, price, address } = req.body;
    const newLocation = await LocationModel.createLocation(name, description, price, address);
    res.status(201).json(newLocation);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al crear la ubicación' });
  }
};

// Actualizar una ubicación
export const updateLocation = async (req, res) => {
  try {
    const { id } = req.params;
    const { name, description, price, address } = req.body;
    
    const updatedLocation = await LocationModel.updateLocation(id, name, description, price, address);
    
    if (!updatedLocation) {
      return res.status(404).json({ error: 'Ubicación no encontrada' });
    }

    res.status(200).json(updatedLocation);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al actualizar la ubicación' });
  }
};

// Eliminar una ubicación
export const deleteLocation = async (req, res) => {
  try {
    const { id } = req.params;
    const deletedLocation = await LocationModel.deleteLocation(id);
    if (!deletedLocation) {
      return res.status(404).json({ error: 'Ubicación no encontrada' });
    }
    res.status(200).json({ mensaje: 'Ubicación eliminada correctamente' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al eliminar la ubicación' });
  }
};
