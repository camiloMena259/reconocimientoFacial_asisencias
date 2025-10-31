"""
Crear sesiones académicas personalizadas con fechas y horarios interactivos
Permite al usuario elegir fecha, horarios y configuración de la sesión
"""

import psycopg2
from datetime import datetime, date
import sys
import os

# Configuración de la base de datos
DATABASE_CONFIG = {
    'host': 'localhost',
    'database': 'prototipoPG_v2',
    'user': 'postgres',
    'password': 'camilomena',
    'port': '5432'
}

def obtener_info_sesion():
    """Solicitar información de la sesión al usuario de forma interactiva"""
    print("📝 CONFIGURACIÓN DE NUEVA SESIÓN")
    print("="*50)
    
    # Obtener fecha
    print("\n📅 FECHA DE LA SESIÓN:")
    while True:
        fecha_input = input("Ingresa la fecha (YYYY-MM-DD) o presiona Enter para HOY: ").strip()
        if not fecha_input:
            fecha = datetime.now().date()
            break
        try:
            fecha = datetime.strptime(fecha_input, '%Y-%m-%d').date()
            break
        except ValueError:
            print("❌ Formato incorrecto. Use YYYY-MM-DD (ej: 2025-10-20)")
    
    # Obtener hora de inicio
    print(f"\n⏰ HORA DE INICIO:")
    while True:
        hora_inicio_input = input("Ingresa hora de inicio (HH:MM) o Enter para 08:00: ").strip()
        if not hora_inicio_input:
            hora_inicio = "08:00:00"
            break
        try:
            # Validar formato de hora
            datetime.strptime(hora_inicio_input, '%H:%M')
            hora_inicio = hora_inicio_input + ":00"
            break
        except ValueError:
            print("❌ Formato incorrecto. Use HH:MM (ej: 14:30)")
    
    # Obtener hora de fin
    print(f"\n⏰ HORA DE FIN:")
    while True:
        hora_fin_input = input("Ingresa hora de fin (HH:MM) o Enter para 12:00: ").strip()
        if not hora_fin_input:
            hora_fin = "12:00:00"
            break
        try:
            # Validar formato de hora
            datetime.strptime(hora_fin_input, '%H:%M')
            hora_fin = hora_fin_input + ":00"
            
            # Validar que hora fin sea posterior a hora inicio
            inicio = datetime.strptime(hora_inicio, '%H:%M:%S').time()
            fin = datetime.strptime(hora_fin, '%H:%M:%S').time()
            if fin <= inicio:
                print("❌ La hora de fin debe ser posterior a la hora de inicio")
                continue
            break
        except ValueError:
            print("❌ Formato incorrecto. Use HH:MM (ej: 16:30)")
    
    # Obtener nombre de la sesión
    print(f"\n📝 NOMBRE DE LA SESIÓN:")
    nombre_sesion = input("Ingresa nombre (o Enter para automático): ").strip()
    if not nombre_sesion:
        nombre_sesion = f"Sesión {fecha.strftime('%d-%m-%Y')} {hora_inicio[:5]}-{hora_fin[:5]}"
    
    # Obtener aula
    print(f"\n🏢 UBICACIÓN:")
    aula = input("Ingresa aula/ubicación (o Enter para 'Aula Principal'): ").strip()
    if not aula:
        aula = "Aula Principal"
    
    # Preguntar si habilitar asistencia inmediatamente
    print(f"\n🎛️ ASISTENCIA:")
    habilitar_asistencia = input("¿Habilitar asistencia inmediatamente? (s/n): ").strip().lower()
    asistencia_habilitada = habilitar_asistencia in ('s', 'sí', 'si', 'y', 'yes')
    
    return {
        'fecha': fecha,
        'hora_inicio': hora_inicio,
        'hora_fin': hora_fin,
        'nombre_sesion': nombre_sesion,
        'aula': aula,
        'asistencia_habilitada': asistencia_habilitada
    }

def crear_sesiones_personalizadas():
    """
    Crear sesiones académicas personalizadas de forma interactiva
    """
    print("🎯 CREADOR DE SESIONES ACADÉMICAS PERSONALIZADAS")
    print("="*60)
    
    # Obtener información de la sesión del usuario
    info_sesion = obtener_info_sesion()
    
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    
    try:
        # Detectar período académico automáticamente basado en la fecha
        # (No necesitamos importar el gestor, haremos el cálculo directamente aquí)
        
        # Determinar semestre y corte basado en la fecha elegida
        fecha_para_calculo = info_sesion['fecha']
        mes = fecha_para_calculo.month
        año = fecha_para_calculo.year
        
        if mes in [1, 2, 3, 4, 5, 6]:
            semestre = f"{año}-1"
            if mes in [1, 2]:
                corte = 1
            elif mes in [3, 4]:
                corte = 2
            else:  # mayo, junio
                corte = 3
        else:  # julio a diciembre
            semestre = f"{año}-2"
            if mes in [7, 8]:
                corte = 1
            elif mes in [9, 10]:
                corte = 2
            else:  # noviembre, diciembre
                corte = 3
        
        print(f"\n🎯 Período detectado: {año}, {semestre}, Corte {corte}")
        print(f"📅 Fecha: {info_sesion['fecha']}")
        print(f"⏰ Horario: {info_sesion['hora_inicio'][:5]} - {info_sesion['hora_fin'][:5]}")
        print(f"📝 Nombre: {info_sesion['nombre_sesion']}")
        print(f"🏢 Aula: {info_sesion['aula']}")
        print(f"🎛️ Asistencia: {'Habilitada' if info_sesion['asistencia_habilitada'] else 'Programada'}")
        
        # Confirmar creación
        confirmacion = input(f"\n¿Crear esta sesión? (s/n): ").strip().lower()
        if confirmacion not in ('s', 'sí', 'si', 'y', 'yes'):
            print("❌ Operación cancelada")
            return
        
        print(f"\n🔄 Creando sesión académica...")
        
        # Buscar siguiente número de sesión
        cursor.execute("""
            SELECT COALESCE(MAX(numero_sesion), 0) + 1 
            FROM sesiones_academicas 
            WHERE año = %s AND semestre = %s AND corte = %s
        """, (año, semestre, corte))
        
        numero_sesion = cursor.fetchone()[0]
        
        # Calcular duración en horas
        inicio = datetime.strptime(info_sesion['hora_inicio'], '%H:%M:%S').time()
        fin = datetime.strptime(info_sesion['hora_fin'], '%H:%M:%S').time()
        inicio_dt = datetime.combine(date.today(), inicio)
        fin_dt = datetime.combine(date.today(), fin)
        duracion_horas = (fin_dt - inicio_dt).total_seconds() / 3600
        
        # Determinar día de la semana
        dias_semana = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
        dia_semana = dias_semana[info_sesion['fecha'].weekday()]
        
        # Crear descripción automática
        descripcion = f"Sesión de {info_sesion['hora_inicio'][:5]} a {info_sesion['hora_fin'][:5]} - Reconocimiento Facial"
        
        # Estado inicial
        estado = 'activa' if info_sesion['asistencia_habilitada'] else 'programada'
        
        sesion_sql = """
        INSERT INTO sesiones_academicas (
            año, semestre, corte, id_curso, numero_sesion, nombre_sesion,
            descripcion, fecha_programada, hora_inicio, hora_fin, dia_semana,
            aula, estado, asistencia_habilitada, tolerancia_minutos,
            duracion_horas, tipo_clase, creada_en
        ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (año, semestre, corte, id_curso, numero_sesion) 
        DO UPDATE SET 
            asistencia_habilitada = EXCLUDED.asistencia_habilitada,
            estado = EXCLUDED.estado,
            actualizada_en = CURRENT_TIMESTAMP
        RETURNING id_sesion;
        """
        
        cursor.execute(sesion_sql, (
            año,                                    # año
            semestre,                              # semestre  
            corte,                                 # corte
            1,                                     # id_curso
            numero_sesion,                         # numero_sesion
            info_sesion['nombre_sesion'],          # nombre_sesion
            descripcion,                           # descripcion
            info_sesion['fecha'],                  # fecha_programada
            info_sesion['hora_inicio'],            # hora_inicio
            info_sesion['hora_fin'],               # hora_fin
            dia_semana,                            # dia_semana
            info_sesion['aula'],                   # aula
            estado,                                # estado
            info_sesion['asistencia_habilitada'],  # asistencia_habilitada
            15,                                    # tolerancia_minutos
            duracion_horas,                        # duracion_horas
            'personalizada',                       # tipo_clase
            datetime.now()                         # creada_en
        ))
        
        id_sesion = cursor.fetchone()[0]
        print(f"✅ Sesión creada exitosamente: ID {id_sesion}")
        print(f"   📅 {info_sesion['fecha']}")
        print(f"   ⏰ {info_sesion['hora_inicio'][:5]} - {info_sesion['hora_fin'][:5]} ({duracion_horas:.1f} horas)")
        print(f"   � {info_sesion['aula']}")
        print(f"   🎛️ Asistencia: {'HABILITADA' if info_sesion['asistencia_habilitada'] else 'Programada'}")
        
        conn.commit()
        
        # VERIFICACIÓN Y PRÓXIMOS PASOS
        print(f"\n🎉 ¡SESIÓN CREADA EXITOSAMENTE!")
        print("="*50)
        
        if info_sesion['asistencia_habilitada']:
            print("✅ La sesión está ACTIVA - puedes registrar asistencias inmediatamente")
        else:
            print("🔄 La sesión está programada - se activará automáticamente en su horario")
        
        print(f"\n📋 DETALLES FINALES:")
        print(f"   🆔 ID Sesión: {id_sesion}")
        print(f"   📊 Número: {numero_sesion} (Período: {semestre}, Corte {corte})")
        print(f"   📅 {info_sesion['fecha'].strftime('%A, %d de %B de %Y')}")
        print(f"   ⏰ {info_sesion['hora_inicio'][:5]} - {info_sesion['hora_fin'][:5]}")
        print(f"   � {info_sesion['aula']}")
        
        # Verificar si la sesión está en horario actual
        ahora = datetime.now()
        if ahora.date() == info_sesion['fecha'] and info_sesion['asistencia_habilitada']:
            hora_actual = ahora.time()
            hora_inicio = datetime.strptime(info_sesion['hora_inicio'], '%H:%M:%S').time()
            hora_fin = datetime.strptime(info_sesion['hora_fin'], '%H:%M:%S').time()
            
            if hora_inicio <= hora_actual <= hora_fin:
                print(f"\n� ¡SESIÓN EN CURSO!")
                print(f"   ⏰ Hora actual: {ahora.strftime('%H:%M:%S')}")
                print(f"   ✅ Puedes registrar asistencias AHORA")
            elif hora_actual < hora_inicio:
                print(f"\n⏰ La sesión iniciará a las {info_sesion['hora_inicio'][:5]}")
            else:
                print(f"\n⏰ La sesión ya terminó a las {info_sesion['hora_fin'][:5]}")
        
        print(f"\n💡 CONSEJOS:")
        print(f"   • Usa 'python src/utils/verificar_sistema_completo.py' para ver el estado general")
        print(f"   • Usa 'python main.py' para iniciar el reconocimiento facial")
        if not info_sesion['asistencia_habilitada']:
            print(f"   • La sesión se habilitará automáticamente en su horario")
        
    except Exception as e:
        print(f"❌ Error creando sesión: {e}")
        conn.rollback()
    
    finally:
        cursor.close()
        conn.close()

def main():
    """Función principal con menú interactivo"""
    while True:
        print(f"\n🎯 GESTOR DE SESIONES ACADÉMICAS")
        print("="*40)
        print("1. ➕ Crear nueva sesión personalizada")
        print("2. 📊 Ver sesiones existentes")
        print("3. 🚪 Salir")
        
        opcion = input(f"\nSelecciona opción (1-3): ").strip()
        
        if opcion == '1':
            crear_sesiones_personalizadas()
            input(f"\nPresiona Enter para continuar...")
        elif opcion == '2':
            mostrar_sesiones_existentes()
            input(f"\nPresiona Enter para continuar...")
        elif opcion == '3':
            print("👋 ¡Hasta luego!")
            break
        else:
            print("❌ Opción inválida")

def mostrar_sesiones_existentes():
    """Mostrar las sesiones académicas existentes"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                id_sesion, numero_sesion, nombre_sesion, fecha_programada,
                hora_inicio, hora_fin, aula, estado, asistencia_habilitada,
                año, semestre, corte
            FROM sesiones_academicas
            ORDER BY fecha_programada DESC, hora_inicio DESC
            LIMIT 10
        """)
        
        sesiones = cursor.fetchall()
        
        print(f"\n📋 SESIONES ACADÉMICAS RECIENTES (últimas 10):")
        print("-"*80)
        
        if not sesiones:
            print("   ℹ️ No hay sesiones registradas")
            return
        
        for sesion in sesiones:
            id_sesion, numero, nombre, fecha, inicio, fin, aula, estado, habilitada, año, semestre, corte = sesion
            status_icon = "🟢" if habilitada else "🔴"
            estado_icon = "✅" if estado == 'activa' else "📅" if estado == 'programada' else "⏹️"
            
            print(f"{status_icon} ID {id_sesion} | Sesión {numero} - {nombre}")
            print(f"   📅 {fecha} | ⏰ {inicio} - {fin} | 🏢 {aula}")
            print(f"   📊 {año}, {semestre}, Corte {corte} | {estado_icon} {estado.title()}")
            print()
    
    except Exception as e:
        print(f"❌ Error consultando sesiones: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    main()