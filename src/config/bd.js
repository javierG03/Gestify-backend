import pkg from 'pg';
const { Pool } = pkg;

import dotenv from 'dotenv';


dotenv.config();

const pool = new Pool({
  connectionString: process.env.DATABASE_URL,
  ssl: process.env.DATABASE_URL.includes('localhost') ? false : { rejectUnauthorized: false },
});


// verificar conexión para no ponernos nerviosos
async function verifyConnection() {
  try {
    await pool.query('SELECT 1');
    console.log('✅ Conexión exitosa con PostgreSQL.');
  } catch (error) {
    console.error('❌ Error al conectar con PostgreSQL:', error);
  }
}

verifyConnection(); // Llamada inmediata para testear la conexión

export default pool;

