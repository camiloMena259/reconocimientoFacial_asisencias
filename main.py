import os
import time
import threading
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
import face_recognition
from flask import Flask, render_template, Response, jsonify
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

app = Flask(__name__)

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

# 🧠 CARGAR ROSTROS DESDE POSTGRESQL (reemplaza load_face_encodings)
def load_face_encodings():
    """Cargar embeddings desde PostgreSQL en lugar de archivos"""
    print("🔄 Cargando rostros desde PostgreSQL...")
    
    db = get_db_session()
    try:
        # Consultar embeddings de estudiantes activos
        result = db.execute(text("""
            SELECT u.nombre, u.apellido, e.embedding_vector 
            FROM usuarios u 
            JOIN embeddings_faciales e ON u.id_usuario = e.id_usuario 
            WHERE u.rol = 'estudiante' AND u.estado = 'activo' AND e.activo = 'true'
        """)).fetchall()
        
        known_face_encodings = []
        valid_names = []
        
        for row in result:
            try:
                nombre = row[0]
                apellido = row[1] 
                embedding_bytes = row[2]
                
                # Convertir bytes a numpy array
                embedding = np.frombuffer(embedding_bytes, dtype=np.float64)
                
                known_face_encodings.append(embedding)
                valid_names.append(f"{nombre} {apellido}")
                print(f"  ✅ Cargado: {nombre} {apellido}")
                
            except Exception as e:
                print(f"  ❌ Error procesando {nombre}: {e}")
        
        print(f"✅ Total de rostros cargados: {len(valid_names)}")
        return known_face_encodings, valid_names
        
    except Exception as e:
        print(f"❌ Error cargando desde PostgreSQL: {e}")
        return [], []
    finally:
        db.close()

known_face_encodings, valid_names = load_face_encodings()

# 📝 REGISTRAR ASISTENCIA EN POSTGRESQL (reemplaza mark_attendance)
def mark_attendance(name):
    """Registra la asistencia en PostgreSQL en lugar de CSV"""
    global last_recognition_time

    try:
        current_time = time.time()
        if current_time - last_recognition_time < recognition_cooldown:
            return False

        db = get_db_session()
        
        # Obtener datos del estudiante
        result = db.execute(text("""
            SELECT id_usuario FROM usuarios 
            WHERE CONCAT(nombre, ' ', apellido) = :name AND rol = 'estudiante'
        """), {"name": name}).fetchone()
        
        if not result:
            print(f"❌ Estudiante no encontrado: {name}")
            return False
        
        id_estudiante = result[0]
        
        # Verificar si ya registró hoy
        today = datetime.now().date()
        existing = db.execute(text("""
            SELECT id_asistencia FROM asistencias 
            WHERE id_estudiante = :id_estudiante 
            AND DATE(fecha_registro) = :today
        """), {"id_estudiante": id_estudiante, "today": today}).fetchone()
        
        if existing:
            print(f"⚠ {name} ya registró asistencia hoy")
            last_recognition_time = current_time
            return True  # Ya registrado
        
        # Obtener o crear sesión activa
        result = db.execute(text("""
            SELECT id_sesion FROM sesiones 
            WHERE activa = true 
            ORDER BY fecha_programada DESC 
            LIMIT 1
        """)).fetchone()
        
        if not result:
            # Crear sesión automática
            db.execute(text("""
                INSERT INTO sesiones (id_curso, nombre, descripcion, fecha_programada, tipo, activa)
                VALUES (1, 'Sesión Automática', 'Reconocimiento facial', :fecha, 'clase', true)
            """), {"fecha": datetime.now()})
            db.commit()
            
            result = db.execute(text("""
                SELECT id_sesion FROM sesiones ORDER BY id_sesion DESC LIMIT 1
            """)).fetchone()
        
        id_sesion = result[0]
        
        # Registrar asistencia
        db.execute(text("""
            INSERT INTO asistencias (id_estudiante, id_sesion, fecha_registro, metodo_registro, estado)
            VALUES (:id_estudiante, :id_sesion, :fecha_registro, :metodo_registro, :estado)
        """), {
            "id_estudiante": id_estudiante,
            "id_sesion": id_sesion, 
            "fecha_registro": datetime.now(),
            "metodo_registro": "reconocimiento_facial",
            "estado": "presente"
        })
        
        db.commit()
        db.close()
        
        last_recognition_time = current_time
        print(f"✅ Asistencia registrada: {name} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        return False  # Nuevo registro
        
    except Exception as e:
        print(f"❌ Error al marcar asistencia: {str(e)}")
        return False

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
    global global_frame, recognized_person, camera_active

    print("🎥 Iniciando hilo de reconocimiento facial...")

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

    # Parámetros de reconocimiento (TUS MISMOS VALORES)
    TOLERANCE = 0.45  # Valor más bajo = más estricto
    FRAME_SKIP = 3  # Procesar cada X frames para mejor rendimiento
    frame_count = 0

    try:
        while camera_active:
            ret, frame = cap.read()
            if not ret:
                print("❌ Error al leer frame de la cámara")
                break

            # Crear una copia para mostrar
            display_frame = frame.copy()

            # Procesar cada X frames
            frame_count += 1
            if frame_count % FRAME_SKIP == 0:
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

                        if matches and matches[best_match_index]:
                            name = valid_names[best_match_index]
                            # Dibujar rectángulo verde para reconocido
                            cv2.rectangle(display_frame, (left, top), (right, bottom), (0, 255, 0), 2)
                            confidence = 1 - best_distance
                            cv2.putText(display_frame, f"{name} ({confidence:.2f})", 
                                       (left, top - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.6, (0, 255, 0), 2)

                            already_registered = mark_attendance(name)
                            status_text = "Ya registrado" if already_registered else "Registrado"
                            recognized_person = {
                                'name': name, 'confidence': confidence, 'status': status_text}
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
    """Obtener asistencias desde PostgreSQL (reemplaza CSV)"""
    try:
        db = get_db_session()
        
        # Obtener asistencias de hoy
        today = datetime.now().date()
        result = db.execute(text("""
            SELECT u.nombre, u.apellido, a.fecha_registro, a.estado
            FROM asistencias a
            JOIN usuarios u ON a.id_estudiante = u.id_usuario
            WHERE DATE(a.fecha_registro) = :today
            ORDER BY a.fecha_registro DESC
        """), {"today": today}).fetchall()
        
        records = []
        for row in result:
            records.append({
                'Nombre': f"{row[0]} {row[1]}",
                'Fecha': row[2].strftime('%Y-%m-%d %H:%M:%S') if row[2] else '',
                'Estado': row[3]
            })
        
        db.close()
        return jsonify(records)
    
    except Exception as e:
        print(f"❌ Error obteniendo asistencias: {e}")
        return jsonify([])

@app.route('/recognition_status')
def recognition_status():
    """Estado del reconocimiento"""
    global recognized_person, camera_active
    return jsonify({
        'person': recognized_person,
        'camera_active': camera_active,
        'faces_loaded': len(valid_names)
    })

@app.route('/reload_faces')
def reload_faces():
    """Recargar rostros desde PostgreSQL"""
    global known_face_encodings, valid_names
    try:
        known_face_encodings, valid_names = load_face_encodings()
        return jsonify({
            'status': 'success',
            'message': f'Rostros recargados desde PostgreSQL. Total: {len(valid_names)}'
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Error recargando rostros: {str(e)}'
        })

if __name__ == '__main__':
    print("🚀 === TU SISTEMA DE RECONOCIMIENTO FACIAL + POSTGRESQL ===")
    print("📊 Cargando rostros desde PostgreSQL...")
    print("🌐 Iniciando servidor Flask...")
    print("📹 Accede a: http://192.168.18.10:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)