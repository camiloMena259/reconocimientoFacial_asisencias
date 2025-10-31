-- ========================================
-- SCHEMA PARA SISTEMA DE SESIONES ACADÉMICAS
-- Sistema de periodos académicos, cortes y sesiones de clase
-- ========================================

-- Eliminar tablas existentes relacionadas con sesiones si existen
DROP TABLE IF EXISTS asistencias_sesiones CASCADE;
DROP TABLE IF EXISTS sesiones_clase CASCADE;
DROP TABLE IF EXISTS cortes_academicos CASCADE;
DROP TABLE IF EXISTS periodos_academicos CASCADE;
DROP TABLE IF EXISTS horarios_clase CASCADE;

-- Eliminar tipos ENUM relacionados
DROP TYPE IF EXISTS tipo_periodo CASCADE;
DROP TYPE IF EXISTS estado_periodo CASCADE;
DROP TYPE IF EXISTS estado_corte CASCADE;
DROP TYPE IF EXISTS dia_semana CASCADE;

-- ========================================
-- CREAR TIPOS ENUMERADOS
-- ========================================

-- Tipo de periodo (1ra o 2da parte del año)
CREATE TYPE tipo_periodo AS ENUM ('primer_semestre', 'segundo_semestre');

-- Estado del periodo
CREATE TYPE estado_periodo AS ENUM ('activo', 'finalizado', 'programado');

-- Estado del corte
CREATE TYPE estado_corte AS ENUM ('activo', 'finalizado', 'programado');

-- Días de la semana
CREATE TYPE dia_semana AS ENUM ('lunes', 'martes', 'miercoles', 'jueves', 'viernes', 'sabado', 'domingo');

-- ========================================
-- TABLA PERIODOS ACADÉMICOS
-- ========================================
CREATE TABLE periodos_academicos (
    id_periodo SERIAL PRIMARY KEY,
    nombre VARCHAR(100) NOT NULL, -- Ej: "2025-1", "2025-2"
    tipo tipo_periodo NOT NULL,
    año INTEGER NOT NULL,
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    estado estado_periodo DEFAULT 'programado',
    descripcion TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- TABLA CORTES ACADÉMICOS
-- ========================================
CREATE TABLE cortes_academicos (
    id_corte SERIAL PRIMARY KEY,
    id_periodo INTEGER REFERENCES periodos_academicos(id_periodo),
    numero_corte INTEGER NOT NULL CHECK (numero_corte IN (1, 2, 3)),
    nombre VARCHAR(100) NOT NULL, -- Ej: "Primer Corte 2025-1"
    fecha_inicio DATE NOT NULL,
    fecha_fin DATE NOT NULL,
    porcentaje_nota DECIMAL(5,2) DEFAULT 33.33, -- Porcentaje de la nota final
    estado estado_corte DEFAULT 'programado',
    descripcion TEXT,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(id_periodo, numero_corte)
);

-- ========================================
-- TABLA HORARIOS DE CLASE
-- ========================================
CREATE TABLE horarios_clase (
    id_horario SERIAL PRIMARY KEY,
    id_curso INTEGER REFERENCES cursos(id_curso),
    id_periodo INTEGER REFERENCES periodos_academicos(id_periodo),
    dia_semana dia_semana NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    aula VARCHAR(100),
    tipo_clase VARCHAR(50) DEFAULT 'teorica', -- teorica, practica, laboratorio
    duracion_horas DECIMAL(3,1) NOT NULL, -- Ej: 3.0 para 3 horas
    activo BOOLEAN DEFAULT true,
    creado_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- TABLA SESIONES DE CLASE
-- ========================================
CREATE TABLE sesiones_clase (
    id_sesion_clase SERIAL PRIMARY KEY,
    id_curso INTEGER REFERENCES cursos(id_curso),
    id_corte INTEGER REFERENCES cortes_academicos(id_corte),
    id_horario INTEGER REFERENCES horarios_clase(id_horario),
    numero_sesion INTEGER NOT NULL, -- Secuencial por corte
    nombre VARCHAR(200) NOT NULL,
    descripcion TEXT,
    fecha_programada DATE NOT NULL,
    hora_inicio TIME NOT NULL,
    hora_fin TIME NOT NULL,
    duracion_real_minutos INTEGER,
    aula VARCHAR(100),
    tema VARCHAR(500),
    objetivos TEXT,
    estado VARCHAR(50) DEFAULT 'programada', -- programada, en_curso, finalizada, cancelada
    tolerancia_minutos INTEGER DEFAULT 15,
    asistencia_habilitada BOOLEAN DEFAULT false,
    creada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    actualizada_en TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- ========================================
-- TABLA ASISTENCIAS POR SESIÓN
-- ========================================
CREATE TABLE asistencias_sesiones (
    id_asistencia SERIAL PRIMARY KEY,
    id_estudiante INTEGER REFERENCES usuarios(id_usuario),
    id_sesion_clase INTEGER REFERENCES sesiones_clase(id_sesion_clase),
    fecha_registro TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    metodo_registro metodo_registro DEFAULT 'reconocimiento_facial',
    confidence_score FLOAT,
    estado estado_asistencia DEFAULT 'presente',
    minutos_tardanza INTEGER DEFAULT 0,
    notas TEXT,
    ubicacion_registro VARCHAR(200),
    ip_registro INET,
    justificacion TEXT,
    justificada_por INTEGER REFERENCES usuarios(id_usuario), -- Profesor que justifica
    fecha_justificacion TIMESTAMP,
    UNIQUE(id_estudiante, id_sesion_clase)
);

-- ========================================
-- CREAR ÍNDICES PARA OPTIMIZACIÓN
-- ========================================

CREATE INDEX idx_periodos_año ON periodos_academicos(año);
CREATE INDEX idx_periodos_tipo ON periodos_academicos(tipo);
CREATE INDEX idx_periodos_estado ON periodos_academicos(estado);

CREATE INDEX idx_cortes_periodo ON cortes_academicos(id_periodo);
CREATE INDEX idx_cortes_numero ON cortes_academicos(numero_corte);
CREATE INDEX idx_cortes_estado ON cortes_academicos(estado);

CREATE INDEX idx_horarios_curso ON horarios_clase(id_curso);
CREATE INDEX idx_horarios_periodo ON horarios_clase(id_periodo);
CREATE INDEX idx_horarios_dia ON horarios_clase(dia_semana);

CREATE INDEX idx_sesiones_curso ON sesiones_clase(id_curso);
CREATE INDEX idx_sesiones_corte ON sesiones_clase(id_corte);
CREATE INDEX idx_sesiones_fecha ON sesiones_clase(fecha_programada);
CREATE INDEX idx_sesiones_estado ON sesiones_clase(estado);

CREATE INDEX idx_asistencias_estudiante ON asistencias_sesiones(id_estudiante);
CREATE INDEX idx_asistencias_sesion ON asistencias_sesiones(id_sesion_clase);
CREATE INDEX idx_asistencias_fecha ON asistencias_sesiones(fecha_registro);

-- ========================================
-- CREAR TRIGGERS PARA ACTUALIZACIÓN AUTOMÁTICA
-- ========================================

-- Trigger para periodos académicos
CREATE TRIGGER update_periodos_updated_at 
    BEFORE UPDATE ON periodos_academicos 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger para cortes académicos
CREATE TRIGGER update_cortes_updated_at 
    BEFORE UPDATE ON cortes_academicos 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Trigger para sesiones de clase
CREATE TRIGGER update_sesiones_updated_at 
    BEFORE UPDATE ON sesiones_clase 
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- ========================================
-- FUNCIONES AUXILIARES
-- ========================================

-- Función para crear sesiones automáticamente basadas en horarios
CREATE OR REPLACE FUNCTION generar_sesiones_corte(
    p_id_corte INTEGER,
    p_id_curso INTEGER
) RETURNS INTEGER AS $$
DECLARE
    r_corte RECORD;
    r_horario RECORD;
    fecha_actual DATE;
    numero_sesion_counter INTEGER := 1;
    sesiones_creadas INTEGER := 0;
BEGIN
    -- Obtener información del corte
    SELECT * INTO r_corte FROM cortes_academicos WHERE id_corte = p_id_corte;
    
    -- Obtener horarios del curso para el periodo del corte
    FOR r_horario IN 
        SELECT h.* FROM horarios_clase h
        JOIN cortes_academicos c ON c.id_periodo = h.id_periodo
        WHERE c.id_corte = p_id_corte 
        AND h.id_curso = p_id_curso 
        AND h.activo = true
    LOOP
        fecha_actual := r_corte.fecha_inicio;
        
        -- Iterar por cada día del corte
        WHILE fecha_actual <= r_corte.fecha_fin LOOP
            -- Verificar si el día coincide con el horario
            IF EXTRACT(DOW FROM fecha_actual) = 
               CASE r_horario.dia_semana
                   WHEN 'lunes' THEN 1
                   WHEN 'martes' THEN 2
                   WHEN 'miercoles' THEN 3
                   WHEN 'jueves' THEN 4
                   WHEN 'viernes' THEN 5
                   WHEN 'sabado' THEN 6
                   WHEN 'domingo' THEN 0
               END
            THEN
                -- Crear sesión
                INSERT INTO sesiones_clase (
                    id_curso, id_corte, id_horario, numero_sesion,
                    nombre, fecha_programada, hora_inicio, hora_fin,
                    aula, tema, estado
                ) VALUES (
                    p_id_curso, p_id_corte, r_horario.id_horario, numero_sesion_counter,
                    'Sesión ' || numero_sesion_counter || ' - ' || r_horario.tipo_clase,
                    fecha_actual, r_horario.hora_inicio, r_horario.hora_fin,
                    r_horario.aula, 'Tema por definir', 'programada'
                );
                
                numero_sesion_counter := numero_sesion_counter + 1;
                sesiones_creadas := sesiones_creadas + 1;
            END IF;
            
            fecha_actual := fecha_actual + INTERVAL '1 day';
        END LOOP;
    END LOOP;
    
    RETURN sesiones_creadas;
END;
$$ LANGUAGE plpgsql;

-- ========================================
-- DATOS DE EJEMPLO PARA TESTING
-- ========================================

-- Insertar periodo académico 2025-1
INSERT INTO periodos_academicos (nombre, tipo, año, fecha_inicio, fecha_fin, estado) 
VALUES ('2025-1', 'primer_semestre', 2025, '2025-02-03', '2025-06-30', 'activo');

-- Insertar los 3 cortes del periodo 2025-1
INSERT INTO cortes_academicos (id_periodo, numero_corte, nombre, fecha_inicio, fecha_fin, estado) 
VALUES 
(1, 1, 'Primer Corte 2025-1', '2025-02-03', '2025-03-21', 'activo'),
(1, 2, 'Segundo Corte 2025-1', '2025-03-24', '2025-05-09', 'programado'),
(1, 3, 'Tercer Corte 2025-1', '2025-05-12', '2025-06-30', 'programado');

-- Insertar horario de ejemplo para el curso (2 sesiones por semana, 3 horas cada una)
-- Asumiendo que ya existe un curso con id_curso = 1
INSERT INTO horarios_clase (id_curso, id_periodo, dia_semana, hora_inicio, hora_fin, aula, tipo_clase, duracion_horas) 
VALUES 
(1, 1, 'martes', '08:00:00', '11:00:00', 'Aula 101', 'teorica', 3.0),
(1, 1, 'jueves', '08:00:00', '11:00:00', 'Aula 101', 'teorica', 3.0);

-- Generar sesiones automáticamente para el primer corte
SELECT generar_sesiones_corte(1, 1) as sesiones_creadas;

-- ========================================
-- CONSULTAS DE VERIFICACIÓN
-- ========================================

-- Ver estructura completa del sistema académico
SELECT 
    pa.nombre as periodo,
    ca.nombre as corte,
    ca.fecha_inicio,
    ca.fecha_fin,
    COUNT(sc.id_sesion_clase) as total_sesiones
FROM periodos_academicos pa
JOIN cortes_academicos ca ON pa.id_periodo = ca.id_periodo
LEFT JOIN sesiones_clase sc ON ca.id_corte = sc.id_corte
GROUP BY pa.nombre, ca.nombre, ca.fecha_inicio, ca.fecha_fin
ORDER BY pa.nombre, ca.numero_corte;

-- Ver horarios configurados
SELECT 
    c.nombre as curso,
    hc.dia_semana,
    hc.hora_inicio,
    hc.hora_fin,
    hc.duracion_horas,
    hc.aula,
    hc.tipo_clase
FROM horarios_clase hc
JOIN cursos c ON hc.id_curso = c.id_curso
WHERE hc.activo = true
ORDER BY c.nombre, hc.dia_semana;

-- Ver sesiones creadas
SELECT 
    sc.numero_sesion,
    sc.nombre,
    sc.fecha_programada,
    sc.hora_inicio,
    sc.hora_fin,
    sc.aula,
    sc.estado
FROM sesiones_clase sc
JOIN cortes_academicos ca ON sc.id_corte = ca.id_corte
WHERE ca.numero_corte = 1
ORDER BY sc.fecha_programada, sc.hora_inicio;