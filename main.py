import time
import threading
from datetime import datetime
import sys
import os

import cv2
import numpy as np
import face_recognition
from flask import Flask, render_template, Response, jsonify, request
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

# Agregar path y importar gestor académico
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from src.utils.gestor_academico_automatico import GestorAcademicoAutomatico

app = Flask(__name__)

# INSTANCIA GLOBAL DEL GESTOR ACADÉMICO
gestor_academico = GestorAcademicoAutomatico()

# 🔗 CONFIGURACIÓN POSTGRESQL (reemplaza el CSV)
DATABASE_URL = 'postgresql://postgres:camilomena@localhost:5432/prototipoPG_v2'

def get_db_session():
    """Crear sesión de base de datos"""
    engine = create_engine(DATABASE_URL)
    Session = sessionmaker(bind=engine)
    return Session()

# Variables globales para compartir información entre hilos
global_frame = None
camera_active = False
recognized_person = None
last_recognition_time = 0
recognition_cooldown = 2  # segundos entre reconocimientos del mismo alumno
camera_lock = threading.Lock()

# Variables para el modo de registro de usuarios
current_mode = "asistencia"  # "asistencia" o "registro"
captured_photos = []  # Lista para almacenar las 4 fotos capturadas
capture_count = 0  # Contador de fotos capturadas
registration_status = "idle"  # "idle", "capturing", "preview", "processing"
reload_embeddings = False  # Señal para recargar embeddings en el hilo principal

# 🧠 CARGAR ROSTROS DESDE POSTGRESQL (reemplaza load_face_encodings)
def load_face_encodings():
    """Cargar embeddings desde PostgreSQL en lugar de archivos"""
    print("🔄 Cargando rostros desde PostgreSQL...")
    
    db = get_db_session()
    try:
        # Consultar embeddings de estudiantes activos agrupados por usuario
        result = db.execute(text("""
            SELECT u.id_usuario, u.nombre, u.apellido, 
                   array_agg(e.embedding_vector ORDER BY e.quality_score DESC) as embeddings,
                   COUNT(e.embedding_vector) as num_embeddings
            FROM usuarios u 
            JOIN embeddings_faciales e ON u.id_usuario = e.id_usuario 
            WHERE u.rol = 'estudiante' AND u.estado = 'activo' AND e.activo = true
            GROUP BY u.id_usuario, u.nombre, u.apellido
        """)).fetchall()
        
        known_face_encodings = []
        valid_names = []
        
        for row in result:
            try:
                user_id = row[0]
                nombre = row[1]
                apellido = row[2] 
                embeddings_list = row[3]  # Array de embeddings
                num_embeddings = row[4]
                
                if embeddings_list and len(embeddings_list) > 0:
                    # Usar el primer embedding (mejor calidad por el ORDER BY)
                    embedding_bytes = embeddings_list[0]
                    embedding = np.frombuffer(embedding_bytes, dtype=np.float64)
                    
                    known_face_encodings.append(embedding)
                    valid_names.append(f"{nombre} {apellido}")
                    print(f"  ✅ Cargado: {nombre} {apellido} ({num_embeddings} fotos disponibles)")
                
            except Exception as e:
                print(f"  ❌ Error procesando {nombre}: {e}")
        
        print(f"✅ Total de usuarios únicos cargados: {len(valid_names)}")
        return known_face_encodings, valid_names
        
    except Exception as e:
        print(f"❌ Error cargando desde PostgreSQL: {e}")
        return [], []
    finally:
        db.close()

known_face_encodings, valid_names = load_face_encodings()

# 📝 REGISTRAR ASISTENCIA COMPLETAMENTE AUTOMÁTICA
def mark_attendance(name):
    """
    Sistema completamente automático:
    1. Detecta período académico actual
    2. Busca o crea sesión automáticamente  
    3. Habilita asistencia automáticamente
    4. Registra asistencia en el corte correcto
    """
    global last_recognition_time

    try:
        current_time = time.time()
        if current_time - last_recognition_time < recognition_cooldown:
            return False

        # Obtener información académica actual AUTOMÁTICAMENTE
        info_academica = gestor_academico.obtener_info_academica_completa()
        print(f"🎯 SISTEMA AUTOMÁTICO - Registrando en: {info_academica['descripcion_periodo']}")
        print(f"📅 Fecha: {info_academica['fecha_consultada']}")
        print(f"🗓️ Mes: {info_academica['nombre_mes']}")

        db = get_db_session()
        
        # Obtener datos del estudiante
        result = db.execute(text("""
            SELECT id_usuario FROM usuarios 
            WHERE CONCAT(nombre, ' ', apellido) = :name AND rol = 'estudiante'
        """), {"name": name}).fetchone()
        
        if not result:
            print(f"❌ Estudiante no encontrado: {name}")
            db.close()
            return False
        
        id_estudiante = result[0]
        print(f"👤 Estudiante encontrado: {name} (ID: {id_estudiante})")
        
        # PASO 1: Buscar sesión del día actual en el corte correcto
        sesion_activa = gestor_academico.obtener_sesion_activa_actual()
        
        if not sesion_activa:
            print("🔄 No hay sesión activa, creando sesión automática para el período actual...")
            
            # Crear sesión automática en el período correcto
            from datetime import datetime
            now = datetime.now()
            dias = ['lunes', 'martes', 'miércoles', 'jueves', 'viernes', 'sábado', 'domingo']
            dia_actual = dias[now.weekday()]
            
            # Crear sesión en sesiones_academicas (nueva tabla)
            crear_sesion_query = """
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
            
            # Calcular hora de fin (1 hora después)
            hora_fin = now.replace(hour=min(23, now.hour + 1))
            
            # Buscar último número de sesión para generar uno nuevo
            cursor = db.execute(text("""
                SELECT COALESCE(MAX(numero_sesion), 0) + 1 
                FROM sesiones_academicas 
                WHERE año = :año AND semestre = :semestre AND corte = :corte
            """), {
                "año": info_academica['año'],
                "semestre": info_academica['semestre'], 
                "corte": info_academica['corte']
            }).fetchone()
            
            numero_sesion = cursor[0] if cursor else 1
            
            # Ejecutar creación de sesión
            result_sesion = db.execute(text(crear_sesion_query), (
                info_academica['año'],           # año
                info_academica['semestre'],      # semestre
                info_academica['corte'],         # corte
                1,                              # id_curso (por defecto)
                numero_sesion,                  # numero_sesion
                f'Sesión Automática - {now.strftime("%d/%m/%Y")}',  # nombre_sesion
                f'Sesión creada automáticamente por reconocimiento facial',  # descripcion
                now.date(),                     # fecha_programada
                now.time(),                     # hora_inicio
                hora_fin.time(),               # hora_fin
                dia_actual,                    # dia_semana
                'Aula Reconocimiento Facial',  # aula
                'activa',                      # estado
                True,                          # asistencia_habilitada ¡AUTOMÁTICO!
                15,                            # tolerancia_minutos
                1.0,                           # duracion_horas
                'reconocimiento',              # tipo_clase
                now                            # creada_en
            ))
            
            id_sesion_nueva = result_sesion.fetchone()[0]
            db.commit()
            
            print(f"✅ Sesión automática creada: ID {id_sesion_nueva}")
            print(f"📚 Período: {info_academica['descripcion_periodo']}")
            print(f"🕐 Horario: {now.strftime('%H:%M')} - {hora_fin.strftime('%H:%M')}")
            
            id_sesion_para_asistencia = id_sesion_nueva
        else:
            print(f"✅ Sesión encontrada: {sesion_activa['nombre_sesion']}")
            id_sesion_para_asistencia = sesion_activa['id_sesion']
            
            # Si la sesión existe pero no está habilitada, habilitarla AUTOMÁTICAMENTE
            if not sesion_activa['asistencia_habilitada']:
                print("🔄 Habilitando asistencia automáticamente...")
                db.execute(text("""
                    UPDATE sesiones_academicas 
                    SET asistencia_habilitada = true,
                        estado = 'activa',
                        actualizada_en = CURRENT_TIMESTAMP
                    WHERE id_sesion = :id_sesion
                """), {"id_sesion": sesion_activa['id_sesion']})
                db.commit()
                print("✅ Asistencia habilitada automáticamente")
        
        # PASO 2: Verificar si ya registró asistencia
        verificar_asistencia = db.execute(text("""
            SELECT id_asistencia, estado, minutos_tardanza 
            FROM asistencias_academicas 
            WHERE id_sesion = :id_sesion AND id_estudiante = :id_estudiante
        """), {
            "id_sesion": id_sesion_para_asistencia,
            "id_estudiante": id_estudiante
        }).fetchone()
        
        if verificar_asistencia:
            print(f"⚠️ {name} ya registró asistencia como: {verificar_asistencia[1]}")
            last_recognition_time = current_time
            db.close()
            return True  # Ya registrado
        
        # PASO 3: Calcular estado (presente/tardanza) automáticamente
        from datetime import datetime
        ahora = datetime.now()
        
        # Obtener hora de inicio de la sesión
        sesion_info = db.execute(text("""
            SELECT hora_inicio, tolerancia_minutos 
            FROM sesiones_academicas 
            WHERE id_sesion = :id_sesion
        """), {"id_sesion": id_sesion_para_asistencia}).fetchone()
        
        if sesion_info:
            hora_inicio_sesion = datetime.combine(ahora.date(), sesion_info[0])
            tolerancia = sesion_info[1] or 15
        else:
            # Si no hay info, usar la hora actual como referencia
            hora_inicio_sesion = ahora
            tolerancia = 15
        
        diferencia_minutos = (ahora - hora_inicio_sesion).total_seconds() / 60
        
        if diferencia_minutos <= tolerancia:
            estado_asistencia = 'presente'
            minutos_tardanza = 0
            print(f"✅ Estado: PRESENTE (llegó {diferencia_minutos:.0f} min después del inicio)")
        else:
            estado_asistencia = 'tardanza'
            minutos_tardanza = int(diferencia_minutos - tolerancia)
            print(f"⏰ Estado: TARDANZA ({minutos_tardanza} min de retraso)")
        
        # PASO 4: Registrar asistencia AUTOMÁTICAMENTE
        db.execute(text("""
            INSERT INTO asistencias_academicas (
                id_sesion, id_estudiante, fecha_registro, metodo_registro,
                confidence_score, estado, minutos_tardanza
            ) VALUES (:id_sesion, :id_estudiante, :fecha_registro, :metodo_registro, 
                     :confidence_score, :estado, :minutos_tardanza)
        """), {
            "id_sesion": id_sesion_para_asistencia,
            "id_estudiante": id_estudiante,
            "fecha_registro": ahora,
            "metodo_registro": "reconocimiento_facial",
            "confidence_score": None,
            "estado": estado_asistencia,
            "minutos_tardanza": minutos_tardanza
        })
        
        db.commit()
        db.close()
        
        last_recognition_time = current_time
        
        # MENSAJE DE ÉXITO COMPLETO
        print("="*60)
        print(f"🎉 ¡ASISTENCIA REGISTRADA AUTOMÁTICAMENTE!")
        print(f"👤 Estudiante: {name}")
        print(f"📚 Período: {info_academica['descripcion_periodo']}")
        print(f"📅 Fecha: {ahora.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"✅ Estado: {estado_asistencia.upper()}")
        if minutos_tardanza > 0:
            print(f"⏰ Tardanza: {minutos_tardanza} minutos")
        print("="*60)
        
        return True
        
    except Exception as e:
        print(f"❌ Error en sistema automático: {str(e)}")
        if 'db' in locals():
            db.close()
        return False

def save_new_user(nombre, apellido, email, photos_data):
    """Guardar nuevo usuario con sus fotos y embeddings en la base de datos"""
    try:
        db = get_db_session()
        
        # 1. Insertar usuario
        # Generar email por defecto si no se proporciona
        if not email:
            email = f"{nombre.lower()}.{apellido.lower()}@estudiante.local"
        
        # Generar contraseña hash por defecto (se puede cambiar después)
        default_password_hash = "default_hash_changeme"
        
        result = db.execute(text("""
            INSERT INTO usuarios (nombre, apellido, correo, contrasena_hash, rol, estado)
            VALUES (:nombre, :apellido, :correo, :contrasena_hash, 'estudiante', 'activo')
            RETURNING id_usuario
        """), {
            "nombre": nombre,
            "apellido": apellido, 
            "correo": email,
            "contrasena_hash": default_password_hash
        })
        
        user_id = result.fetchone()[0]
        
        # 2. Procesar fotos y generar embeddings
        embeddings_saved = 0
        for i, photo_bytes in enumerate(photos_data):
            try:
                # Convertir bytes a numpy array (imagen)
                nparr = np.frombuffer(photo_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
                
                # Generar embedding
                face_locations = face_recognition.face_locations(rgb_image)
                print(f"  📸 Foto {i+1}: Encontradas {len(face_locations)} caras")
                
                if len(face_locations) > 0:
                    face_encodings = face_recognition.face_encodings(rgb_image, face_locations)
                    print(f"  🧠 Foto {i+1}: Generados {len(face_encodings)} embeddings")
                    
                    if len(face_encodings) > 0:
                        embedding = face_encodings[0]
                        embedding_bytes = embedding.tobytes()
                        
                        # Guardar embedding en BD
                        db.execute(text("""
                            INSERT INTO embeddings_faciales (id_usuario, embedding_vector, quality_score, detection_confidence, activo)
                            VALUES (:id_usuario, :embedding_vector, :quality_score, :detection_confidence, true)
                        """), {
                            "id_usuario": user_id,
                            "embedding_vector": embedding_bytes,
                            "quality_score": 0.85,  # Valor por defecto
                            "detection_confidence": 0.90  # Valor por defecto
                        })
                        
                        embeddings_saved += 1
                        print(f"✅ Embedding {i+1} guardado para {nombre} {apellido}")
                    else:
                        print(f"⚠️ Foto {i+1}: No se pudieron generar embeddings")
                else:
                    print(f"⚠️ Foto {i+1}: No se encontraron caras en la imagen")
                
            except Exception as e:
                print(f"❌ Error procesando foto {i+1}: {e}")
                # En caso de error, hacer rollback de la transacción
                if 'db' in locals():
                    db.rollback()
        
        if embeddings_saved > 0:
            db.commit()
            print(f"✅ Usuario {nombre} {apellido} registrado con {embeddings_saved} embeddings")
            
            # Señalar al hilo principal que recargue embeddings
            global reload_embeddings
            reload_embeddings = True
            print("📡 Señal de recarga enviada al hilo de reconocimiento")
            
            db.close()
            return True, f"Usuario registrado exitosamente con {embeddings_saved} fotos"
        else:
            db.rollback()
            db.close()
            return False, "No se pudo generar ningún embedding válido. Asegúrate de que las fotos muestren claramente el rostro."
            
    except Exception as e:
        print(f"❌ Error guardando usuario: {e}")
        if 'db' in locals():
            db.rollback()
            db.close()
        return False, f"Error: {str(e)}"

def release_camera():
    """Libera los recursos de la cámara si está activa."""
    global camera_active
    if camera_active:
        with camera_lock:
            camera_active = False
        print("Cámara liberada correctamente")
        time.sleep(1)  # Dar tiempo para que se libere completamente

def facial_recognition_thread():
    """Función que se ejecuta en un hilo separado para el reconocimiento facial."""
    global global_frame, recognized_person, camera_active, current_mode, captured_photos, capture_count, registration_status, reload_embeddings

    print("🎥 Iniciando hilo de reconocimiento facial...")
    
    # Cargar rostros conocidos
    known_face_encodings, valid_names = load_face_encodings()
    if len(known_face_encodings) == 0:
        print("❌ No hay rostros cargados para reconocer")
        return

    # Asegurar que la cámara está libre antes de intentar acceder
    release_camera()
    time.sleep(1)

    # Intentar diferentes índices de cámara si el primero falla
    camera_indexes = [0, 1, 2]  # Probar con la cámara 0, 1 y 2
    cap = None

    for idx in camera_indexes:
        try:
            print(f"🔍 Intentando abrir cámara con índice {idx}...")
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                print(f"✅ Cámara abierta correctamente con índice {idx}")
                break
        except Exception as e:
            print(f"❌ Error al abrir cámara {idx}: {e}")

    if cap is None or not cap.isOpened():
        print("❌ No se pudo abrir ninguna cámara")
        return

    with camera_lock:
        camera_active = True

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Parámetros de reconocimiento balanceados
    TOLERANCE = 0.45  # Tolerance original que funcionaba
    FRAME_SKIP = 4  # Procesar cada 4 frames
    CONFIDENCE_THRESHOLD = 0.55  # Confianza mínima más flexible
    frame_count = 0

    try:
        while camera_active:
            # Verificar si necesitamos recargar embeddings
            if reload_embeddings:
                print("🔄 Recargando embeddings por nuevo registro...")
                known_face_encodings, valid_names = load_face_encodings()
                reload_embeddings = False
                print(f"✅ Embeddings recargados: {len(valid_names)} usuarios disponibles")

            ret, frame = cap.read()
            if not ret:
                print("❌ Error al leer frame de la cámara")
                break

            # Crear una copia para mostrar
            display_frame = frame.copy()

            # Mostrar información del modo actual
            if current_mode == "registro":
                cv2.putText(display_frame, f"MODO REGISTRO - Fotos: {capture_count}/4", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 255), 2)
                
                # En modo registro, solo mostrar el frame sin procesar
                if registration_status == "capturing":
                    # Mostrar indicador de captura
                    cv2.putText(display_frame, "Presiona CAPTURAR cuando estes listo", 
                               (10, display_frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)
                elif registration_status == "preview":
                    cv2.putText(display_frame, "Revisa las fotos y confirma registro", 
                               (10, display_frame.shape[0] - 50), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (255, 255, 0), 2)
            else:
                # Modo asistencia normal - procesar reconocimiento
                cv2.putText(display_frame, "MODO ASISTENCIA", 
                           (10, 30), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)

            # Procesar cada X frames (solo en modo asistencia)
            frame_count += 1
            if frame_count % FRAME_SKIP == 0 and current_mode == "asistencia":
                # Redimensionar para mejor rendimiento
                small_frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)
                rgb_small_frame = cv2.cvtColor(small_frame, cv2.COLOR_BGR2RGB)

                # Encontrar rostros en el frame
                face_locations = face_recognition.face_locations(rgb_small_frame)
                face_encodings = face_recognition.face_encodings(rgb_small_frame, face_locations)
                


                for (top, right, bottom, left), face_encoding in zip(face_locations, face_encodings):
                    # Escalar de vuelta las coordenadas
                    top *= 2
                    right *= 2
                    bottom *= 2
                    left *= 2

                    # Comparar con rostros conocidos (TU LÓGICA EXACTA)
                    matches = face_recognition.compare_faces(known_face_encodings, face_encoding, TOLERANCE)
                    face_distances = face_recognition.face_distance(known_face_encodings, face_encoding)

                    if len(face_distances) > 0:
                        best_match_index = np.argmin(face_distances)
                        best_distance = face_distances[best_match_index]
                        confidence = 1 - best_distance
                        
                        if matches and matches[best_match_index]:
                            name = valid_names[best_match_index]
                            
                            # Solo procesar si la confianza es alta
                            if confidence >= CONFIDENCE_THRESHOLD:
                                # Dibujar rectángulo verde para reconocido con alta confianza
                                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                                cv2.putText(display_frame, f"{name} ({confidence:.2f})", 
                                           (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                                already_registered = mark_attendance(name)
                                status_text = "Ya registrado" if already_registered else "Registrado"
                                recognized_person = {
                                    'name': name, 'confidence': confidence, 'status': status_text}
                            else:
                                # Confianza baja - mostrar como "posible" pero no registrar
                                cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 165, 255), 2)  # Naranja
                                cv2.putText(display_frame, f"¿{name}? ({confidence:.2f})", 
                                           (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 165, 255), 2)
                                recognized_person = None
                        else:
                            # Dibujar rectángulo rojo para no reconocido
                            cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 0, 255), 2)
                            cv2.putText(display_frame, "No reconocido", (left, top - 10),
                                       cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 0, 255), 2)
                            recognized_person = None

            # Mostrar estado del sistema
            cv2.putText(display_frame, f"Referencias: {len(valid_names)} rostros",
                       (10, display_frame.shape[0] - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)

            # Actualizar el frame global
            ret, buffer = cv2.imencode('.jpg', display_frame)
            if ret:
                global_frame = buffer.tobytes()

            # Pequeña pausa para evitar consumo excesivo de CPU
            time.sleep(0.02)

    except Exception as e:
        print(f"❌ Error en el hilo de reconocimiento: {e}")
    finally:
        if cap is not None:
            cap.release()
            print("📹 Cámara liberada")
        with camera_lock:
            camera_active = False

# Estado inicial del hilo de reconocimiento
recognition_thread = None

def ensure_recognition_thread_running():
    """Asegura que el hilo de reconocimiento esté ejecutándose."""
    global recognition_thread, camera_active

    if recognition_thread is None or not recognition_thread.is_alive():
        with camera_lock:
            if camera_active:
                release_camera()

        recognition_thread = threading.Thread(target=facial_recognition_thread, daemon=True)
        recognition_thread.start()
        print("🚀 Hilo de reconocimiento iniciado")

def generate_frames():
    """Generador para streaming de video."""
    ensure_recognition_thread_running()

    fallback_image = None
    try:
        with open('static/waiting.jpg', 'rb') as f:
            fallback_image = f.read()
    except:
        # Si no hay imagen de fallback, crear una imagen negra
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        _, buffer = cv2.imencode('.jpg', blank)
        fallback_image = buffer.tobytes()

    while True:
        if global_frame is not None:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + global_frame + b'\r\n')
        else:
            yield (b'--frame\r\n'
                   b'Content-Type: image/jpeg\r\n\r\n' + fallback_image + b'\r\n')
        time.sleep(0.02)

# 🌐 RUTAS FLASK (TUS MISMAS RUTAS)
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_attendance')
def get_attendance():
    """Obtener asistencias desde la nueva tabla asistencias_academicas"""
    try:
        db = get_db_session()
        
        # Obtener información académica actual para mostrar contexto
        info_academica = gestor_academico.obtener_info_academica_completa()
        
        # Obtener asistencias de hoy de la nueva tabla
        today = datetime.now().date()
        result = db.execute(text("""
            SELECT 
                u.nombre, 
                u.apellido, 
                aa.fecha_registro, 
                aa.estado, 
                aa.minutos_tardanza,
                sa.nombre_sesion,
                sa.corte,
                sa.semestre
            FROM asistencias_academicas aa
            JOIN usuarios u ON aa.id_estudiante = u.id_usuario
            JOIN sesiones_academicas sa ON aa.id_sesion = sa.id_sesion
            WHERE DATE(aa.fecha_registro) = :today
            ORDER BY aa.fecha_registro DESC
        """), {"today": today}).fetchall()
        
        records = []
        for row in result:
            # Formatear estado con emoji
            estado_display = row[3]
            if row[3] == 'presente':
                estado_display = '✅ Presente'
            elif row[3] == 'tardanza':
                estado_display = f'⏰ Tardanza ({row[4]} min)'
            elif row[3] == 'ausente':
                estado_display = '❌ Ausente'
            
            records.append({
                'Nombre': f"{row[0]} {row[1]}",
                'Fecha': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else '',
                'Estado': estado_display,
                'Sesion': row[5] or 'Sin sesión',
                'Periodo': f"{row[7]} - Corte {row[6]}"
            })
        
        db.close()
        return jsonify(records)
    
    except Exception as e:
        print(f"❌ Error obteniendo asistencias: {e}")
        return jsonify([])

@app.route('/recognition_status')
def recognition_status():
    """Estado del reconocimiento con estadísticas actualizadas"""
    global recognized_person, camera_active
    
    # Obtener estadísticas de hoy
    try:
        db = get_db_session()
        today = datetime.now().date()
        
        # Contar asistencias de hoy
        asistencias_hoy = db.execute(text("""
            SELECT COUNT(*) FROM asistencias_academicas aa
            JOIN sesiones_academicas sa ON aa.id_sesion = sa.id_sesion
            WHERE DATE(aa.fecha_registro) = :today
        """), {"today": today}).fetchone()[0]
        
        # Contar total de estudiantes
        total_estudiantes = db.execute(text("""
            SELECT COUNT(*) FROM usuarios WHERE rol = 'estudiante'
        """)).fetchone()[0]
        
        # Obtener información académica actual
        info_academica = gestor_academico.obtener_info_academica_completa()
        
        db.close()
        
        return jsonify({
            'person': recognized_person,
            'camera_active': camera_active,
            'faces_loaded': len(valid_names),
            'asistencias_hoy': asistencias_hoy,
            'total_estudiantes': total_estudiantes,
            'periodo_academico': info_academica['descripcion_periodo'],
            'fecha_actual': info_academica['fecha_consultada']
        })
        
    except Exception as e:
        print(f"❌ Error obteniendo estadísticas: {e}")
        return jsonify({
            'person': recognized_person,
            'camera_active': camera_active,
            'faces_loaded': len(valid_names),
            'asistencias_hoy': 0,
            'total_estudiantes': 0,
            'periodo_academico': 'Error',
            'fecha_actual': 'Error'
        })

@app.route('/toggle_mode', methods=['POST'])
def toggle_mode():
    """Cambiar entre modo asistencia y registro"""
    global current_mode, captured_photos, capture_count, registration_status
    
    data = request.get_json()
    new_mode = data.get('mode', 'asistencia')
    
    if new_mode in ['asistencia', 'registro']:
        current_mode = new_mode
        
        # Limpiar estado si cambia a modo registro
        if new_mode == "registro":
            captured_photos = []
            capture_count = 0
            registration_status = "capturing"
        else:
            registration_status = "idle"
        
        return jsonify({
            'success': True, 
            'current_mode': current_mode,
            'message': f'Cambiado a modo {new_mode}'
        })
    else:
        return jsonify({'success': False, 'message': 'Modo inválido'})

@app.route('/capture_photo', methods=['POST'])
def capture_photo():
    """Capturar una foto del frame actual para registro"""
    global global_frame, captured_photos, capture_count, registration_status
    
    if current_mode != "registro":
        return jsonify({'success': False, 'message': 'No estás en modo registro'})
    
    if capture_count >= 4:
        return jsonify({'success': False, 'message': 'Ya capturaste 4 fotos'})
    
    if global_frame is None:
        return jsonify({'success': False, 'message': 'No hay frame disponible'})
    
    try:
        # Guardar el frame actual
        captured_photos.append(global_frame)
        capture_count += 1
        
        # Si ya tenemos 4 fotos, cambiar a modo preview
        if capture_count >= 4:
            registration_status = "preview"
        
        return jsonify({
            'success': True, 
            'capture_count': capture_count,
            'total_needed': 4,
            'status': registration_status,
            'message': f'Foto {capture_count}/4 capturada'
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/get_captured_photos')
def get_captured_photos():
    """Obtener las fotos capturadas para preview"""
    global captured_photos, capture_count
    
    try:
        # Convertir cada foto a base64 para enviar al frontend
        import base64
        photos_b64 = []
        
        for photo_bytes in captured_photos:
            b64_string = base64.b64encode(photo_bytes).decode('utf-8')
            photos_b64.append(f"data:image/jpeg;base64,{b64_string}")
        
        return jsonify({
            'success': True,
            'photos': photos_b64,
            'count': capture_count
        })
    
    except Exception as e:
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@app.route('/save_user', methods=['POST'])
def save_user():
    """Guardar nuevo usuario con sus fotos"""
    global captured_photos, current_mode, capture_count, registration_status
    
    if current_mode != "registro":
        return jsonify({'success': False, 'message': 'No estás en modo registro'})
    
    if len(captured_photos) != 4:
        return jsonify({'success': False, 'message': 'Necesitas exactamente 4 fotos'})
    
    try:
        data = request.get_json()
        nombre = data.get('nombre', '').strip()
        apellido = data.get('apellido', '').strip()
        email = data.get('email', '').strip()
        
        # Validaciones básicas
        if not nombre or not apellido:
            return jsonify({'success': False, 'message': 'Nombre y apellido son requeridos'})
        
        if email and '@' not in email:
            return jsonify({'success': False, 'message': 'Email inválido'})
        
        registration_status = "processing"
        
        # Guardar usuario
        success, message = save_new_user(nombre, apellido, email, captured_photos)
        
        if success:
            # Limpiar estado y volver a modo asistencia
            captured_photos = []
            capture_count = 0
            current_mode = "asistencia"
            registration_status = "idle"
            
            return jsonify({
                'success': True, 
                'message': message,
                'redirect': True
            })
        else:
            registration_status = "preview"  # Volver a preview para reintentar
            return jsonify({'success': False, 'message': message})
    
    except Exception as e:
        registration_status = "preview"
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

# 🎯 NUEVAS RUTAS DEL SISTEMA ACADÉMICO AUTOMÁTICO

@app.route('/get_session_info')
def get_session_info():
    """
    Obtiene información de la sesión actual para mostrar en la interfaz
    """
    try:
        info_academica = gestor_academico.obtener_info_academica_completa()
        sesion_activa = gestor_academico.obtener_sesion_activa_actual()
        
        return jsonify({
            'success': True,
            'periodo_academico': info_academica['descripcion_periodo'],
            'fecha_actual': info_academica['fecha_consultada'],
            'mes_actual': info_academica['nombre_mes'],
            'sesion_activa': sesion_activa is not None,
            'info_sesion': sesion_activa if sesion_activa else None
        })
    except Exception as e:
        print(f"❌ Error obteniendo info de sesión: {e}")
        return jsonify({'success': False, 'message': str(e)})

@app.route('/toggle_asistencia', methods=['GET', 'POST'])
def toggle_asistencia():
    """
    Habilita o deshabilita la asistencia para la sesión actual
    """
    try:
        resultado = gestor_academico.habilitar_asistencia_automatica()
        
        return jsonify({
            'success': resultado['exito'],
            'message': resultado['mensaje'],
            'session_info': resultado.get('sesion', {})
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/estadisticas_corte')
def estadisticas_corte():
    """
    Obtiene estadísticas del corte académico actual
    """
    try:
        stats = gestor_academico.obtener_estadisticas_corte_actual()
        
        return jsonify({
            'success': True,
            'estadisticas': stats
        })
        
    except Exception as e:
        return jsonify({
            'success': False,
            'message': f'Error: {str(e)}'
        })

@app.route('/reset_registration', methods=['POST'])
def reset_registration():
    """Reiniciar el proceso de registro"""
    global captured_photos, capture_count, registration_status
    
    captured_photos = []
    capture_count = 0 
    registration_status = "capturing"
    
    return jsonify({'success': True, 'message': 'Registro reiniciado'})

if __name__ == '__main__':
    print("🚀 === TU SISTEMA DE RECONOCIMIENTO FACIAL + POSTGRESQL ===")
    print("📊 Cargando rostros desde PostgreSQL...")
    print("🌐 Iniciando servidor Flask...")
    print("📹 Accede a: http://192.168.18.10:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)