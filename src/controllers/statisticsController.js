import * as StatisticsModel from '../models/statistics.js';

// Obtener estadísticas generales
export const getStatistics = async (req, res) => {
    try {
        const statistics = await StatisticsModel.getStatistics();
        res.status(200).json(statistics);
    } catch (error) {
        res.status(500).json({ error: 'Error al obtener estadísticas' });
    }
};
