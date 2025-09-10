// eventNotificationService.js
import db from '../config/bd.js';
import schedule from 'node-schedule';

// Función para crear notificaciones para eventos próximos
export async function createUpcomingEventNotifications() {
  try {
    // Consulta para encontrar eventos que ocurrirán en menos de 2 días
    // y que no tienen notificaciones de recordatorio enviadas
    const upcomingEvents = await db.query(`
        SELECT 
        e.id_event, 
        e.name, 
        toe.start_time, 
        p.user_id
        FROM events e
        JOIN type_of_event toe ON e.type_of_event_id = toe.id_type_of_event
        JOIN participants p ON e.id_event = p.event_id
        LEFT JOIN notifications n ON (
        e.id_event = n.event_id AND 
        p.user_id = n.user_id AND 
        n.notification_type = 'upcoming_event'
        )
        WHERE 
        toe.start_time IS NOT NULL
        AND toe.start_time >= NOW()
        AND toe.start_time < NOW() + INTERVAL '3 days'
        AND n.id_notification IS NULL 
        AND e.event_state_id NOT IN (
            SELECT id_event_state 
            FROM event_state 
            WHERE LOWER(state_name) = 'cancelled'
        );

      `);
      
    console.log(`Encontrados ${upcomingEvents.rows.length} eventos próximos que requieren notificación`);

    // Crear notificaciones para cada evento próximo
    for (const event of upcomingEvents.rows) {
      const message = `Recordatorio: El evento "${event.name}" comenzará en menos de 48 horas`;

      await db.query(`
        INSERT INTO notifications (
          user_id, 
          message, 
          event_id, 
          notification_type
        )
        VALUES ($1, $2, $3, $4)
      `, [event.user_id, message, event.id_event, 'upcoming_event']);
    }

    return upcomingEvents.rows.length;
  } catch (error) {
    console.error('Error al crear notificaciones de eventos próximos:', error);
    throw error;
  }
}

// Inicializar el programador de tareas
export function initNotificationScheduler() {
  // Ejecutar diariamente a las 8:00 AM
  schedule.scheduleJob('0 8 * * *', async () => {
    console.log('Ejecutando verificación de eventos próximos');
    try {
      const notificationsCreated = await createUpcomingEventNotifications();
      console.log(`Se han creado ${notificationsCreated} notificaciones de eventos próximos`);
    } catch (error) {
      console.error('Error en el programador de notificaciones:', error);
    }
  });

  console.log('Programador de notificaciones iniciado correctamente');
}

// Función para ejecutar la verificación manualmente (útil para pruebas)
export async function runManualCheck() {
  try {
    const notificationsCreated = await createUpcomingEventNotifications();
    return notificationsCreated;
  } catch (error) {
    console.error('Error en verificación manual:', error);
    throw error;
  }
}