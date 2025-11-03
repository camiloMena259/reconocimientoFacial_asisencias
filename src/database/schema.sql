-- ============================================================
-- SCHEMA PRINCIPAL - Sistema de Reconocimiento Facial
-- ============================================================
-- Base de datos: prototipoPG_v2
-- Generado automáticamente: 2025-10-31 08:37:59
-- Script: generar_schemas.py
-- ============================================================

-- ============================================================
-- TIPOS ENUM
-- ============================================================

-- Tipo para roles de usuario
CREATE TYPE rol_usuario AS ENUM ('estudiante', 'profesor', 'administrador');

-- Tipo para estados de usuario
CREATE TYPE estado_usuario AS ENUM ('activo', 'inactivo', 'suspendido');

-- Tipo para estados de curso
CREATE TYPE estado_curso AS ENUM ('activo', 'finalizado', 'cancelado');

-- Tipo para métodos de registro (backup)
CREATE TYPE metodo_registro AS ENUM ('reconocimiento_facial', 'manual', 'qr_code');

-- Tipo para estados de asistencia (backup)
CREATE TYPE estado_asistencia AS ENUM ('presente', 'tardanza', 'ausente', 'justificado');

-- Tipo para tipos de sesión (backup)
CREATE TYPE tipo_sesion AS ENUM ('teorica', 'practica', 'laboratorio', 'evaluacion', 'taller');

-- ============================================================
-- TABLAS PRINCIPALES
-- ============================================================

-- Tabla: usuarios
CREATE TABLE IF NOT EXISTS usuarios (
    id_usuario INTEGER DEFAULT nextval('usuarios_id_usuario_seq'::regclass) NOT NULL,
    nombre VARCHAR(100) NOT NULL,
    apellido VARCHAR(100) NOT NULL,
    correo VARCHAR(255) NOT NULL,
    contrasena_hash VARCHAR(255) NOT NULL,
    rol ROL_USUARIO DEFAULT 'estudiante'::rol_usuario NOT NULL,
    telefono VARCHAR(20) NULL,
    perfil_foto_path VARCHAR(500) NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    estado ESTADO_USUARIO DEFAULT 'activo'::estado_usuario NULL,
    email VARCHAR(255) NULL,
    PRIMARY KEY (id_usuario),
    CONSTRAINT usuarios_correo_unique UNIQUE (correo)
);

CREATE INDEX IF NOT EXISTS idx_usuarios_correo ON usuarios (correo);
CREATE INDEX IF NOT EXISTS idx_usuarios_estado ON usuarios (estado);
CREATE INDEX IF NOT EXISTS idx_usuarios_rol ON usuarios (rol);
CREATE UNIQUE INDEX IF NOT EXISTS usuarios_correo_key ON usuarios (correo);

COMMENT ON TABLE usuarios IS 'Tabla principal de usuarios del sistema (estudiantes, profesores, administradores)';
COMMENT ON COLUMN usuarios.rol IS 'Rol del usuario: estudiante, profesor, administrador';
COMMENT ON COLUMN usuarios.estado IS 'Estado del usuario: activo, inactivo, suspendido';
COMMENT ON COLUMN usuarios.correo IS 'Email único del usuario (usado para login)';

-- Tabla: embeddings_faciales
CREATE TABLE IF NOT EXISTS embeddings_faciales (
    id_embedding INTEGER DEFAULT nextval('embeddings_faciales_id_embedding_seq'::regclass) NOT NULL,
    id_usuario INTEGER NULL,
    embedding_vector BYTEA NOT NULL,
    imagen_path VARCHAR(500) NULL,
    detection_confidence DOUBLE PRECISION DEFAULT 0.0 NULL,
    quality_score DOUBLE PRECISION DEFAULT 0.0 NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    activo BOOLEAN DEFAULT true NULL,
    PRIMARY KEY (id_embedding),
    CONSTRAINT embeddings_faciales_id_usuario_fkey FOREIGN KEY (id_usuario) REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_embeddings_activo ON embeddings_faciales (activo);
CREATE INDEX IF NOT EXISTS idx_embeddings_usuario ON embeddings_faciales (id_usuario);

COMMENT ON TABLE embeddings_faciales IS 'Vectores de características faciales para reconocimiento';
COMMENT ON COLUMN embeddings_faciales.embedding_vector IS 'Vector de 128 dimensiones generado por face_recognition (serializado)';
COMMENT ON COLUMN embeddings_faciales.detection_confidence IS 'Confianza de la detección facial (0.0 a 1.0)';
COMMENT ON COLUMN embeddings_faciales.quality_score IS 'Score de calidad de la imagen facial';
COMMENT ON COLUMN embeddings_faciales.activo IS 'Si el embedding está activo para usar en reconocimiento';

-- ============================================================
-- TABLAS DE BACKUP (Mantener para referencia histórica)
-- ============================================================

-- Tabla: backup_asistencias
CREATE TABLE IF NOT EXISTS backup_asistencias (
    id_asistencia INTEGER NULL,
    id_estudiante INTEGER NULL,
    id_sesion INTEGER NULL,
    fecha_registro TIMESTAMP NULL,
    metodo_registro METODO_REGISTRO NULL,
    confidence_score DOUBLE PRECISION NULL,
    estado ESTADO_ASISTENCIA NULL,
    notas TEXT NULL,
    ubicacion_registro VARCHAR(200) NULL,
    ip_registro INET NULL,
    backup_fecha TIMESTAMPTZ NULL
);

-- Tabla: backup_sesiones
CREATE TABLE IF NOT EXISTS backup_sesiones (
    id_sesion INTEGER NULL,
    id_curso INTEGER NULL,
    nombre VARCHAR(200) NULL,
    descripcion TEXT NULL,
    fecha_programada TIMESTAMP NULL,
    duracion_minutos INTEGER NULL,
    tipo TIPO_SESION NULL,
    ubicacion VARCHAR(200) NULL,
    tolerancia_minutos INTEGER NULL,
    activa BOOLEAN NULL,
    creada_en TIMESTAMP NULL,
    hora_inicio TIME WITHOUT TIME ZONE NULL,
    hora_fin TIME WITHOUT TIME ZONE NULL,
    dias_semana ARRAY NULL,
    fecha_creacion TIMESTAMP NULL,
    estado_sesion VARCHAR(20) NULL,
    id_corte INTEGER NULL,
    numero_sesion INTEGER NULL,
    duracion_horas NUMERIC(3,1) NULL,
    backup_fecha TIMESTAMPTZ NULL
);

-- Tabla: inscripciones
CREATE TABLE IF NOT EXISTS inscripciones (
    id_inscripcion INTEGER DEFAULT nextval('inscripciones_id_inscripcion_seq'::regclass) NOT NULL,
    id_estudiante INTEGER NULL,
    id_curso INTEGER NULL,
    fecha_inscripcion TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    estado ESTADO_USUARIO DEFAULT 'activo'::estado_usuario NULL,
    PRIMARY KEY (id_inscripcion),
    CONSTRAINT inscripciones_id_estudiante_fkey FOREIGN KEY (id_estudiante) REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT inscripciones_id_curso_fkey FOREIGN KEY (id_curso) REFERENCES cursos(id_curso) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT inscripciones_estudiante_curso_unique UNIQUE (id_estudiante, id_curso)
);

CREATE INDEX IF NOT EXISTS idx_inscripciones_curso ON inscripciones (id_curso);
CREATE INDEX IF NOT EXISTS idx_inscripciones_estudiante ON inscripciones (id_estudiante);
CREATE UNIQUE INDEX IF NOT EXISTS inscripciones_id_estudiante_id_curso_key ON inscripciones (id_estudiante, id_curso);

COMMENT ON TABLE inscripciones IS 'Relación entre estudiantes y cursos (matrícula)';
COMMENT ON COLUMN inscripciones.estado IS 'Estado de la inscripción: activo, inactivo';

-- ============================================================
-- FUNCIONES AUXILIARES
-- ============================================================

-- Función para actualizar timestamp de actualización en usuarios
CREATE OR REPLACE FUNCTION actualizar_timestamp_usuario()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizado_en = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para usuarios
DROP TRIGGER IF EXISTS trigger_actualizar_usuario ON usuarios;
CREATE TRIGGER trigger_actualizar_usuario
    BEFORE UPDATE ON usuarios
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_timestamp_usuario();

-- Función para actualizar timestamp en embeddings_faciales
DROP TRIGGER IF EXISTS trigger_actualizar_embedding ON embeddings_faciales;
CREATE TRIGGER trigger_actualizar_embedding
    BEFORE UPDATE ON embeddings_faciales
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_timestamp_usuario();

-- ============================================================
-- FIN DEL SCHEMA PRINCIPAL
-- ============================================================