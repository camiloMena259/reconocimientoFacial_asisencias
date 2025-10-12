#!/usr/bin/env python3
"""
Limpiar asistencias de hoy para hacer pruebas
"""

from sqlalchemy import create_engine, text
from datetime import datetime

DATABASE_URL = 'postgresql://postgres:camilomena@localhost:5432/prototipoPG_v2'

def limpiar_asistencias_hoy():
    """Eliminar solo las asistencias de hoy"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("🧹 Limpiando asistencias de hoy...")
        
        # Contar asistencias de hoy antes de eliminar
        result = conn.execute(text("""
            SELECT COUNT(*) FROM asistencias 
            WHERE DATE(fecha_registro) = CURRENT_DATE
        """))
        count_before = result.fetchone()[0]
        
        if count_before == 0:
            print("ℹ️ No hay asistencias de hoy para eliminar")
            return
        
        # Mostrar asistencias que se van a eliminar
        result = conn.execute(text("""
            SELECT u.nombre, u.apellido, a.fecha_registro
            FROM asistencias a
            JOIN usuarios u ON a.id_estudiante = u.id_usuario
            WHERE DATE(a.fecha_registro) = CURRENT_DATE
            ORDER BY a.fecha_registro DESC
        """))
        
        asistencias_hoy = result.fetchall()
        print(f"📝 Asistencias de hoy a eliminar ({count_before}):")
        for i, ast in enumerate(asistencias_hoy, 1):
            fecha = ast[2].strftime('%H:%M:%S') if ast[2] else 'Sin hora'
            print(f"  {i}. {ast[0]} {ast[1]} - {fecha}")
        
        # Eliminar asistencias de hoy
        result = conn.execute(text("""
            DELETE FROM asistencias 
            WHERE DATE(fecha_registro) = CURRENT_DATE
        """))
        
        conn.commit()
        print(f"✅ {count_before} asistencias de hoy eliminadas")
        print("🎯 Ahora puedes probar el reconocimiento nuevamente")

if __name__ == "__main__":
    limpiar_asistencias_hoy()