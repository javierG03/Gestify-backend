import cron from 'node-cron';
import { updateEventState } from '../models/event.js';  

cron.schedule('* * * * *', async () => {
    console.log('Cronjob ejecutado: ', new Date());
    try {
      const updatedEvents = await updateEventState();
      console.log(`Se han actualizado ${updatedEvents} eventos`);
    } catch (error) {
      console.error('Error al actualizar eventos:', error);
    }
  });