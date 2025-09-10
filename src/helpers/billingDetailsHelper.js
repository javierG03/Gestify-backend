import { getPriceEventById } from '../models/event.js';

// Devuelve los totales desglosados para un evento
export const getBillingDetailsForEvent = async (event_id) => {
  const event = await getPriceEventById(event_id);
  if (!event) return null;
  return {
    logistica: event.logistics_price || 0,
    alquiler_sitio: event.location_rent || 0,
    alimentacion: event.food_total || 0,
    recursos: event.resources_total || 0,
    total: event.total_value || 0
  };
};
