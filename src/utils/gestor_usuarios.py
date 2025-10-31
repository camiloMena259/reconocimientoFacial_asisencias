"""
Script para gestionar usuarios - Mostrar lista y eliminar por ID
"""

import psycopg2
from datetime import datetime

# Configuración de la base de datos
DATABASE_CONFIG = {
    'host': 'localhost',
    'database': 'prototipoPG_v2',
    'user': 'postgres',
    'password': 'camilomena',
    'port': '5432'
}

def mostrar_todos_los_usuarios():
    """Mostrar todos los usuarios del sistema con información detallada"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT 
                u.id_usuario,
                u.nombre,
                u.apellido,
                u.email,
                u.rol,
                COUNT(DISTINCT e.id_embedding) as num_fotos,
                COUNT(DISTINCT aa.id_asistencia) as num_asistencias_nuevas,
                COUNT(DISTINCT a.id_asistencia) as num_asistencias_viejas
            FROM usuarios u
            LEFT JOIN embeddings_faciales e ON u.id_usuario = e.id_usuario
            LEFT JOIN asistencias_academicas aa ON u.id_usuario = aa.id_estudiante
            LEFT JOIN asistencias a ON u.id_usuario = a.id_estudiante
            GROUP BY u.id_usuario, u.nombre, u.apellido, u.email, u.rol
            ORDER BY u.id_usuario
        """)
        
        usuarios = cursor.fetchall()
        
        print("👥 TODOS LOS USUARIOS EN EL SISTEMA")
        print("="*75)
        print(f"{'ID':<3} {'NOMBRE':<25} {'EMAIL':<25} {'ROL':<12} {'FOTOS':<6} {'ASIST':<6}")
        print("-"*75)
        
        for usuario in usuarios:
            id_usuario, nombre, apellido, email, rol, fotos, asist_nuevas, asist_viejas = usuario
            
            nombre_completo = f"{nombre} {apellido}"[:24]  # Truncar si es muy largo
            email_display = (email or "Sin email")[:24]
            total_asistencias = asist_nuevas + asist_viejas
            
            # Icono según el rol
            if rol == "estudiante":
                icono = "🎓"
            elif rol == "profesor":
                icono = "👨‍🏫"
            else:
                icono = "👤"
            
            print(f"{id_usuario:<3} {icono} {nombre_completo:<23} {email_display:<25} {rol:<12} {fotos:<6} {total_asistencias:<6}")
        
        print("-"*75)
        print(f"Total usuarios: {len(usuarios)}")
        
        return usuarios
        
    except Exception as e:
        print(f"❌ Error obteniendo usuarios: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def eliminar_usuario_por_id(id_usuario):
    """Eliminar completamente un usuario por su ID"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    
    try:
        # 1. Verificar que el usuario existe y obtener su info
        cursor.execute("""
            SELECT nombre, apellido, email, rol 
            FROM usuarios 
            WHERE id_usuario = %s
        """, (id_usuario,))
        
        usuario_info = cursor.fetchone()
        
        if not usuario_info:
            print(f"❌ ERROR: No existe usuario con ID {id_usuario}")
            return False
        
        nombre, apellido, email, rol = usuario_info
        nombre_completo = f"{nombre} {apellido}"
        
        print(f"\n🗑️ ELIMINANDO USUARIO ID {id_usuario}: {nombre_completo}")
        print("="*60)
        
        # 2. Eliminar asistencias académicas (tabla nueva)
        cursor.execute("DELETE FROM asistencias_academicas WHERE id_estudiante = %s", (id_usuario,))
        eliminados_asist_acad = cursor.rowcount
        print(f"✅ Asistencias académicas eliminadas: {eliminados_asist_acad}")
        
        # 3. Eliminar asistencias antiguas
        cursor.execute("DELETE FROM asistencias WHERE id_estudiante = %s", (id_usuario,))
        eliminados_asist_old = cursor.rowcount
        print(f"✅ Asistencias antiguas eliminadas: {eliminados_asist_old}")
        
        # 4. Eliminar inscripciones
        cursor.execute("DELETE FROM inscripciones WHERE id_estudiante = %s", (id_usuario,))
        eliminados_inscripciones = cursor.rowcount
        print(f"✅ Inscripciones eliminadas: {eliminados_inscripciones}")
        
        # 5. Eliminar embeddings faciales
        cursor.execute("DELETE FROM embeddings_faciales WHERE id_usuario = %s", (id_usuario,))
        eliminados_embeddings = cursor.rowcount
        print(f"✅ Embeddings faciales eliminados: {eliminados_embeddings}")
        
        # 6. Eliminar usuario principal
        cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        eliminado_usuario = cursor.rowcount
        print(f"✅ Usuario eliminado: {eliminado_usuario}")
        
        # 7. Commit todos los cambios
        conn.commit()
        
        print(f"\n🎉 USUARIO ELIMINADO COMPLETAMENTE")
        print(f"👤 {nombre_completo} (ID: {id_usuario})")
        print(f"📊 Total eliminado:")
        print(f"   • Asistencias académicas: {eliminados_asist_acad}")
        print(f"   • Asistencias antiguas: {eliminados_asist_old}")
        print(f"   • Inscripciones: {eliminados_inscripciones}")
        print(f"   • Fotos/Embeddings: {eliminados_embeddings}")
        print(f"   • Usuario: {eliminado_usuario}")
        
        return True
        
    except Exception as e:
        print(f"❌ ERROR eliminando usuario: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def menu_principal():
    """Menú principal interactivo"""
    while True:
        print("\n" + "="*60)
        print("🎛️  GESTOR DE USUARIOS - SISTEMA DE ASISTENCIA")
        print("="*60)
        
        # Mostrar usuarios
        usuarios = mostrar_todos_los_usuarios()
        
        if not usuarios:
            print("\n❌ No hay usuarios en el sistema")
            return
        
        print(f"\n🎛️  OPCIONES:")
        print(f"   • Escribe el ID del usuario a eliminar (ej: 5)")
        print(f"   • Escribe 'salir' para terminar")
        print(f"   • Escribe 'actualizar' para refrescar la lista")
        
        try:
            opcion = input(f"\n👤 ¿Qué usuario quieres eliminar? (ID): ").strip().lower()
            
            if opcion == 'salir':
                print("👋 ¡Hasta luego!")
                break
            elif opcion == 'actualizar':
                continue  # Vuelve al inicio del bucle
            
            # Intentar convertir a número
            try:
                id_usuario = int(opcion)
            except ValueError:
                print("❌ Por favor ingresa un ID válido (número) o 'salir'")
                continue
            
            # Verificar que el ID existe en la lista
            ids_disponibles = [u[0] for u in usuarios]
            if id_usuario not in ids_disponibles:
                print(f"❌ ID {id_usuario} no existe. IDs disponibles: {ids_disponibles}")
                continue
            
            # Buscar info del usuario seleccionado
            usuario_seleccionado = None
            for usuario in usuarios:
                if usuario[0] == id_usuario:
                    usuario_seleccionado = usuario
                    break
            
            if usuario_seleccionado:
                id_user, nombre, apellido, email, rol, fotos, asist_nuevas, asist_viejas = usuario_seleccionado
                nombre_completo = f"{nombre} {apellido}"
                total_asistencias = asist_nuevas + asist_viejas
                
                print(f"\n⚠️  CONFIRMACIÓN DE ELIMINACIÓN")
                print(f"="*40)
                print(f"ID: {id_user}")
                print(f"Nombre: {nombre_completo}")
                print(f"Email: {email or 'Sin email'}")
                print(f"Rol: {rol}")
                print(f"Fotos registradas: {fotos}")
                print(f"Asistencias registradas: {total_asistencias}")
                
                print(f"\n🚨 ESTA ACCIÓN NO SE PUEDE DESHACER")
                confirmacion = input(f"¿Estás SEGURO de eliminar a {nombre_completo}? (sí/no): ").strip().lower()
                
                if confirmacion in ['sí', 'si', 's', 'yes', 'y']:
                    print(f"\n🔄 Eliminando usuario...")
                    
                    if eliminar_usuario_por_id(id_usuario):
                        print(f"\n✅ ¡Usuario eliminado exitosamente!")
                        print(f"💡 Recuerda reiniciar la aplicación para que los cambios tomen efecto:")
                        print(f"   python main.py")
                        
                        continuar = input(f"\n¿Quieres eliminar otro usuario? (sí/no): ").strip().lower()
                        if continuar not in ['sí', 'si', 's', 'yes', 'y']:
                            break
                    else:
                        print(f"\n❌ Error eliminando usuario")
                else:
                    print(f"❌ Eliminación cancelada")
            
        except KeyboardInterrupt:
            print(f"\n\n👋 Operación cancelada por el usuario")
            break
        except Exception as e:
            print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    print("🚀 Iniciando Gestor de Usuarios...")
    try:
        menu_principal()
    except Exception as e:
        print(f"❌ Error fatal: {e}")
    finally:
        print(f"\n🔚 Programa terminado")