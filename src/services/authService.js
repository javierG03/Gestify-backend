import jwt from 'jsonwebtoken';
import bcrypt from 'bcryptjs';
import * as UserModel from '../models/user.js';

// Constantes para configuración de cookies
const COOKIE_OPTIONS = {
    httpOnly: true,         // No accesible desde JavaScript (previene XSS)
    secure: process.env.NODE_ENV === 'production', // Solo HTTPS en producción
    sameSite: 'strict',     // Previene CSRF
    maxAge: 24 * 60 * 60 * 1000 // 1 día en milisegundos (coincide con expiresIn del token)
  };
  
  const TOKEN_COOKIE_NAME = 'auth_token';

/**
 * Genera un token JWT para verificación de email
 * @param {string} email - Email del usuario
 * @returns {string} Token JWT
 */
export const generateEmailVerificationToken = (email) => {
  return jwt.sign({ email }, process.env.JWT_SECRET, { expiresIn: '1d' });
};

/**
 * Genera un token JWT para sesión de usuario
 * @param {Object} user - Datos del usuario
 * @returns {string} Token JWT
 */
export const generateAuthToken = (user) => {
  return jwt.sign(
    {
      id_user: user.id_user,
      email: user.email,
      id_role: user.id_role,
      name: user.name,           // <-- Agrega esto
      last_name: user.last_name, // <-- Y esto
    },
    process.env.JWT_SECRET,
    { expiresIn: '1d' }
  );
};
/**
 * Verifica un token JWT
 * @param {string} token - Token JWT a verificar
 * @returns {Object} Datos decodificados del token
 */
export const verifyToken = (token) => {
  return jwt.verify(token, process.env.JWT_SECRET);
};

/**
 * Establece el token de autenticación como cookie
 * @param {Object} res - Objeto de respuesta Express
 * @param {string} token - Token JWT
 */
export const setAuthCookie = (res, token) => {
    res.cookie(TOKEN_COOKIE_NAME, token, COOKIE_OPTIONS);
};

/**
 * Elimina la cookie de autenticación
 * @param {Object} res - Objeto de respuesta Express
 */
export const clearAuthCookie = (res) => {
    res.clearCookie(TOKEN_COOKIE_NAME);
};

/**
 * Encripta una contraseña
 * @param {string} password - Contraseña en texto plano
 * @returns {Promise<string>} Contraseña encriptada
 */
export const hashPassword = async (password) => {
  return await bcrypt.hash(password, 10);
};

/**
 * Verifica si una contraseña coincide con su versión encriptada
 * @param {string} password - Contraseña en texto plano
 * @param {string} hashedPassword - Contraseña encriptada
 * @returns {Promise<boolean>} true si coinciden, false si no
 */
export const comparePassword = async (password, hashedPassword) => {
  return await bcrypt.compare(password, hashedPassword);
};

/**
 * Autentica a un usuario con email y contraseña
 * @param {string} email - Email del usuario
 * @param {string} password - Contraseña en texto plano
 * @returns {Promise<Object>} Datos del usuario y token si la autenticación es exitosa
 */
export const authenticateUser = async (email, password) => {
  // Obtener el usuario con su contraseña
  const user = await UserModel.getUserWithPassword(email)
  if (!user) throw new Error("Credenciales incorrectas")

  // Verificar que el email esté confirmado
  if (!user.email_verified) throw new Error(`El email no esta confirmado, debes confirmarlo para poder iniciar sesión`)

  // Verificar la contraseña
  console.log("Intentando verificar contraseña para:", email)
  console.log("Contraseña proporcionada (hash):", await hashPassword(password))
  console.log("Contraseña almacenada:", user.password)

  const isMatch = await comparePassword(password, user.password)
  console.log("¿Contraseña coincide?:", isMatch)

  if (!isMatch) throw new Error("Credenciales incorrectas")

  const token = generateAuthToken(user)

  return {
    token,
    usuario: {
      id_user: user.id_user,
      email: user.email,
      name: user.name,
      last_name: user.last_name,
      role: user.role_name,
    },
  }
}
  

/**
 * Verifica el email de un usuario mediante un token
 * @param {string} token - Token JWT de verificación
 * @returns {Promise<string>} Email verificado
 */
export const verifyUserEmail = async (token) => {
  try {
    const decoded = verifyToken(token);
    const email = decoded.email;
    
    await UserModel.verifyEmail(email);
    
    return email;
  } catch (error) {
    throw new Error('Token inválido o expirado');
  }
};

/**
 * Cierra la sesión del usuario eliminando la cookie
 * @param {Object} res - Objeto de respuesta Express
 */
export const logoutUser = (res) => {
    clearAuthCookie(res);
  };