-- ============================================================
-- SCHEMA DE SESIONES ACADÉMICAS
-- ============================================================
-- Base de datos: prototipoPG_v2
-- Generado automáticamente: 2025-10-31 08:37:59
-- Script: generar_schemas.py
-- ============================================================

-- ============================================================
-- NOTA: Este schema asume que los tipos ENUM ya fueron creados
-- Si no existen, ejecutar primero schema.sql
-- ============================================================

-- ============================================================
-- TABLAS ACADÉMICAS
-- ============================================================

-- Tabla: cursos (debe crearse primero por las foreign keys)
CREATE TABLE IF NOT EXISTS cursos (
    id_curso INTEGER DEFAULT nextval('cursos_id_curso_seq'::regclass) NOT NULL,
    nombre VARCHAR(200) NOT NULL,
    codigo VARCHAR(50) NOT NULL,
    descripcion TEXT NULL,
    id_profesor INTEGER NULL,
    creditos INTEGER DEFAULT 3 NULL,
    horario VARCHAR(200) NULL,
    aula VARCHAR(100) NULL,
    fecha_inicio DATE NULL,
    fecha_fin DATE NULL,
    estado ESTADO_CURSO DEFAULT 'activo'::estado_curso NULL,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    PRIMARY KEY (id_curso),
    CONSTRAINT cursos_id_profesor_fkey FOREIGN KEY (id_profesor) REFERENCES usuarios(id_usuario) ON DELETE SET NULL ON UPDATE CASCADE
);

CREATE UNIQUE INDEX IF NOT EXISTS cursos_codigo_key ON cursos (codigo);
CREATE INDEX IF NOT EXISTS idx_cursos_codigo ON cursos (codigo);
CREATE INDEX IF NOT EXISTS idx_cursos_estado ON cursos (estado);
CREATE INDEX IF NOT EXISTS idx_cursos_profesor ON cursos (id_profesor);

COMMENT ON TABLE cursos IS 'Tabla de cursos académicos del sistema';
COMMENT ON COLUMN cursos.codigo IS 'Código único del curso (ej: PROG101)';
COMMENT ON COLUMN cursos.creditos IS 'Número de créditos académicos del curso';
COMMENT ON COLUMN cursos.estado IS 'Estado actual del curso: activo, finalizado, cancelado';

-- Tabla: sesiones_academicas
CREATE TABLE IF NOT EXISTS sesiones_academicas (
    id_sesion INTEGER DEFAULT nextval('sesiones_academicas_id_sesion_seq'::regclass) NOT NULL,
    año INTEGER NOT NULL,
    semestre VARCHAR(20) NOT NULL,
    corte INTEGER NOT NULL,
    id_curso INTEGER NULL,
    numero_sesion INTEGER NOT NULL,
    nombre_sesion VARCHAR(200) NOT NULL,
    descripcion TEXT NULL,
    fecha_programada DATE NOT NULL,
    hora_inicio TIME WITHOUT TIME ZONE NOT NULL,
    hora_fin TIME WITHOUT TIME ZONE NOT NULL,
    dia_semana VARCHAR(15) NOT NULL,
    aula VARCHAR(100) NULL,
    tolerancia_minutos INTEGER DEFAULT 15 NULL,
    estado VARCHAR(20) DEFAULT 'programada'::character varying NULL,
    asistencia_habilitada BOOLEAN DEFAULT false NULL,
    tema VARCHAR(500) NULL,
    objetivos TEXT NULL,
    duracion_horas NUMERIC(3,1) DEFAULT 3.0 NULL,
    tipo_clase VARCHAR(50) DEFAULT 'teorica'::character varying NULL,
    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    actualizada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    PRIMARY KEY (id_sesion),
    CONSTRAINT sesiones_academicas_id_curso_fkey FOREIGN KEY (id_curso) REFERENCES cursos(id_curso) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT sesiones_academicas_corte_check CHECK ((corte = ANY (ARRAY[1, 2, 3]))),
    CONSTRAINT sesiones_academicas_semestre_check CHECK ((semestre IN ('1', '2', 'verano'))),
    CONSTRAINT sesiones_academicas_estado_check CHECK ((estado IN ('programada', 'en_curso', 'finalizada', 'cancelada')))
);

CREATE INDEX IF NOT EXISTS idx_sesiones_acad_activa ON sesiones_academicas (asistencia_habilitada);
CREATE INDEX IF NOT EXISTS idx_sesiones_acad_fecha ON sesiones_academicas (fecha_programada);
CREATE INDEX IF NOT EXISTS idx_sesiones_acad_semestre ON sesiones_academicas (año, semestre, corte);
CREATE INDEX IF NOT EXISTS idx_sesiones_acad_curso ON sesiones_academicas (id_curso);
CREATE UNIQUE INDEX IF NOT EXISTS sesiones_academicas_año_semestre_corte_id_curso_numero_ses_key ON sesiones_academicas (año, semestre, corte, id_curso, numero_sesion);

COMMENT ON TABLE sesiones_academicas IS 'Sesiones de clase programadas por periodo académico';
COMMENT ON COLUMN sesiones_academicas.año IS 'Año académico (ej: 2025)';
COMMENT ON COLUMN sesiones_academicas.semestre IS 'Semestre académico: 1, 2 o verano';
COMMENT ON COLUMN sesiones_academicas.corte IS 'Número de corte académico (1, 2 o 3)';
COMMENT ON COLUMN sesiones_academicas.numero_sesion IS 'Número consecutivo de la sesión en el corte';
COMMENT ON COLUMN sesiones_academicas.asistencia_habilitada IS 'Indica si la sesión está activa para tomar asistencia';
COMMENT ON COLUMN sesiones_academicas.tolerancia_minutos IS 'Minutos de tolerancia antes de marcar tardanza';
COMMENT ON COLUMN sesiones_academicas.estado IS 'Estado de la sesión: programada, en_curso, finalizada, cancelada';

-- Tabla: asistencias_academicas
CREATE TABLE IF NOT EXISTS asistencias_academicas (
    id_asistencia INTEGER DEFAULT nextval('asistencias_academicas_id_asistencia_seq'::regclass) NOT NULL,
    id_sesion INTEGER NULL,
    id_estudiante INTEGER NULL,
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP NULL,
    metodo_registro VARCHAR(50) DEFAULT 'reconocimiento_facial'::character varying NULL,
    confidence_score DOUBLE PRECISION NULL,
    estado VARCHAR(20) DEFAULT 'presente'::character varying NULL,
    minutos_tardanza INTEGER DEFAULT 0 NULL,
    notas TEXT NULL,
    justificacion TEXT NULL,
    justificada_por INTEGER NULL,
    PRIMARY KEY (id_asistencia),
    CONSTRAINT asistencias_academicas_id_sesion_fkey FOREIGN KEY (id_sesion) REFERENCES sesiones_academicas(id_sesion) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT asistencias_academicas_id_estudiante_fkey FOREIGN KEY (id_estudiante) REFERENCES usuarios(id_usuario) ON DELETE CASCADE ON UPDATE CASCADE,
    CONSTRAINT asistencias_academicas_justificada_por_fkey FOREIGN KEY (justificada_por) REFERENCES usuarios(id_usuario) ON DELETE SET NULL ON UPDATE CASCADE,
    CONSTRAINT asistencias_academicas_estado_check CHECK ((estado IN ('presente', 'tardanza', 'ausente', 'justificado'))),
    CONSTRAINT asistencias_academicas_metodo_check CHECK ((metodo_registro IN ('reconocimiento_facial', 'manual', 'qr_code')))
);

CREATE UNIQUE INDEX IF NOT EXISTS asistencias_academicas_id_sesion_id_estudiante_key ON asistencias_academicas (id_sesion, id_estudiante);
CREATE INDEX IF NOT EXISTS idx_asistencias_acad_estudiante ON asistencias_academicas (id_estudiante);
CREATE INDEX IF NOT EXISTS idx_asistencias_acad_fecha ON asistencias_academicas (fecha_registro);
CREATE INDEX IF NOT EXISTS idx_asistencias_acad_sesion ON asistencias_academicas (id_sesion);
CREATE INDEX IF NOT EXISTS idx_asistencias_acad_estado ON asistencias_academicas (estado);

COMMENT ON TABLE asistencias_academicas IS 'Registro de asistencias de estudiantes a sesiones académicas';
COMMENT ON COLUMN asistencias_academicas.metodo_registro IS 'Método usado: reconocimiento_facial, manual, qr_code';
COMMENT ON COLUMN asistencias_academicas.confidence_score IS 'Nivel de confianza del reconocimiento facial (0.0 a 1.0)';
COMMENT ON COLUMN asistencias_academicas.estado IS 'Estado de asistencia: presente, tardanza, ausente, justificado';
COMMENT ON COLUMN asistencias_academicas.minutos_tardanza IS 'Minutos de retraso si aplica';
COMMENT ON COLUMN asistencias_academicas.justificada_por IS 'ID del usuario que justificó la ausencia (profesor/admin)';

-- ============================================================
-- FUNCIONES Y TRIGGERS
-- ============================================================

-- Función para actualizar timestamp de actualización
CREATE OR REPLACE FUNCTION actualizar_timestamp()
RETURNS TRIGGER AS $$
BEGIN
    NEW.actualizada_en = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Trigger para sesiones_academicas
DROP TRIGGER IF EXISTS trigger_actualizar_sesion ON sesiones_academicas;
CREATE TRIGGER trigger_actualizar_sesion
    BEFORE UPDATE ON sesiones_academicas
    FOR EACH ROW
    EXECUTE FUNCTION actualizar_timestamp();

-- ============================================================
-- VISTAS ÚTILES
-- ============================================================

-- Vista de sesiones con información del curso
CREATE OR REPLACE VIEW vista_sesiones_completas AS
SELECT 
    sa.id_sesion,
    sa.año,
    sa.semestre,
    sa.corte,
    sa.numero_sesion,
    sa.nombre_sesion,
    sa.fecha_programada,
    sa.hora_inicio,
    sa.hora_fin,
    sa.dia_semana,
    sa.aula,
    sa.estado,
    sa.asistencia_habilitada,
    c.codigo AS curso_codigo,
    c.nombre AS curso_nombre,
    c.aula AS curso_aula_default,
    u.nombre || ' ' || u.apellido AS profesor
FROM sesiones_academicas sa
LEFT JOIN cursos c ON sa.id_curso = c.id_curso
LEFT JOIN usuarios u ON c.id_profesor = u.id_usuario;

-- Vista de estadísticas de asistencia por sesión
CREATE OR REPLACE VIEW vista_estadisticas_asistencia AS
SELECT 
    sa.id_sesion,
    sa.nombre_sesion,
    sa.fecha_programada,
    COUNT(aa.id_asistencia) AS total_registros,
    SUM(CASE WHEN aa.estado = 'presente' THEN 1 ELSE 0 END) AS presentes,
    SUM(CASE WHEN aa.estado = 'tardanza' THEN 1 ELSE 0 END) AS tardanzas,
    SUM(CASE WHEN aa.estado = 'ausente' THEN 1 ELSE 0 END) AS ausentes,
    SUM(CASE WHEN aa.estado = 'justificado' THEN 1 ELSE 0 END) AS justificados,
    ROUND(AVG(aa.minutos_tardanza), 2) AS promedio_tardanza,
    ROUND(AVG(aa.confidence_score), 3) AS promedio_confianza
FROM sesiones_academicas sa
LEFT JOIN asistencias_academicas aa ON sa.id_sesion = aa.id_sesion
GROUP BY sa.id_sesion, sa.nombre_sesion, sa.fecha_programada;

-- ============================================================
-- DATOS DE EJEMPLO (COMENTADO - DESCOMENTAR SI ES NECESARIO)
-- ============================================================

/*
-- Insertar periodos académicos de ejemplo
INSERT INTO periodos_academicos (año, semestre, fecha_inicio, fecha_fin, estado)
VALUES 
    (2025, '1', '2025-02-01', '2025-06-30', 'activo'),
    (2025, '2', '2025-08-01', '2025-12-15', 'programado')
ON CONFLICT DO NOTHING;
*/