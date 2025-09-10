import express from 'express';
import cors from 'cors';
import morgan from 'morgan';
import dotenv from 'dotenv';
import userRoutes from './src/routes/userRoutes.js';
import eventRoutes from './src/routes/eventRoutes.js';
import locationRoutes from './src/routes/locationRoutes.js';
import foodRoutes from './src/routes/foodRoutes.js';
import eventFoodRoutes from './src/routes/eventFoodRoutes.js';
import roleRoutes from './src/routes/roleRoutes.js';
import permissionsRoutes from './src/routes/permissionRoutes.js';
import invitationRoutes from './src/routes/invitationRoutes.js';
import statisticsRoutes from './src/routes/statisticsRoutes.js';
import resourceRoutes from './src/routes/resourceRoutes.js';
import eventResourceRoutes from './src/routes/eventResourceRoutes.js'
import typeOfEventRoutes from './src/routes/typeOfEventRoutes.js'
import participantsRoutes from './src/routes/participantsRoutes.js';
import invitationHandlerRoutes from './src/routes/invitationHandlerRoutes.js';
import categoryRoutes from './src/routes/categoryRoutes.js';
import cookieParser from 'cookie-parser';
import billingRoutes from './src/routes/billing.js';
import notificationRoutes from './src/routes/notifications.js';
import './src/config/cronJobs.js';
import { initNotificationScheduler } from './src/services/eventNotificationService.js';


// 1. Cargar variables de entorno
dotenv.config();

// 2. Inicializaciones
const app = express();
const PORT = process.env.PORT || 7777;

// 3. Configuración de CORS (permite solo el frontend en http://localhost:5173)
const allowedOrigins = [
    process.env.URL_FRONT_WEB_DEV,
    process.env.URL_FRONT_MOVIL_DEV,
    process.env.URL_FRONT_WEB_PROD,
    process.env.URL_FRONT_MOVIL_PROD
  ].filter(Boolean); // Filtra valores `undefined` o vacíos

const corsOptions = {
  origin: allowedOrigins, // Cambiar esto si el frontend está en otro puerto
  methods: 'GET,POST,PUT,DELETE',
  allowedHeaders: ['Content-Type', 'Authorization'],
  credentials: true,
};
app.use(cors(corsOptions));

// 4. Middlewares generales
app.use(express.json()); // Para parsear JSON
app.use(cookieParser());
app.use(express.urlencoded({ extended: true })); // Para datos del formulario
app.use(morgan('dev')); // Logger HTTP para desarrollo

// 5a. Ruta para el mensaje en /api
app.get('/api', (req, res) => {
    res.json({ message: 'API funcionando correctamente 🚀' });
  });

// 5b. Importar y usar rutas
app.use('/api', userRoutes);
app.use('/api/events', eventRoutes);
app.use('/api/locations', locationRoutes);
app.use('/api', foodRoutes);
app.use('/api', eventFoodRoutes);
app.use('/api', roleRoutes);
app.use('/api', permissionsRoutes);
app.use('/api', invitationRoutes);
app.use('/api', statisticsRoutes);
app.use('/api', resourceRoutes);
app.use('/api', eventResourceRoutes);
app.use('/api', typeOfEventRoutes);
app.use('/api', participantsRoutes);
app.use('/api', invitationHandlerRoutes);
app.use('/api', categoryRoutes);
app.use('/api', billingRoutes);
app.use('/api', notificationRoutes);

// Iniciar el programador de notificaciones
initNotificationScheduler();

// 6. Ruta inicial para verificar el servidor
// app.get('/', (req, res) => {
//   res.send('API funcionando 🚀');
// });
// Ruta inicial para listar todas las rutas y sus métodos
app.get("/", (req, res) => {
  const routes = [];

  app._router.stack.forEach((middleware) => {
      if (middleware.route) {
          const methods = Object.keys(middleware.route.methods).join(", ").toUpperCase();
          routes.push({ method: methods, path: middleware.route.path });
      } else if (middleware.name === "router") {
          middleware.handle.stack.forEach((handler) => {
              if (handler.route) {
                  const methods = Object.keys(handler.route.methods).join(", ").toUpperCase();
                  routes.push({ method: methods, path: handler.route.path });
              }
          });
      }
  });

  let html = `
      <html>
      <head>
          <title>Eventos Pichote Routes</title>
          <style>
              body { font-family: Arial, sans-serif; text-align: center; padding: 20px; transition: background 0.3s, color 0.3s; }
              .dark-mode { background-color: #222; color: white; }
              h2 { color: rgb(14, 143, 10); }
              .dark-mode h2 { color: rgb(50, 205, 50); }
              table { width: 80%; margin: auto; border-collapse: collapse; }
              th, td { border: 1px solid black; padding: 10px; text-align: left; }
              th { background-color: rgb(14, 143, 10); color: white; }
              tr:nth-child(even) { background-color: #f2f2f2; }
              .dark-mode tr:nth-child(even) { background-color: #444; }
              .dark-mode table { border: 1px solid white; }
              button { padding: 8px 12px; margin: 5px; cursor: pointer; border-radius: 5px; font-size: 14px; border: none; }
              .copy-btn { background-color: rgb(14, 143, 10); color: white; }
              .theme-btn { background-color: rgb(14, 143, 10); color: white; }
              .dark-mode .theme-btn { background-color: #888; color: black; }
          </style>
      </head>
      <body>
          <h2>Eventos Pichote Routes</h2>
          <button class="theme-btn" onclick="toggleTheme()">Dark Mode</button>
          <table>
              <tr><th>Método</th><th>Ruta</th><th>Acción</th></tr>`;

  routes.forEach((route) => {
      html += `<tr>
                  <td>${route.method}</td>
                  <td>${route.path}</td>
                  <td><button class="copy-btn" onclick="copyToClipboard('${route.path}')">Copy</button></td>
              </tr>`;
  });

  html += `
          </table>

          <script>
              function copyToClipboard(text) {
                  navigator.clipboard.writeText(text).then(() => {
                      alert("Ruta copiada: " + text);
                  }).catch(err => console.error("Error al copiar", err));
              }

              function toggleTheme() {
                  document.body.classList.toggle("dark-mode");
              }
          </script>

        <script src="https://cdn.userway.org/widget.js" data-account="c6gdoTT5VM"></script>

        <script src="https://cdn.botpress.cloud/webchat/v2.4/inject.js"></script>
        <script src="https://files.bpcontent.cloud/2025/04/29/17/20250429171130-8FWA1O82.js"></script>    



      </body>
      </html>
  `;

  res.send(html);
});



// 7. Manejo de errores para rutas no encontradas
app.use((req, res, next) => {
  res.status(404).json({ message: 'Ruta no encontrada ❌' });
});

// 8. Iniciar el servidor
app.listen(PORT, () => {
  console.log(`🔥 Servidor corriendo en → http://localhost:${PORT}`);
});
