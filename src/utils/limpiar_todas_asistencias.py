#!/usr/bin/env python3
"""
Limpiar TODAS las asistencias (empezar desde cero)
"""

from sqlalchemy import create_engine, text

DATABASE_URL = 'postgresql://postgres:camilomena@localhost:5432/prototipoPG_v2'

def limpiar_todas_asistencias():
    """Eliminar TODAS las asistencias"""
    engine = create_engine(DATABASE_URL)
    
    with engine.connect() as conn:
        print("🧹 Limpiando TODAS las asistencias...")
        
        # Contar total de asistencias
        result = conn.execute(text("SELECT COUNT(*) FROM asistencias"))
        total = result.fetchone()[0]
        
        if total == 0:
            print("ℹ️ No hay asistencias para eliminar")
            return
        
        print(f"⚠️ Se eliminarán {total} asistencias en total")
        
        # Eliminar todas las asistencias
        conn.execute(text("DELETE FROM asistencias"))
        
        # Reiniciar secuencia de IDs
        conn.execute(text("ALTER SEQUENCE asistencias_id_asistencia_seq RESTART WITH 1"))
        
        conn.commit()
        print(f"✅ {total} asistencias eliminadas")
        print("🔄 Secuencia de IDs reiniciada")
        print("🎯 Sistema listo para nuevas pruebas")

if __name__ == "__main__":
    limpiar_todas_asistencias()