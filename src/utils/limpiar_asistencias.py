"""
Script interactivo para limpiar asistencias de la sesión activa
Borra solo las asistencias de la SESIÓN ACTIVA (sesión con asistencia_habilitada = true o la que coincida con fecha/hora actual)

Uso:
    python src/utils/limpiar_asistencias.py
"""

import psycopg2
from datetime import datetime
import sys
import os

# Configuración DB - adapta si usas variables de entorno
DATABASE_CONFIG = {
    'host': 'localhost',
    'database': 'prototipoPG_v2',
    'user': 'postgres',
    'password': 'camilomena',
    'port': '5432'
}


def conectar():
    try:
        conn = psycopg2.connect(**DATABASE_CONFIG)
        return conn
    except Exception as e:
        print(f"❌ Error conectando a la base de datos: {e}")
        sys.exit(1)


def contar_asistencias_totales(conn):
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM asistencias_academicas")
    total = cur.fetchone()[0]
    cur.close()
    return total


def obtener_sesion_activa(conn):
    """Devuelve la sesión activa (si existe) basada en `asistencia_habilitada = true` o por fecha/hora."""
    cur = conn.cursor()
    # Primero buscar asistencia_habilitada = true
    cur.execute("""
        SELECT id_sesion, nombre_sesion, fecha_programada, hora_inicio, hora_fin
        FROM sesiones_academicas
        WHERE asistencia_habilitada = true
        ORDER BY fecha_programada DESC
        LIMIT 1
    """)
    fila = cur.fetchone()
    if fila:
        cur.close()
        return fila  # (id_sesion, nombre, fecha, hora_inicio, hora_fin)

    # Si no hay una habilitada, buscar una que coincida con la fecha actual
    ahora = datetime.now()
    cur.execute("""
        SELECT id_sesion, nombre_sesion, fecha_programada, hora_inicio, hora_fin
        FROM sesiones_academicas
        WHERE fecha_programada = %s
        AND hora_inicio <= %s AND hora_fin >= %s
        ORDER BY hora_inicio LIMIT 1
    """, (ahora.date(), ahora.time(), ahora.time()))
    fila2 = cur.fetchone()
    cur.close()
    return fila2


def borrar_asistencias_sesion_activa(conn, confirm=False):
    sesion = obtener_sesion_activa(conn)
    if not sesion:
        print("ℹ️ No se encontró sesión activa (ni habilitada ni en curso ahora mismo).")
        return

    id_sesion, nombre, fecha, hora_inicio, hora_fin = sesion
    cur = conn.cursor()
    cur.execute("SELECT COUNT(*) FROM asistencias_academicas WHERE id_sesion = %s", (id_sesion,))
    total = cur.fetchone()[0]

    if total == 0:
        print(f"ℹ️ No hay asistencias registradas para la sesión activa (ID {id_sesion} - {nombre}).")
        cur.close()
        return

    if not confirm:
        resp = input(f"⚠️ Se eliminarán {total} asistencias de la sesión activa '{nombre}' (ID {id_sesion}). ¿Confirmas? (sí/no): ").strip().lower()
        if resp not in ('sí', 'si', 's', 'yes', 'y'):
            print("Operación cancelada")
            cur.close()
            return

    try:
        cur.execute("DELETE FROM asistencias_academicas WHERE id_sesion = %s", (id_sesion,))
        deleted = cur.rowcount
        conn.commit()
        print(f"✅ Eliminadas {deleted} asistencias de la sesión ID {id_sesion} - {nombre}")
    except Exception as e:
        conn.rollback()
        print(f"❌ Error eliminando asistencias: {e}")
    finally:
        cur.close()


def mostrar_menu():
    conn = conectar()
    try:
        while True:
            print('\n' + '='*60)
            print('🧹 LIMPIADOR DE ASISTENCIAS - SESIÓN ACTIVA')
            print('='*60)
            total = contar_asistencias_totales(conn)
            print(f'📊 Total asistencias en sistema: {total}')

            sesion = obtener_sesion_activa(conn)
            if sesion:
                cur = conn.cursor()
                cur.execute("SELECT COUNT(*) FROM asistencias_academicas WHERE id_sesion = %s", (sesion[0],))
                asistencias_sesion = cur.fetchone()[0]
                cur.close()
                print(f"🎯 Sesión activa: ID {sesion[0]} - {sesion[1]}")
                print(f"📅 Fecha: {sesion[2]} | Horario: {sesion[3]}-{sesion[4]}")
                print(f"👥 Asistencias en esta sesión: {asistencias_sesion}")
            else:
                print('ℹ️ No hay sesión activa detectada')

            print('\nOpciones:')
            print(' 1) Limpiar asistencias de la SESIÓN ACTIVA')
            print(' 2) Salir')

            opcion = input('\nSelecciona una opción (1/2): ').strip()
            if opcion == '1':
                borrar_asistencias_sesion_activa(conn)
            elif opcion == '2':
                print('👋 Saliendo')
                break
            else:
                print('Opción no válida')
    finally:
        conn.close()


if __name__ == '__main__':
    mostrar_menu()
