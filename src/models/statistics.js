import pool from '../config/bd.js';

const cache = {
    data: null,
    lastUpdated: null
};

// Obtener estadísticas generales con datos completos
export const getStatistics = async () => {
    try {
        const CACHE_DURATION = 5 * 60 * 1000; // 5 minutos

        // Si los datos en caché son recientes, devolverlos
        if (cache.data && (Date.now() - cache.lastUpdated < CACHE_DURATION)) {
            return cache.data;
        }

        const queries = {
            users: 'SELECT * FROM users;',
            events: 'SELECT * FROM events;',
            participants: 'SELECT * FROM participants;',
            locations: 'SELECT * FROM location;',
            roles: 'SELECT * FROM roles;',
            permissions: 'SELECT * FROM permissions;',
            resources: 'SELECT * FROM resources;',
            food: 'SELECT * FROM food;',

            //Estadisticas por filtros
            // // Eventos más populares
            // popular_events: `
            //     SELECT e.id_event, e.name, COUNT(p.id_user) AS total_participantes
            //     FROM events e
            //     JOIN participants p ON e.id_event = p.id_event
            //     GROUP BY e.id_event, e.name
            //     ORDER BY total_participantes DESC
            //     LIMIT 5;
            // `,

            // // Recursos más utilizados
            // popular_resources: `
            //     SELECT r.id_resource, r.name, COUNT(er.id_event) AS veces_utilizado
            //     FROM resources r
            //     JOIN event_resources er ON r.id_resource = er.id_resource
            //     GROUP BY r.id_resource, r.name
            //     ORDER BY veces_utilizado DESC
            //     LIMIT 5;
            // `,

            // // Ubicaciones más usadas
            // popular_locations: `
            //     SELECT l.id_location, l.name, COUNT(e.id_event) AS total_eventos
            //     FROM location l
            //     JOIN events e ON l.id_location = e.location_id
            //     GROUP BY l.id_location, l.name
            //     ORDER BY total_eventos DESC
            //     LIMIT 5;
            // `
        };

        // Ejecutar todas las consultas en paralelo
        const results = await Promise.all(
            Object.entries(queries).map(async ([key, query]) => {
                const res = await pool.query(query);
                return { 
                    [`${key}_count`]: res.rows.length,  // Agrega el total de registros
                    [key]: res.rows                      // Agrega los datos completos
                };
            })
        );

        // Convertir el array de resultados en un objeto
        const statistics = Object.assign({}, ...results);

        // Almacenar en caché
        cache.data = statistics;
        cache.lastUpdated = Date.now();

        return statistics;

    } catch (error) {
        console.error('Error al obtener estadísticas:', error);
        throw error;
    }
};
