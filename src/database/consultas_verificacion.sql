-- ========================================
-- CONSULTAS PARA VERIFICAR DATOS EN PGADMIN
-- Ejecuta estas consultas en pgAdmin > Query Tool
-- ========================================

-- 1. VER TODOS LOS ESTUDIANTES REGISTRADOS
SELECT 
    u.id_usuario,
    u.nombre,
    u.apellido, 
    u.correo,
    u.rol,
    u.estado,
    u.creado_en
FROM usuarios u 
WHERE u.rol = 'estudiante'
ORDER BY u.creado_en DESC;

-- 2. VER EMBEDDINGS FACIALES GUARDADOS
SELECT 
    e.id_embedding,
    u.nombre,
    u.apellido,
    e.imagen_path,
    e.detection_confidence,
    e.quality_score,
    e.creado_en,
    e.activo
FROM embeddings_faciales e
JOIN usuarios u ON e.id_usuario = u.id_usuario
ORDER BY e.creado_en DESC;

-- 3. VER ASISTENCIAS REGISTRADAS
SELECT 
    a.id_asistencia,
    u.nombre,
    u.apellido,
    s.nombre as sesion,
    a.fecha_registro,
    a.metodo_registro,
    a.confidence_score,
    a.estado
FROM asistencias a
JOIN usuarios u ON a.id_estudiante = u.id_usuario
JOIN sesiones s ON a.id_sesion = s.id_sesion
ORDER BY a.fecha_registro DESC;

-- 4. VER RESUMEN COMPLETO
SELECT 
    '👥 Usuarios' as tipo,
    COUNT(*) as cantidad
FROM usuarios
UNION ALL
SELECT 
    '🧠 Embeddings', 
    COUNT(*)
FROM embeddings_faciales
UNION ALL
SELECT 
    '📝 Asistencias',
    COUNT(*)
FROM asistencias
UNION ALL
SELECT 
    '📚 Cursos',
    COUNT(*)
FROM cursos
UNION ALL
SELECT 
    '🎯 Sesiones',
    COUNT(*)
FROM sesiones;

-- 5. VER ASISTENCIAS DE HOY
SELECT 
    u.nombre || ' ' || u.apellido as estudiante,
    a.fecha_registro,
    a.confidence_score,
    a.metodo_registro,
    EXTRACT(HOUR FROM a.fecha_registro) || ':' || 
    LPAD(EXTRACT(MINUTE FROM a.fecha_registro)::text, 2, '0') as hora
FROM asistencias a
JOIN usuarios u ON a.id_estudiante = u.id_usuario
WHERE DATE(a.fecha_registro) = CURRENT_DATE
ORDER BY a.fecha_registro DESC;

-- 6. ESTADÍSTICAS POR ESTUDIANTE
SELECT 
    u.nombre || ' ' || u.apellido as estudiante,
    COUNT(a.id_asistencia) as total_asistencias,
    MAX(a.fecha_registro) as ultima_asistencia,
    AVG(a.confidence_score) as confianza_promedio
FROM usuarios u
LEFT JOIN asistencias a ON u.id_usuario = a.id_estudiante
WHERE u.rol = 'estudiante'
GROUP BY u.id_usuario, u.nombre, u.apellido
ORDER BY total_asistencias DESC;