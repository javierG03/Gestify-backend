export const verificationMailOptions = (email, verificationURL) => ({
    from: process.env.EMAIL_USER,
    to: email,
    subject: '✅ Verificación de Cuenta - EventosIA',
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; background: #fff; border-radius: 10px; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); padding: 20px; text-align: center; border: 1px solid #ddd;">
        <div style="background: #4CAF50; color: white; padding: 15px; border-radius: 10px 10px 0 0;">
          <h2 style="margin: 0;">✅ Verifica tu Cuenta</h2>
        </div>
        <div style="padding: 20px;">
          <p style="font-size: 18px; color: #333;"><b>Bienvenido/a a EventosIA!</b></p>
          <p style="color: #555;">Gracias por registrarte en nuestra plataforma. Para activar tu cuenta y comenzar a usar todos nuestros servicios, por favor verifica tu correo electrónico haciendo clic en el siguiente botón:</p>
          
          <a href="${verificationURL}" style="display: inline-block; background-color: #4CAF50; color: white; padding: 12px 30px; text-decoration: none; border-radius: 5px; font-size: 16px; margin: 20px 0; font-weight: bold;">
            ✔️ Verificar mi Cuenta
          </a>
          
          <p style="color: #555;">Si no puedes hacer clic en el botón, copia y pega el siguiente enlace en tu navegador:</p>
          <p style="background-color: #f5f5f5; padding: 10px; border-radius: 5px; word-break: break-all;">
            <a href="${verificationURL}" style="color: #007bff; text-decoration: none;">${verificationURL}</a>
          </p>
          
          <p style="margin-top: 20px; color: #555;">Si no has solicitado esta cuenta, puedes ignorar este mensaje.</p>
          
          <hr style="border: 0; height: 1px; background: #ddd; margin: 20px 0;">
          
          <h3 style="color: #4CAF50;">Detalles de la cuenta</h3>
          <table style="width: 100%; border-collapse: collapse; text-align: left; margin-top: 10px;">
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Email:</b></td>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;">${email}</td>
            </tr>
            <tr>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;"><b>Fecha de registro:</b></td>
              <td style="padding: 8px; border-bottom: 1px solid #ddd;">${new Date().toLocaleString()}</td>
            </tr>
          </table>
          
          <p style="color: #777; margin-top: 20px;">Este enlace expirará en 24 horas.</p>
        </div>
        <div style="background: #f5f5f5; padding: 15px; border-radius: 0 0 10px 10px;">
          <p style="margin: 0; font-size: 14px; color: #555;">📅 EventosIA | Tu plataforma para gestionar eventos</p>
          <p style="margin: 5px 0 0; font-size: 12px; color: #777;">Si necesitas ayuda, contáctanos en <a href="mailto:eventosia854@gmail.com" style="color: #4CAF50;">soporte@eventosai.com</a></p>
        </div>
      </div>
    `,
  });