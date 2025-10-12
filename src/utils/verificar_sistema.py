#!/usr/bin/env python3
"""
Script para verificar todos los datos guardados en PostgreSQL
"""

from sqlalchemy import create_engine, text
from datetime import datetime
import pandas as pd

DATABASE_URL = 'postgresql://postgres:camilomena@localhost:5432/prototipoPG_v2'

def verificar_datos():
    """Verificar todos los datos del sistema"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("🔍 === VERIFICACIÓN COMPLETA DEL SISTEMA ===\n")
        
        # 1. Estudiantes registrados
        print("👥 ESTUDIANTES REGISTRADOS:")
        result = conn.execute(text("""
            SELECT nombre, apellido, correo, creado_en
            FROM usuarios 
            WHERE rol = 'estudiante'
            ORDER BY creado_en DESC
        """))
        
        estudiantes = result.fetchall()
        for i, est in enumerate(estudiantes, 1):
            fecha = est[3].strftime('%Y-%m-%d %H:%M') if est[3] else 'Sin fecha'
            print(f"  {i}. {est[0]} {est[1]} ({est[2]}) - Registrado: {fecha}")
        
        # 2. Embeddings faciales
        print(f"\n🧠 EMBEDDINGS FACIALES:")
        result = conn.execute(text("""
            SELECT u.nombre, u.apellido, e.imagen_path, e.detection_confidence, e.creado_en
            FROM embeddings_faciales e
            JOIN usuarios u ON e.id_usuario = u.id_usuario
            ORDER BY e.creado_en DESC
        """))
        
        embeddings = result.fetchall()
        for i, emb in enumerate(embeddings, 1):
            fecha = emb[4].strftime('%Y-%m-%d %H:%M') if emb[4] else 'Sin fecha'
            confidence = f"{emb[3]:.2f}" if emb[3] else "N/A"
            print(f"  {i}. {emb[0]} {emb[1]} - Confianza: {confidence} - {fecha}")
            print(f"     Imagen: {emb[2]}")
        
        # 3. Asistencias registradas
        print(f"\n📝 ASISTENCIAS REGISTRADAS:")
        result = conn.execute(text("""
            SELECT u.nombre, u.apellido, a.fecha_registro, a.confidence_score, a.metodo_registro
            FROM asistencias a
            JOIN usuarios u ON a.id_estudiante = u.id_usuario
            ORDER BY a.fecha_registro DESC
        """))
        
        asistencias = result.fetchall()
        if asistencias:
            for i, ast in enumerate(asistencias, 1):
                fecha = ast[2].strftime('%Y-%m-%d %H:%M:%S') if ast[2] else 'Sin fecha'
                confidence = f"{ast[3]:.1f}%" if ast[3] else "N/A"
                print(f"  {i}. {ast[0]} {ast[1]} - {fecha}")
                print(f"     Confianza: {confidence} - Método: {ast[4]}")
        else:
            print("  ⚠ No hay asistencias registradas")
        
        # 4. Resumen estadístico
        print(f"\n📊 RESUMEN ESTADÍSTICO:")
        
        # Contar registros
        counts = {}
        for table in ['usuarios', 'embeddings_faciales', 'asistencias', 'cursos', 'sesiones']:
            result = conn.execute(text(f"SELECT COUNT(*) FROM {table}"))
            counts[table] = result.fetchone()[0]
        
        print(f"  👥 Usuarios totales: {counts['usuarios']}")
        print(f"  🧠 Embeddings almacenados: {counts['embeddings_faciales']}")
        print(f"  📝 Asistencias registradas: {counts['asistencias']}")
        print(f"  📚 Cursos disponibles: {counts['cursos']}")
        print(f"  🎯 Sesiones creadas: {counts['sesiones']}")
        
        # 5. Asistencias de hoy
        print(f"\n📅 ASISTENCIAS DE HOY ({datetime.now().strftime('%Y-%m-%d')}):")
        result = conn.execute(text("""
            SELECT u.nombre, u.apellido, 
                   TO_CHAR(a.fecha_registro, 'HH24:MI:SS') as hora,
                   a.confidence_score
            FROM asistencias a
            JOIN usuarios u ON a.id_estudiante = u.id_usuario
            WHERE DATE(a.fecha_registro) = CURRENT_DATE
            ORDER BY a.fecha_registro DESC
        """))
        
        hoy = result.fetchall()
        if hoy:
            for i, reg in enumerate(hoy, 1):
                confidence = f"{reg[3]:.1f}%" if reg[3] else "N/A"
                print(f"  {i}. {reg[0]} {reg[1]} - {reg[2]} (Confianza: {confidence})")
        else:
            print("  ℹ️ No hay asistencias registradas hoy")
        
        # 6. Verificar integridad de datos
        print(f"\n🔎 VERIFICACIÓN DE INTEGRIDAD:")
        
        # Estudiantes sin embeddings
        result = conn.execute(text("""
            SELECT u.nombre, u.apellido
            FROM usuarios u
            LEFT JOIN embeddings_faciales e ON u.id_usuario = e.id_usuario
            WHERE u.rol = 'estudiante' AND e.id_embedding IS NULL
        """))
        
        sin_embeddings = result.fetchall()
        if sin_embeddings:
            print(f"  ⚠️ Estudiantes SIN embeddings faciales:")
            for est in sin_embeddings:
                print(f"    - {est[0]} {est[1]}")
        else:
            print(f"  ✅ Todos los estudiantes tienen embeddings faciales")
        
        # Embeddings sin usuarios
        result = conn.execute(text("""
            SELECT COUNT(*)
            FROM embeddings_faciales e
            LEFT JOIN usuarios u ON e.id_usuario = u.id_usuario
            WHERE u.id_usuario IS NULL
        """))
        
        huerfanos = result.fetchone()[0]
        if huerfanos > 0:
            print(f"  ⚠️ {huerfanos} embeddings huérfanos (sin usuario)")
        else:
            print(f"  ✅ Todos los embeddings tienen usuario asociado")
        
        print(f"\n✅ VERIFICACIÓN COMPLETADA")

if __name__ == "__main__":
    verificar_datos()