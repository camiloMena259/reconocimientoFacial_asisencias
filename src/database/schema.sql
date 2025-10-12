-- ========================================
-- SCRIPT COMPLETO PARA BASE DE DATOS DE RECONOCIMIENTO FACIAL
-- Ejecutar en pgAdmin después de crear la base de datos
-- ========================================

-- Eliminar tablas si existen (para empezar limpio)
DROP TABLE IF EXISTS asistencias CASCADE;
DROP TABLE IF EXISTS embeddings_faciales CASCADE;
DROP TABLE IF EXISTS sesiones CASCADE;
DROP TABLE IF EXISTS inscripciones CASCADE;
DROP TABLE IF EXISTS cursos CASCADE;
DROP TABLE IF EXISTS usuarios CASCADE;

-- Eliminar tipos ENUM si existen
DROP TYPE IF EXISTS rol_usuario CASCADE;
DROP TYPE IF EXISTS estado_usuario CASCADE;
DROP TYPE IF EXISTS estado_curso CASCADE;
DROP TYPE IF EXISTS tipo_sesion CASCADE;
DROP TYPE IF EXISTS metodo_registro CASCADE;
DROP TYPE IF EXISTS estado_asistencia CASCADE;

-- ========================================
-- CREAR TIPOS ENUMERADOS
-- ========================================

-- Roles de usuario
CREATE TYPE rol_usuario AS ENUM ('estudiante', 'profesor', 'administrador');

-- Estados de usuario
CREATE TYPE estado_usuario AS ENUM ('activo', 'inactivo', 'suspendido');

-- Estados de curso
CREATE TYPE estado_curso AS ENUM ('activo', 'inactivo', 'finalizado');

-- Tipos de sesión
CREATE TYPE tipo_sesion AS ENUM ('clase', 'laboratorio', 'examen', 'taller');

-- Métodos de registro de asistencia
CREATE TYPE metodo_registro AS ENUM ('reconocimiento_facial', 'manual', 'qr_code');

-- Estados de asistencia
CREATE TYPE estado_asistencia AS ENUM ('presente', 'ausente', 'tardanza', 'justificado');

-- ========================================
-- CREAR TABLA USUARIOS
-- ========================================
CREATE TABLE usuarios (
    id_usuario SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    correo VARCHAR(255) UNIQUE NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol rol_usuario NOT NULL DEFAULT 'estudiante',
    telefono VARCHAR(20),
    perfil_foto_path VARCHAR(500),
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado estado_usuario DEFAULT 'activo'
);

-- ========================================
-- CREAR TABLA CURSOS
-- ========================================
CREATE TABLE cursos (
    id_curso SERIAL PRIMARY KEY,
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50) UNIQUE NOT NULL,
    descripcion TEXT,
    id_profesor INTEGER REFERENCES usuarios(id_usuario),
    creditos INTEGER DEFAULT 3,
    horario VARCHAR(200),
    aula VARCHAR(100),
    fecha_inicio DATE,
    fecha_fin DATE,
    estado estado_curso DEFAULT 'activo',
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- CREAR TABLA INSCRIPCIONES
-- ========================================
CREATE TABLE inscripciones (
    id_inscripcion SERIAL PRIMARY KEY,
    id_estudiante INTEGER REFERENCES usuarios(id_usuario),
    id_curso INTEGER REFERENCES cursos(id_curso),
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    estado estado_usuario DEFAULT 'activo',
    UNIQUE(id_estudiante, id_curso)
);

-- ========================================
-- CREAR TABLA SESIONES DE CLASE
-- ========================================
CREATE TABLE sesiones (
    id_sesion SERIAL PRIMARY KEY,
    id_curso INTEGER REFERENCES cursos(id_curso),
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    fecha_programada TIMESTAMP NOT NULL,
    duracion_minutos INTEGER DEFAULT 90,
    tipo tipo_sesion DEFAULT 'clase',
    ubicacion VARCHAR(200),
    tolerancia_minutos INTEGER DEFAULT 15,
    activa BOOLEAN DEFAULT false,
    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- CREAR TABLA EMBEDDINGS FACIALES
-- ========================================
CREATE TABLE embeddings_faciales (
    id_embedding SERIAL PRIMARY KEY,
    id_usuario INTEGER REFERENCES usuarios(id_usuario),
    embedding_vector BYTEA NOT NULL, -- Almacenar el array numpy serializado
    imagen_path VARCHAR(500),
    detection_confidence FLOAT DEFAULT 0.0,
    quality_score FLOAT DEFAULT 0.0,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    activo BOOLEAN DEFAULT true
);

-- ========================================
-- CREAR TABLA ASISTENCIAS
-- ========================================
CREATE TABLE asistencias (
    id_asistencia SERIAL PRIMARY KEY,
    id_estudiante INTEGER REFERENCES usuarios(id_usuario),
    id_sesion INTEGER REFERENCES sesiones(id_sesion),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metodo_registro metodo_registro DEFAULT 'reconocimiento_facial',
    confidence_score FLOAT,
    estado estado_asistencia DEFAULT 'presente',
    notas TEXT,
    ubicacion_registro VARCHAR(200),
    ip_registro INET,
    UNIQUE(id_estudiante, id_sesion)
);

-- ========================================
-- CREAR ÍNDICES PARA OPTIMIZACIÓN
-- ========================================

-- Índices para búsquedas frecuentes
CREATE INDEX idx_usuarios_correo ON usuarios(correo);
CREATE INDEX idx_usuarios_rol ON usuarios(rol);
CREATE INDEX idx_usuarios_estado ON usuarios(estado);

CREATE INDEX idx_cursos_codigo ON cursos(codigo);
CREATE INDEX idx_cursos_profesor ON cursos(id_profesor);
CREATE INDEX idx_cursos_estado ON cursos(estado);

CREATE INDEX idx_inscripciones_estudiante ON inscripciones(id_estudiante);
CREATE INDEX idx_inscripciones_curso ON inscripciones(id_curso);

CREATE INDEX idx_sesiones_curso ON sesiones(id_curso);
CREATE INDEX idx_sesiones_fecha ON sesiones(fecha_programada);
CREATE INDEX idx_sesiones_activa ON sesiones(activa);

CREATE INDEX idx_embeddings_usuario ON embeddings_faciales(id_usuario);
CREATE INDEX idx_embeddings_activo ON embeddings_faciales(activo);

CREATE INDEX idx_asistencias_estudiante ON asistencias(id_estudiante);
CREATE INDEX idx_asistencias_sesion ON asistencias(id_sesion);
CREATE INDEX idx_asistencias_fecha ON asistencias(fecha_registro);

-- ========================================
-- CREAR TRIGGERS PARA ACTUALIZACIÓN AUTOMÁTICA
-- ========================================

-- Función para actualizar timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Triggers para usuarios y embeddings
CREATE TRIGGER update_usuarios_updated_at 
    BEFORE UPDATE ON usuarios 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_embeddings_updated_at 
    BEFORE UPDATE ON embeddings_faciales 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- INSERTAR DATOS DE PRUEBA BÁSICOS
-- ========================================

-- Insertar un profesor administrador
INSERT INTO usuarios (nombre, apellido, correo, contrasena_hash, rol, estado) 
VALUES ('Administrador', 'Sistema', 'admin@sistema.edu', 'admin_hash', 'administrador', 'activo');

-- Insertar un curso de prueba
INSERT INTO cursos (nombre, codigo, descripcion, id_profesor, creditos, estado) 
VALUES ('Curso de Reconocimiento Facial', 'RF101', 'Curso para probar el sistema de asistencias', 1, 3, 'activo');

-- Insertar una sesión de prueba
INSERT INTO sesiones (id_curso, nombre, descripcion, fecha_programada, tipo, activa) 
VALUES (1, 'Sesión de Prueba', 'Primera sesión para probar asistencias', CURRENT_TIMESTAMP + INTERVAL '1 hour', 'clase', true);

-- ========================================
-- VERIFICACIONES FINALES
-- ========================================

-- Mostrar información de las tablas creadas
SELECT 
    schemaname,
    tablename,
    tableowner
FROM pg_tables 
WHERE schemaname = 'public' 
ORDER BY tablename;

-- Mostrar los tipos ENUM creados
SELECT 
    t.typname AS enum_name,
    e.enumlabel AS enum_value
FROM pg_type t 
JOIN pg_enum e ON t.oid = e.enumtypid  
WHERE t.typname LIKE '%_usuario' OR t.typname LIKE '%_curso' OR t.typname LIKE '%_sesion' OR t.typname LIKE '%_registro' OR t.typname LIKE '%_asistencia'
ORDER BY t.typname, e.enumsortorder;

-- ========================================
-- SCRIPT COMPLETADO EXITOSAMENTE
-- ========================================