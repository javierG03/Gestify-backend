import * as EventResourceModel from '../models/eventResource.js';

// Obtener los recursos asignados a un evento
export const getResourcesByEvent = async (req, res) => {
  try {
    const { id_event } = req.params;
    const resources = await EventResourceModel.getResourcesByEvent(id_event);
    res.status(200).json(resources);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los recursos del evento' });
  }
};

// Asignar un recurso a un evento
export const handleAssignResourceToEvent = async (req, res) => {
  try {
    const { id_event, id_resource } = req.body;

    if (!id_event || !id_resource) {
      return res.status(400).json({ error: 'Se requieren id_event e id_resource' });
    }

    const assignedResource = await EventResourceModel.assignResourceToEvent(id_event, id_resource);
    res.status(201).json(assignedResource);
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al asignar el recurso al evento' });
  }
};


// Actualizar el recurso de un evento (cambiar `id_resource`)
// export const updateResourceInEvent = async (req, res) => {
//   try {
//     const { id_event, id_resource } = req.params;
//     const { new_id_resource } = req.body;

//     const updatedResource = await EventResourceModel.updateResourceInEvent(id_event, id_resource, new_id_resource);

//     if (!updatedResource) {
//       return res.status(404).json({ error: 'Recurso en evento no encontrado o no se pudo actualizar' });
//     }

//     res.status(200).json(updatedResource);
//   } catch (error) {
//     console.error(error);
//     res.status(500).json({ error: 'Error al actualizar el recurso en el evento' });
//   }
// };

// Eliminar un recurso de un evento
export const removeResourceFromEvent = async (req, res) => {
  try {
    const { id_event, id_resource } = req.params;
    const deletedResource = await EventResourceModel.removeResourceFromEvent(id_event, id_resource);

    if (!deletedResource) {
      return res.status(404).json({ error: 'Recurso en evento no encontrado' });
    }

    res.status(200).json({ mensaje: 'Recurso eliminado del evento correctamente' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al eliminar el recurso del evento' });
  }
};
