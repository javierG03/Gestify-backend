// crear-admin.js
import bcrypt from 'bcrypt';
import pool from './src/config/bd.js';

async function createAdmin() {
    const client = await pool.connect();
    
    try {
        await client.query('BEGIN');
        
        // Configuración del administrador
        const adminData = {
            name: 'Super',
            last_name: 'Administrador', 
            email: 'gaona2762@gmail.com', // CAMBIAR por tu email real
            password: 'Admin123', // CAMBIAR por una contraseña segura
            role_id: 1 // Admin role
        };
        
        console.log('Iniciando creación del usuario administrador...');
        
        // Verificar si el admin ya existe
        const existingUser = await client.query(
            'SELECT id_user FROM users WHERE email = $1',
            [adminData.email]
        );
        
        if (existingUser.rows.length > 0) {
            console.log('El usuario administrador ya existe con email:', adminData.email);
            return;
        }
        
        console.log('Encriptando contraseña...');
        // Encriptar contraseña
        const hashedPassword = await bcrypt.hash(adminData.password, 10);
        
        console.log('Creando usuario en la base de datos...');
        // Crear usuario
        const userResult = await client.query(`
            INSERT INTO users (name, last_name, email, password, email_verified, created_at)
            VALUES ($1, $2, $3, $4, $5, NOW())
            RETURNING id_user, name, last_name, email
        `, [adminData.name, adminData.last_name, adminData.email, hashedPassword, true]);
        
        const newUser = userResult.rows[0];
        console.log('Usuario creado con ID:', newUser.id_user);
        
        // Asignar rol de administrador
        console.log('Asignando rol de administrador...');
        await client.query(`
            INSERT INTO user_role (user_id, role_id, assigned_at)
            VALUES ($1, $2, NOW())
        `, [newUser.id_user, adminData.role_id]);
        
        await client.query('COMMIT');
        
        console.log('\n=== USUARIO ADMINISTRADOR CREADO EXITOSAMENTE ===');
        console.log('Nombre:', `${newUser.name} ${newUser.last_name}`);
        console.log('Email:', newUser.email);
        console.log('Contraseña:', adminData.password);
        console.log('ID de usuario:', newUser.id_user);
        console.log('Rol: Administrador (ID: 1)');
        console.log('Estado: Email verificado');
        console.log('\nIMPORTANTE: Cambia la contraseña después del primer login');
        console.log('===============================================\n');
        
        // Verificar permisos asignados
        const permissionsResult = await client.query(`
            SELECT COUNT(*) as total_permissions
            FROM role_permissions 
            WHERE id_role = $1
        `, [adminData.role_id]);
        
        console.log(`Permisos asignados: ${permissionsResult.rows[0].total_permissions} permisos`);
        
    } catch (error) {
        await client.query('ROLLBACK');
        console.error('Error al crear administrador:', error.message);
        
        if (error.code === '23505') { // Unique violation
            console.error('El email ya está registrado en la base de datos');
        }
    } finally {
        client.release();
    }
}

// Función para verificar la creación
async function verifyAdmin() {
    const client = await pool.connect();
    
    try {
        const result = await client.query(`
            SELECT 
                u.id_user,
                u.name,
                u.last_name,
                u.email,
                u.email_verified,
                r.name as role_name,
                ur.assigned_at,
                COUNT(rp.permission_id) as total_permissions
            FROM users u
            JOIN user_role ur ON u.id_user = ur.user_id
            JOIN roles r ON ur.role_id = r.id_role
            LEFT JOIN role_permissions rp ON r.id_role = rp.id_role
            WHERE r.name = 'Admin'
            GROUP BY u.id_user, u.name, u.last_name, u.email, u.email_verified, r.name, ur.assigned_at
        `);
        
        if (result.rows.length > 0) {
            const admin = result.rows[0];
            console.log('\n=== VERIFICACIÓN DEL ADMINISTRADOR ===');
            console.log('ID:', admin.id_user);
            console.log('Nombre completo:', `${admin.name} ${admin.last_name}`);
            console.log('Email:', admin.email);
            console.log('Email verificado:', admin.email_verified ? 'Sí' : 'No');
            console.log('Rol:', admin.role_name);
            console.log('Fecha de asignación:', admin.assigned_at);
            console.log('Permisos totales:', admin.total_permissions);
            console.log('=====================================\n');
        } else {
            console.log('No se encontró ningún usuario administrador');
        }
        
    } catch (error) {
        console.error('Error al verificar administrador:', error.message);
    } finally {
        client.release();
    }
}

// Función principal
async function main() {
    try {
        console.log('Conectando a la base de datos...');
        
        // Verificar conexión a la base de datos
        const testConnection = await pool.connect();
        testConnection.release();
        console.log('Conexión exitosa a la base de datos\n');
        
        // Crear administrador
        await createAdmin();
        
        // Verificar creación
        await verifyAdmin();
        
    } catch (error) {
        console.error('Error de conexión a la base de datos:', error.message);
        console.error('Verifica tu configuración de base de datos en config/bd.js');
    } finally {
        await pool.end();
        console.log('Conexión cerrada');
    }
}

// Ejecutar el script
main();