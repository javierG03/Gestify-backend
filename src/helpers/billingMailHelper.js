// src/helpers/billingMailHelper.js
import nodemailer from 'nodemailer';

// Función para generar las opciones del correo
export const getBillingMailOptions = (email, clientName, billingDetails, billingId) => {
  const { logistica, alquiler_sitio, alimentacion, recursos, total } = billingDetails;
  
  // Enlace para aceptar la cotización (cambiar a URL de producción en el entorno real)
  const acceptLink = `${process.env.URL_FRONT_WEB_DEV}/billing/accept/${billingId}`; // Utiliza una URL dinámica basada en el entorno
  const rejectLink = `${process.env.URL_FRONT_WEB_DEV}/billing/reject/${billingId}`; // Enlace para rechazar

  return {
    from: process.env.EMAIL_USER,
    to: email,
    subject: '📄 Cotización de tu evento',
    html: `
      <div style="max-width: 600px; margin: 0 auto; font-family: Arial, sans-serif; background: #ffffff;
                  border-radius: 10px; box-shadow: 0px 4px 10px rgba(0, 0, 0, 0.1); padding: 20px; text-align: center; border: 1px solid #ddd;">
        <div style="background: #17a2b8; color: white; padding: 15px; border-radius: 10px 10px 0 0;">
          <h2 style="margin: 0;">💰 Cotización de tu Evento</h2>
        </div>
        <div style="padding: 20px; text-align: left;">
          <p style="font-size: 18px; color: #333;"><b>Hola ${clientName},</b></p>
          <p style="color: #555;">Aquí tienes el detalle de costos estimados para tu evento:</p>
  
          <table style="width: 100%; border-collapse: collapse; margin-top: 20px;">
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">📦 Logística</td>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">$${logistica.toLocaleString()}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">🏢 Alquiler del sitio</td>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">$${alquiler_sitio.toLocaleString()}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">🍽️ Alimentación</td>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">$${alimentacion.toLocaleString()}</td>
            </tr>
            <tr>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">🔧 Recursos</td>
              <td style="padding: 10px; border-bottom: 1px solid #eee;">$${recursos.toLocaleString()}</td>
            </tr>
            <tr>
              <td style="padding: 10px; font-weight: bold;">💵 Total</td>
              <td style="padding: 10px; font-weight: bold;">$${total.toLocaleString()}</td>
            </tr>
          </table>
  
          <p style="color: #555; font-size: 14px; margin-top: 30px;">Gracias por confiar en EventosIA. ¡Estamos listos para ayudarte a crear una experiencia inolvidable!</p>
  
          <div style="margin-top: 30px;">
            <a href="${acceptLink}" style="background-color: #28a745; color: white; padding: 10px 20px; text-decoration: none; font-size: 18px; border-radius: 5px; font-weight: bold; display: inline-block; margin-bottom: 10px;">✅ Aceptar Cotización</a><br>
            <a href="${rejectLink}" style="background-color: #dc3545; color: white; padding: 10px 20px; text-decoration: none; font-size: 18px; border-radius: 5px; font-weight: bold; display: inline-block; margin-top: 10px;">❌ Rechazar Cotización</a>
          </div>
        </div>
        <div style="background: #f5f5f5; padding: 10px; border-radius: 0 0 10px 10px;">
          <p style="margin: 0; font-size: 14px; color: #555;">📩 EventosIA | Todos los derechos reservados.</p>
        </div>
      </div>
  
      <!-- Responsividad para dispositivos móviles -->
      <style>
        @media (max-width: 600px) {
          .container {
            width: 100% !important;
            padding: 10px !important;
          }
          .button {
            width: 100% !important;
            padding: 12px !important;
            font-size: 16px !important;
          }
          .header {
            font-size: 20px !important;
          }
        }
      </style>
    `
  };  
};

// src/helpers/billingMailHelper.js
export const sendBillingEmail = async (email, clientName, billingDetails, billingId) => {
  const transporter = nodemailer.createTransport({
    service: 'gmail',
    auth: {
      user: process.env.EMAIL_USER,
      pass: process.env.EMAIL_PASS,
    },
  });

  const mailOptions = getBillingMailOptions(email, clientName, billingDetails, billingId);

  await transporter.sendMail(mailOptions);
};
