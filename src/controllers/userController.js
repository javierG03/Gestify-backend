import jwt from 'jsonwebtoken';
import * as UserModel from '../models/user.js';
import transporter from '../config/emailConfig.js';
import { mailOptions } from '../helpers/deleteMailHelper.js';
import { verificationMailOptions } from '../helpers/verificationEmailMailHelper.js';
import { credentialsMailOptions } from '../helpers/credentialsMailHelper.js';
import * as authService from '../services/authService.js';

// Obtener usuarios con sus roles
export const getUsers = async (req, res) => {
  try {
    const users = await UserModel.getUsers();
    res.status(200).json({ users });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener los usuarios' });
  }
};

// Crear usuario y asignar rol en `user_role`
export const createUser = async (req, res) => {
  try {
    const { email, password, id_role, ...restData } = req.body;

    // Validar si el usuario ya existe
    const existingUser = await UserModel.getUserByEmail(email);
    if (existingUser) {
      return res.status(400).json({ error: 'El email ya está registrado.' });
    }

    // Generar token JWT con el email del usuario
    const token = jwt.sign({ email }, process.env.JWT_SECRET, { expiresIn: '1d' });

    // Construir el enlace de verificación con el token
    const verificationURL = `${process.env.URL_FRONT_WEB_DEV}/verify-email/${token}`;

    // Configurar correo de verificación
    const options = verificationMailOptions(email, verificationURL);

    // Enviar email de verificación
    await transporter.sendMail(options);

    // Encriptar contraseña
    const hashedPassword = await authService.hashPassword(password);

    // Crear usuario y asignarle rol en `user_role`
    const newUser = await UserModel.createUser({
      email,
      password: hashedPassword,
      id_role,
      ...restData,
    });

    res.status(201).json({
      mensaje: 'Usuario creado exitosamente. Se envió un correo de verificación.',
      usuario: newUser,
    });

  } catch (error) {
    console.error('Error en la función createUser:', error);
    res.status(500).json({ error: 'Error al crear usuario.' });
  }
};

// Verificar email del usuario mediante token JWT
export const verifyEmail = async (req, res) => {
  const { token } = req.params;

  try {
    await authService.verifyUserEmail(token);
    res.status(200).json({ mensaje: 'Email verificado exitosamente.' });
  } catch (error) {
    res.status(400).json({ error: 'Token inválido o expirado.' });
  }
};

// Inicio de sesión con `user_role` y establecimiento de cookie
export const loginUser = async (req, res) => {
  try {
    const { email, password } = req.body;

    // El tercer parámetro (res) permite establecer la cookie
    const authResult = await authService.authenticateUser(email, password);
    authService.setAuthCookie(res, authResult.token);
    
    res.status(200).json({
      mensaje: 'Inicio de sesión exitoso.',
      token: authResult.token,
      usuario: authResult.usuario,
      last_name: authResult.last_name
    });

  } catch (error) {
    // console.error(error);
    if (error.message === 'Credenciales incorrectas' || error.message === 'El email no esta confirmado, debes confirmarlo para poder iniciar sesión') {
      return res.status(400).json({ error: error.message });
    }
    res.status(500).json({ error: 'Error al iniciar sesión.' });
  }
};

// Cerrar sesión
export const logoutUser = (req, res) => {
  try {
    authService.logoutUser(res);
    res.status(200).json({ mensaje: 'Sesión cerrada exitosamente.' });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al cerrar sesión.' });
  }
};

// Obtener usuario por email
export const getUserByEmail = async (req, res) => {
  const { email } = req.params;

  try {
    const usuario = await UserModel.getUserByEmail(email);

    if (!usuario) {
      return res.status(404).json({ error: 'Usuario no encontrado.' });
    }

    res.status(200).json({ usuario });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al obtener el usuario.' });
  }
};

// Actualizar rol de usuario en `user_role`
export const updateUserRole = async (req, res) => {
  const { id } = req.params;
  const { newRoleId } = req.body;
  const { id_role } = req.user; // Se asume que este dato viene del token JWT

  try {
    // Solo los SuperAdmin (id_role = 1) pueden cambiar roles
    if (id_role !== 1) {
      return res.status(403).json({ error: 'No tienes permisos para cambiar roles.' });
    }

    const usuarioActualizado = await UserModel.updateUserRole(id, newRoleId);

    if (!usuarioActualizado) {
      return res.status(404).json({ error: 'Usuario no encontrado.' });
    }

    res.status(200).json({
      mensaje: 'Rol actualizado exitosamente',
      usuario: usuarioActualizado,
    });
  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error al actualizar el rol del usuario.' });
  }
};

// Eliminar usuario y su relación en `user_role`
export const deleteUser = async (req, res) => {
  try {
    const { email } = req.body; 

    if (!email) {
      return res.status(400).json({ error: 'El email es requerido para eliminar el usuario.' });
    }

    // Verificar si el usuario existe
    const user = await UserModel.getUserByEmail(email);
    if (!user) {
      return res.status(404).json({ error: 'No se encontró un usuario con ese email.' });
    }

    // Eliminar el usuario y su rol en `user_role`
    const deletedUser = await UserModel.deleteUserByEmail(email);
    if (!deletedUser) {
      return res.status(500).json({ error: 'Error al eliminar el usuario.' });
    }

    await transporter.sendMail(mailOptions(deletedUser));

    res.status(200).json({ mensaje: 'Usuario eliminado y correo de confirmación enviado.' });

  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error en la eliminación del usuario.' });
  }
};

// editar Usuarios 
export const editUser = async (req, res) => {
  try {
    const { email, name, last_name } = req.body;

    // Verificar si el usuario existe
    const user = await UserModel.getUserByEmail(email);
    if (!user) {
      return res.status(404).json({ error: 'No se encontró un usuario con ese email.' });
    }

    // Verificar que el usuario tenga el email verificado
    if (!user.email_verified) {
      return res.status(403).json({ error: 'Debes verificar tu email primero.' });
    }

    // Actualizar usuario
    const updatedUser = await UserModel.updateUser(email, { name, last_name });

    res.status(200).json({
      mensaje: 'Usuario actualizado exitosamente.',
      usuario: updatedUser
    });

  } catch (error) {
    console.error(error);
    res.status(500).json({ error: 'Error en la actualización del usuario.' });
  }
};



// Enviar credenciales de acceso por correo
export const sendCredentials = async (req, res) => {
  try {
    const { email, password } = req.body;

    if (!email || !password) {
      return res.status(400).json({ error: 'Email y contraseña son requeridos.' });
    }

    // Verificar si el usuario existe
    const user = await UserModel.getUserByEmail(email);
    if (!user) {
      return res.status(404).json({ error: 'Usuario no encontrado.' });
    }

    // Enviar correo con credenciales
    const options = credentialsMailOptions(email, password);
    await transporter.sendMail(options);

    res.status(200).json({ mensaje: 'Correo con credenciales enviado exitosamente.' });

  } catch (error) {
    console.error('Error en la función sendCredentials:', error);
    res.status(500).json({ error: 'Error al enviar las credenciales.' });
  }
};

export const resendVerificationEmail = async (req, res) => {
  try {
    const { email } = req.body;

    if (!email) {
      return res.status(400).json({ error: 'El email es requerido.' });
    }

    // Verificar si el usuario existe
    const user = await UserModel.getUserByEmail(email);
    if (!user) {
      return res.status(404).json({ error: 'No se encontró un usuario con ese email.' });
    }

    // Verificar si el email ya está verificado
    if (user.email_verified) {
      return res.status(400).json({ error: 'El email ya ha sido verificado.' });
    }

    // Generar token JWT con el email del usuario
    const token = jwt.sign({ email }, process.env.JWT_SECRET, { expiresIn: '1d' });

    // Construir el enlace de verificación con el token
    const verificationURL = `${process.env.URL_FRONT_WEB_DEV}/verify-email/${token}`;

    // Configurar correo de verificación
    const options = verificationMailOptions(email, verificationURL);

    // Enviar email de verificación
    await transporter.sendMail(options);

    res.status(200).json({
      mensaje: 'Correo de verificación reenviado exitosamente.',
    });

  } catch (error) {
    console.error('Error en la función resendVerificationEmail:', error);
    res.status(500).json({ error: 'Error al reenviar el correo de verificación.' });
  }
};