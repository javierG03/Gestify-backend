import express from 'express';
import db from '../config/bd.js'; // Asegúrate que tu conexión a la base de datos esté correcta
import { sendBillingEmail } from '../helpers/billingMailHelper.js';
import { getBillingDetailsForEvent } from '../helpers/billingDetailsHelper.js';

const router = express.Router();

// Ruta GET /billing/:eventId
router.get('/billing/:eventId', async (req, res) => {
  const { eventId } = req.params;

  try {
    const result = await db.query(`
      SELECT 
        b.id_billing,
        b.user_id,
        u.name AS user_name,
        u.last_name AS user_last_name,
        u.email AS user_email,
        b.event_id,
        b.price,
        b.state,
        b.payment_method,
        b.created_at
      FROM billing b
      JOIN users u ON u.id_user = b.user_id
      WHERE b.event_id = $1
      ORDER BY b.created_at DESC
    `, [eventId]);

    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'No se encontraron facturas para este evento' });
    }

    res.status(200).json({ billings: result.rows });
  } catch (err) {
    console.error('Error al obtener facturas:', err);
    res.status(500).json({ message: 'Error al obtener las facturas' });
  }
});


router.post('/billing', async (req, res) => {
  const { user_id, event_id, payment_method, price } = req.body;

  if (!user_id || !event_id || !price) {
    return res.status(400).json({ message: 'Faltan campos obligatorios' });
  }

  try {
    // Verificar que el evento y el usuario existan (opcional pero recomendable)
    const eventCheck = await db.query(`SELECT id_event FROM events WHERE id_event = $1`, [event_id]);
    if (eventCheck.rows.length === 0) {
      return res.status(404).json({ message: 'Evento no encontrado' });
    }

    const userCheck = await db.query(`SELECT id_user, name, last_name, email FROM users WHERE id_user = $1`, [user_id]);
    if (userCheck.rows.length === 0) {
      return res.status(404).json({ message: 'Usuario no encontrado' });
    }

    const user = userCheck.rows[0];

    // Insertar directamente la factura con los datos proporcionados
    const insert = await db.query(`
      INSERT INTO billing (user_id, event_id, price, state, payment_method)
      VALUES ($1, $2, $3, $4, $5)
      RETURNING id_billing, user_id, event_id, price, state, payment_method
    `, [user_id, event_id, price, 'Enviado', payment_method]);

    const billingId = insert.rows[0].id_billing;

    // Obtener los totales desglosados del evento
    const billingDetails = await getBillingDetailsForEvent(event_id);

    // Enviar correo al cliente con la cotización
    await sendBillingEmail(user.email, `${user.name} ${user.last_name}`, billingDetails || {
      logistica: 0,
      alquiler_sitio: 0,
      alimentacion: 0,
      recursos: 0,
      total: price
    }, billingId);

    return res.status(201).json({
      message: 'Factura creada y correo enviado',
      billing: insert.rows[0]
    });

  } catch (err) {
    console.error('Error al crear factura:', err);
    res.status(500).json({ message: 'Error al crear la factura' });
  }
});


// Ruta para aceptar la cotización
router.get('/billing/accept/:billingId', async (req, res) => {
  const { billingId } = req.params;

  if (!billingId) {
    return res.status(400).json({ message: 'ID de la factura no proporcionado' });
  }

  try {
    const result = await db.query(`
      UPDATE billing
      SET state = 'Aceptado'
      WHERE id_billing = $1
      RETURNING *
    `, [billingId]);

    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'Factura no encontrada' });
    }

    return res.json({
      message: 'Cotización aceptada',
      billing: result.rows[0]
    });

  } catch (error) {
    console.error('Error al aceptar la cotización:', error);
    res.status(500).json({ message: 'Error al aceptar la cotización' });
  }
});

// Ruta para rechazar la cotización
router.get('/billing/reject/:billingId', async (req, res) => {
  const { billingId } = req.params;

  if (!billingId) {
    return res.status(400).json({ message: 'ID de la factura no proporcionado' });
  }

  try {
    const result = await db.query(`
      UPDATE billing
      SET state = 'Rechazado'
      WHERE id_billing = $1
      RETURNING *
    `, [billingId]);

    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'Factura no encontrada' });
    }

    return res.json({
      message: 'Cotización rechazada',
      billing: result.rows[0]
    });

  } catch (error) {
    console.error('Error al rechazar la cotización:', error);
    res.status(500).json({ message: 'Error al rechazar la cotización' });
  }
});


// Ruta para marcar una factura como pagada
router.put('/billing/pay/:billingId', async (req, res) => {
  const { billingId } = req.params;

  if (!billingId) {
    return res.status(400).json({ message: 'ID de la factura no proporcionado' });
  }

  try {
    const result = await db.query(`
      UPDATE billing
      SET state = 'Pagado'
      WHERE id_billing = $1
      RETURNING *
    `, [billingId]);

    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'Factura no encontrada' });
    }

    return res.json({
      message: 'Factura marcada como pagada',
      billing: result.rows[0]
    });

  } catch (error) {
    console.error('Error al marcar la factura como pagada:', error);
    res.status(500).json({ message: 'Error al actualizar el estado de la factura' });
  }
});


// Ruta para eliminar una factura
router.delete('/billing/:billingId', async (req, res) => {
  const { billingId } = req.params;

  if (!billingId) {
    return res.status(400).json({ message: 'ID de la factura no proporcionado' });
  }

  try {
    const result = await db.query(`
      DELETE FROM billing
      WHERE id_billing = $1
      RETURNING *
    `, [billingId]);

    if (result.rows.length === 0) {
      return res.status(404).json({ message: 'Factura no encontrada o ya eliminada' });
    }

    return res.json({
      message: 'Factura eliminada correctamente',
      billing: result.rows[0]
    });

  } catch (error) {
    console.error('Error al eliminar la factura:', error);
    res.status(500).json({ message: 'Error al eliminar la factura' });
  }
});


export default router;
