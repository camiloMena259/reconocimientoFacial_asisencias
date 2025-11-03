"""
Limpiar cualquier usuario del sistema de forma interactiva
"""

import psycopg2
import os
import glob
from datetime import datetime

# Configuración de la base de datos
DATABASE_CONFIG = {
    'host': 'localhost',
    'database': 'prototipoPG_v2',
    'user': 'postgres',
    'password': 'camilomena',
    'port': '5432'
}

def mostrar_usuarios_disponibles():
    """Mostrar todos los usuarios del sistema"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    cursor = conn.cursor()
    
    try:
        cursor.execute("""
            SELECT u.id_usuario, u.nombre, u.apellido, u.rol,
                   COUNT(e.embedding_vector) as num_embeddings,
                   COUNT(aa.id_asistencia) as num_asistencias
            FROM usuarios u
            LEFT JOIN embeddings_faciales e ON u.id_usuario = e.id_usuario
            LEFT JOIN asistencias_academicas aa ON u.id_usuario = aa.id_estudiante
            GROUP BY u.id_usuario, u.nombre, u.apellido, u.rol
            ORDER BY u.rol, u.nombre
        """)
        
        usuarios = cursor.fetchall()
        
        print(f"👥 USUARIOS EN EL SISTEMA ({len(usuarios)} total):")
        print("="*60)
        
        for i, usuario in enumerate(usuarios, 1):
            id_usuario, nombre, apellido, rol, embeddings, asistencias = usuario
            nombre_completo = f"{nombre} {apellido}"
            
            # Iconos según el rol
            icon = "👨‍🎓" if rol == "estudiante" else "👨‍🏫" if rol == "profesor" else "👤"
            
            print(f"{i:2d}. {icon} {nombre_completo}")
            print(f"     ID: {id_usuario} | Rol: {rol}")
            print(f"     📸 Fotos: {embeddings} | ✅ Asistencias: {asistencias}")
        
        return usuarios
        
    except Exception as e:
        print(f"❌ Error: {e}")
        return []
    finally:
        cursor.close()
        conn.close()

def verificar_tabla_existe(cursor, nombre_tabla):
    """Verificar si una tabla existe en la base de datos"""
    try:
        cursor.execute("""
            SELECT EXISTS (
                SELECT FROM information_schema.tables 
                WHERE table_schema = 'public' 
                AND table_name = %s
            );
        """, (nombre_tabla,))
        return cursor.fetchone()[0]
    except Exception:
        return False

def limpiar_usuario_por_id(id_usuario):
    """Limpiar usuario por ID"""
    conn = psycopg2.connect(**DATABASE_CONFIG)
    conn.autocommit = False  # Asegurar transacciones manuales
    cursor = conn.cursor()
    
    try:
        # Obtener info del usuario
        cursor.execute("SELECT nombre, apellido, rol FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        usuario_info = cursor.fetchone()
        
        if not usuario_info:
            print(f"❌ Usuario con ID {id_usuario} no encontrado")
            return False
        
        nombre, apellido, rol = usuario_info
        nombre_completo = f"{nombre} {apellido}"
        
        print(f"\n🗑️ ELIMINANDO USUARIO: {nombre_completo} (ID: {id_usuario})")
        print("-"*50)
        
        # Eliminar en orden correcto para evitar errores de FK
        
        # 1. Asistencias académicas
        if verificar_tabla_existe(cursor, 'asistencias_academicas'):
            cursor.execute("DELETE FROM asistencias_academicas WHERE id_estudiante = %s", (id_usuario,))
            deleted_asistencias_acad = cursor.rowcount
            print(f"✅ Asistencias académicas: {deleted_asistencias_acad}")
        else:
            print(f"ℹ️  Asistencias académicas: Tabla no existe")
        
        # 2. Asistencias antiguas
        if verificar_tabla_existe(cursor, 'asistencias'):
            cursor.execute("DELETE FROM asistencias WHERE id_estudiante = %s", (id_usuario,))
            deleted_asistencias = cursor.rowcount
            print(f"✅ Asistencias antiguas: {deleted_asistencias}")
        else:
            print(f"ℹ️  Asistencias antiguas: Tabla no existe (ya migrado)")
        
        # 3. Inscripciones
        if verificar_tabla_existe(cursor, 'inscripciones'):
            cursor.execute("DELETE FROM inscripciones WHERE id_estudiante = %s", (id_usuario,))
            deleted_inscripciones = cursor.rowcount
            print(f"✅ Inscripciones: {deleted_inscripciones}")
        else:
            print(f"ℹ️  Inscripciones: Tabla no existe")
        
        # 4. Embeddings faciales
        cursor.execute("DELETE FROM embeddings_faciales WHERE id_usuario = %s", (id_usuario,))
        deleted_embeddings = cursor.rowcount
        print(f"✅ Embeddings faciales: {deleted_embeddings}")
        
        # 5. Usuario
        cursor.execute("DELETE FROM usuarios WHERE id_usuario = %s", (id_usuario,))
        deleted_usuario = cursor.rowcount
        print(f"✅ Usuario: {deleted_usuario}")
        
        # 6. Buscar y eliminar archivos locales
        print(f"\n🔍 Buscando archivos locales...")
        archivos_eliminados = eliminar_archivos_usuario(nombre_completo)
        print(f"✅ Archivos eliminados: {archivos_eliminados}")
        
        conn.commit()
        
        print(f"\n🎉 Usuario '{nombre_completo}' eliminado completamente")
        return True
        
    except Exception as e:
        print(f"❌ Error eliminando usuario: {e}")
        conn.rollback()
        return False
    finally:
        cursor.close()
        conn.close()

def eliminar_archivos_usuario(nombre_completo):
    """Eliminar archivos locales del usuario"""
    archivos_eliminados = 0
    
    carpetas_busqueda = ["students", "fotos", "images", "photos", "rostros", "faces"]
    
    # Crear variaciones del nombre para buscar
    variaciones = [
        nombre_completo.lower(),
        nombre_completo.replace(' ', '_'),
        nombre_completo.replace(' ', ''),
        nombre_completo.split()[0].lower(),  # Solo el nombre
        nombre_completo.split()[-1].lower() if len(nombre_completo.split()) > 1 else ""  # Solo el apellido
    ]
    
    for carpeta in carpetas_busqueda:
        if os.path.exists(carpeta):
            for variacion in variaciones:
                if variacion:  # Si no está vacío
                    patrones = [
                        f"{carpeta}/*{variacion}*",
                        f"{carpeta}/{variacion}/*",
                        f"{carpeta}/*/{variacion}*"
                    ]
                    
                    for patron in patrones:
                        try:
                            archivos = glob.glob(patron)
                            for archivo in archivos:
                                try:
                                    if os.path.isfile(archivo):
                                        os.remove(archivo)
                                        archivos_eliminados += 1
                                    elif os.path.isdir(archivo):
                                        # Eliminar contenido de la carpeta primero
                                        for root, dirs, files in os.walk(archivo, topdown=False):
                                            for file in files:
                                                os.remove(os.path.join(root, file))
                                            for dir in dirs:
                                                os.rmdir(os.path.join(root, dir))
                                        os.rmdir(archivo)
                                        archivos_eliminados += 1
                                except Exception as e:
                                    print(f"   ⚠️ Error eliminando {archivo}: {e}")
                        except Exception:
                            pass  # Continuar si el patrón falla
    
    return archivos_eliminados

def main():
    """Función principal interactiva"""
    print("🧹 LIMPIADOR DE USUARIOS - SISTEMA DE ASISTENCIA")
    print("="*60)
    
    # Mostrar usuarios disponibles
    usuarios = mostrar_usuarios_disponibles()
    
    if not usuarios:
        print("❌ No se encontraron usuarios en el sistema")
        return
    
    print(f"\n" + "="*60)
    print("OPCIONES:")
    print("• Escribe el NÚMERO del usuario a eliminar")
    print("• Escribe 'salir' para cancelar")
    print("• Escribe 'todos' para ver todos de nuevo")
    
    while True:
        try:
            opcion = input(f"\n👤 ¿Qué usuario quieres eliminar? (1-{len(usuarios)}): ").strip().lower()
            
            if opcion == 'salir':
                print("👋 Operación cancelada")
                break
            elif opcion == 'todos':
                usuarios = mostrar_usuarios_disponibles()
                continue
            
            # Convertir a número
            numero = int(opcion)
            
            if 1 <= numero <= len(usuarios):
                usuario_seleccionado = usuarios[numero - 1]
                id_usuario, nombre, apellido, rol, embeddings, asistencias = usuario_seleccionado
                nombre_completo = f"{nombre} {apellido}"
                
                # Confirmación
                print(f"\n⚠️ CONFIRMACIÓN:")
                print(f"   Usuario: {nombre_completo}")
                print(f"   ID: {id_usuario}")
                print(f"   Rol: {rol}")
                print(f"   Fotos: {embeddings}")
                print(f"   Asistencias: {asistencias}")
                
                confirmacion = input(f"\n¿Estás SEGURO de eliminar este usuario? (sí/no): ").strip().lower()
                
                if confirmacion in ['sí', 'si', 's', 'yes', 'y']:
                    if limpiar_usuario_por_id(id_usuario):
                        print(f"\n✅ ¡Usuario eliminado exitosamente!")
                        print(f"💡 Recuerda reiniciar la aplicación: python main.py")
                    else:
                        print(f"\n❌ Error eliminando usuario")
                else:
                    print(f"❌ Eliminación cancelada")
                
                break
            else:
                print(f"❌ Número inválido. Debe ser entre 1 y {len(usuarios)}")
                
        except ValueError:
            print(f"❌ Por favor ingresa un número válido")
        except KeyboardInterrupt:
            print(f"\n👋 Operación cancelada")
            break

if __name__ == "__main__":
    main()