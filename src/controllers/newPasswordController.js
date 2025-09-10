import crypto from 'crypto';
import bcrypt from 'bcryptjs';
import * as PasswordModel from '../models/newPassword.js';
import * as UserModel from '../models/user.js';
import transporter from '../config/emailConfig.js';
import { mailOptions } from '../helpers/newPasswordMailHelper.js';  // Asegúrate de importar correctamente el helper

// Mapa temporal en memoria para almacenar los tokens de recuperación
const passwordResetTokens = new Map();
const baseUrl = process.env.URL_FRONT_WEB_DEV;

export const requestPasswordReset = async (req, res) => {
  try {
    const { email } = req.body;
    const user = await UserModel.getUserByEmail(email);

    if (!user) {
      return res.status(404).json({ error: 'No se encontró un usuario con ese email.' });
    }

    // Verificar que el email esté verificado
    if (!user.email_verified) {
      return res.status(403).json({ error: 'Debes verificar tu email primero.' });
    }

    // Generar un token temporal con expiración de 1 hora
    const resetToken = crypto.randomBytes(32).toString('hex');
    const expiresAt = Date.now() + 3600000; // Expira en 1 hora

    // Guardar el token en memoria
    passwordResetTokens.set(resetToken, { email, expiresAt });

    // Generar el enlace de recuperación (corregido con backticks)
    // Nota: Cambiamos la URL para que apunte al frontend, no al backend
    const resetURL = `${baseUrl}/reset-password-form/${resetToken}`

    // Utilizamos mailOptions para generar el contenido del correo
    const options = mailOptions(email, resetURL);  // Aquí estamos llamando al helper para obtener las opciones del correo

    // Enviar el correo
    await transporter.sendMail(options);

    res.status(200).json({ mensaje: 'Correo de recuperación enviado.' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al solicitar recuperación de contraseña.' });
  }
}

// Método para verificar si un token es válido (GET)
export const verifyResetToken = async (req, res) => {
  try {
    const { token } = req.params

    // Validar si el token existe y no ha expirado
    const tokenData = passwordResetTokens.get(token)
    if (!tokenData) {
      return res.status(400).json({ error: "Token inválido o expirado." })
    }

    // Verificar si el token ya expiró
    if (Date.now() > tokenData.expiresAt) {
      passwordResetTokens.delete(token) // Eliminar token expirado
      return res.status(400).json({ error: "El token ha expirado." })
    }

    res.status(200).json({ mensaje: "Token válido", email: tokenData.email })
  } catch (error) {
    console.error(error)
    res.status(500).json({ error: "Error al verificar el token." })
  }
}

// Método para actualizar la contraseña (POST)
export const resetPassword = async (req, res) => {
  try {
    const { token } = req.params;  // Token recibido desde la URL
    const { newPassword } = req.body; // Nueva contraseña del usuario

    // Validar si el token existe y no ha expirado
    const tokenData = passwordResetTokens.get(token);
    if (!tokenData) {
      return res.status(400).json({ error: 'Token inválido o expirado.' });
    }

    // Verificar si el token ya expiró
    if (Date.now() > tokenData.expiresAt) {
      passwordResetTokens.delete(token); // Eliminar token expirado
      return res.status(400).json({ error: 'El token ha expirado.' });
    }

    const { email } = tokenData;

    // Hashear la nueva contraseña
    const hashedPassword = await bcrypt.hash(newPassword, 10);

    console.log("Actualizando contraseña para:", email)
    console.log("Nueva contraseña (hash):", hashedPassword)

    // Actualizar la contraseña en la base de datos
    await PasswordModel.updatePassword(email, hashedPassword);

    // Eliminar el token después de su uso
    passwordResetTokens.delete(token);

    res.status(200).json({ mensaje: 'Contraseña actualizada correctamente.' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al restablecer la contraseña.' });
  }
};
