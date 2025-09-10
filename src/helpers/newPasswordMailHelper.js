export const mailOptions = (email, resetURL) => ({
    from: process.env.EMAIL_USER,
    to: email,
    subject: '🔒 Recuperación de Contraseña',
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; background: #fff; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); padding: 20px; text-align: center; border: 1px solid #ddd;">
        <div style="background: #007bff; color: white; padding: 15px; border-radius: 10px 10px 0 0;">
            <h2 style="margin: 0;">🔒 Recuperación de Contraseña</h2>
        </div>
        <div style="padding: 20px;">
            <p style="font-size: 18px; color: #333;"><b>Hola ${email},</b></p>
            <p style="color: #555;">Has solicitado restablecer tu contraseña. Para continuar, haz clic en el siguiente botón:</p>
            <a href="${resetURL}" style="display: inline-block; background-color: #28a745; color: white; padding: 12px 20px; text-decoration: none; border-radius: 5px; font-size: 16px; margin-top: 10px;">
            🔗 Restablecer Contraseña
            </a>
            <p style="margin-top: 20px; color: #555;">Si no solicitaste este cambio, puedes ignorar este mensaje.</p>
            <hr style="border: 0; height: 1px; background: #ddd; margin: 20px 0;">
            <h3 style="color: #007bff;">Detalles de la solicitud</h3>
            <table style="width: 100%; border-collapse: collapse; text-align: left; margin-top: 10px;">
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Email:</b></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${email}</td>
            </tr>
            <tr>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Fecha de solicitud:</b></td>
                <td style="padding: 8px; border-bottom: 1px solid #ddd;">${new Date().toLocaleString()}</td>
            </tr>
            </table>
            <hr style="border: 0; height: 1px; background: #ddd;">
            <p style="color: #777;">Este enlace expirará en 15 minutos.</p>
        </div>
        <div style="background: #f5f5f5; padding: 10px; border-radius: 0 0 10px 10px;">
            <p style="margin: 0; font-size: 14px; color: #555;">📩 EventosIA | Todos los derechos reservados.</p>
        </div>
        </div>
    `,
  });
  