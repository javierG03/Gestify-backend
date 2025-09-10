export const credentialsMailOptions = (email, password) => ({
    from: process.env.EMAIL_USER,
    to: email,
    subject: '🔐 Credenciales de Acceso - EventosIA',
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; background: #fff; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); padding: 20px; text-align: center; border: 1px solid #ddd;">
        <div style="background: #2196F3; color: white; padding: 15px; border-radius: 10px 10px 0 0;">
          <h2 style="margin: 0;">🔐 Tus Credenciales de Acceso</h2>
        </div>
        <div style="padding: 20px;">
          <p style="font-size: 18px; color: #333;"><b>Bienvenido/a a EventosIA!</b></p>
          <p style="color: #555;">Se ha creado una cuenta para ti en nuestra plataforma. A continuación encontrarás tus credenciales de acceso. Te recomendamos cambiar la contraseña una vez hayas iniciado sesión por primera vez.</p>
          
          <h3 style="color: #2196F3; margin-top: 30px;">Detalles de la cuenta</h3>
          <table style="width: 100%; border-collapse: collapse; text-align: left; margin-top: 10px;">
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Email:</b></td>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;">${email}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Contraseña:</b></td>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;">${password}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Fecha de creación:</b></td>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;">${new Date().toLocaleString()}</td>
            </tr>
          </table>
  
            <p style="margin-top: 20px; font-size: 16px; color: #333;">Para iniciar sesión, visita nuestro Sitio Web  o Aplicacion Movil y utiliza las credenciales proporcionadas.</p>
        </div>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 0 0 10px 10px;">
          <p style="margin: 0; font-size: 14px; color: #555;">📅 EventosIA | Tu plataforma para gestionar eventos</p>
          <p style="margin: 5px 0 0; font-size: 12px; color: #777;">¿Necesitas ayuda? Contáctanos en <a href="mailto:eventosia854@gmail.com" style="color: #2196F3;">soporte@eventosai.com</a></p>
        </div>
      </div>
    `,
  });
  