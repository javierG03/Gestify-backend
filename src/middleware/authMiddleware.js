import * as authService from '../services/authService.js';

/**
 * Middleware para verificar la autenticación basada en cookie
 * @param {Object} req - Objeto de solicitud Express
 * @param {Object} res - Objeto de respuesta Express
 * @param {Function} next - Función next de Express
 */
export const verifyAuth = (req, res, next) => {
  try {
    // Obtener el token del header Authorization
    const authHeader = req.headers.authorization;

    if (!authHeader || !authHeader.startsWith('Bearer ')) {
      return res.status(401).json({ error: 'No autorizado: Token no proporcionado' });
    }

    const token = authHeader.split(' ')[1];

    // Verificar el token usando tu servicio
    const decoded = authService.verifyToken(token);

    // Guardar los datos del usuario decodificados en el request
    req.user = decoded;

    next();
  } catch (error) {
    return res.status(401).json({ error: 'No autorizado: Token inválido o expirado' });
  }
};

/**
 * Middleware para verificar roles específicos
 * @param {Array} roles - Array de IDs de roles permitidos
 * @returns {Function} Middleware de Express
 */
export const verifyRole = (roles) => {
  return (req, res, next) => {
    // Este middleware debe usarse después de verifyAuth
    if (!req.user) {
      return res.status(401).json({ error: 'No autorizado' });
    }
    
    if (!roles.includes(req.user.id_role)) {
      return res.status(403).json({ error: 'Acceso denegado: No tienes los permisos necesarios' });
    }
    
    next();
  };
};