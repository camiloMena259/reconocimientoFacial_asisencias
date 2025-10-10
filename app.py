import os
import time
import threading
from datetime import datetime

import cv2
import numpy as np
import pandas as pd
import face_recognition
from flask import Flask, render_template, Response, jsonify

app = Flask(__name__)

# Configuración de archivo de asistenciaa
ATTENDANCE_FILE = os.path.join(os.path.dirname(__file__), "attendance.csv")
ATTENDANCE_COLUMNS = ["Nombre", "Fecha"]

def ensure_attendance_file():
    """Asegura que el archivo attendance.csv existe y tiene la estructura correcta"""
    if not os.path.exists(ATTENDANCE_FILE):
        pd.DataFrame(columns=ATTENDANCE_COLUMNS).to_csv(ATTENDANCE_FILE, index=False)
        return
    try:
        pd.read_csv(ATTENDANCE_FILE, nrows=1)
    except (pd.errors.EmptyDataError, pd.errors.ParserError):
        pd.DataFrame(columns=ATTENDANCE_COLUMNS).to_csv(ATTENDANCE_FILE, index=False)

def load_attendance():
    """Carga el archivo de asistencia de forma segura"""
    ensure_attendance_file()
    return pd.read_csv(ATTENDANCE_FILE)

def save_attendance(df):
    """Guarda el DataFrame de asistencia de forma segura"""
    df.to_csv(ATTENDANCE_FILE, index=False)

# Variables globales para compartir información entre hilos
global_frame = None
camera_active = False
recognized_person = None
last_recognition_time = 0
recognition_cooldown = 2  # segundos entre reconocimientos del mismo alumno
camera_lock = threading.Lock()

# Carpeta donde están las imágenes de los alumnos
# Usar rutas relativas al proyecto para portabilidad
project_root = os.path.dirname(os.path.abspath(__file__))
image_folder = os.path.join(project_root, 'students')
attendance_file = os.path.join(project_root, 'attendance.csv')

# Inicializar DataFrame de asistencia y asegurar archivo
ensure_attendance_file()
attendance_df = load_attendance()

# Cargar rostros conocidos
def load_face_encodings():
    print("Cargando imágenes de referencia...")
    # Si la carpeta students no existe, crearla (el usuario agregó imágenes allí)
    if not os.path.exists(image_folder):
        print(f"La carpeta de imágenes no existe: {image_folder}. Creando carpeta.")
        os.makedirs(image_folder, exist_ok=True)

    images = [os.path.join(image_folder, f) for f in os.listdir(image_folder)
              if f.lower().endswith((".jpg", ".jpeg", ".png"))]
    student_names = [os.path.splitext(os.path.basename(img))[0] for img in images]

    known_face_encodings = []
    valid_names = []

    for img_path, name in zip(images, student_names):
        try:
            image = face_recognition.load_image_file(img_path)
            face_encodings = face_recognition.face_encodings(image)
            if face_encodings:
                known_face_encodings.append(face_encodings[0])
                valid_names.append(name)
                print(f"  Cargado: {name}")
            else:
                print(f" X No se detectó rostro en: {name}")
        except Exception as e:
            print(f" X Error al procesar {name}: {e}")
    
    print(f"Total de rostros cargados: {len(valid_names)}")
    return known_face_encodings, valid_names

known_face_encodings, valid_names = load_face_encodings()

def mark_attendance(name):
    """Registra la asistencia en el archivo CSV y actualiza el DataFrame global"""
    global attendance_df, last_recognition_time

    try:
        current_time = time.time()
        if current_time - last_recognition_time < recognition_cooldown:
            return False

        now = datetime.now()
        today_date = now.strftime('%Y-%m-%d')
        dt_string = now.strftime('%Y-%m-%d %H:%M:%S')

        # Verificar si el usuario ya está registrado hoy usando el DataFrame en memoria
        if ((attendance_df["Nombre"] == name) & (attendance_df['Fecha'].str.startswith(today_date))).any():
            last_recognition_time = current_time
            return True  # Ya registrado

        # Añadir directamente al CSV (modo append) y actualizar DataFrame en memoria
        with open(ATTENDANCE_FILE, 'a', encoding='utf-8') as f:
            f.write(f"\n{name},{dt_string}")
        
        new_entry = pd.DataFrame([[name, dt_string]], columns=['Nombre', 'Fecha'])
        attendance_df = pd.concat([attendance_df, new_entry], ignore_index=True)
        
        last_recognition_time = current_time
        print(f"✓ Asistencia registrada: {name} - {dt_string}")
        return False  # Nuevo registro
    except Exception as e:
        print(f"Error al marcar asistencia: {str(e)}")
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

    print("Iniciando hilo de reconocimiento facial...")

    # Asegurar que la cámara está libre antes de intentar acceder
    release_camera()
    time.sleep(1)

    # Intentar diferentes índices de cámara si el primero falla
    camera_indexes = [0, 1, 2]  # Probar con la cámara 0, 1 y 2
    cap = None

    for idx in camera_indexes:
        try:
            print(f"Intentando abrir cámara con índice {idx}...")
            cap = cv2.VideoCapture(idx)
            if cap.isOpened():
                print(f" Cámara abierta correctamente con índice {idx}")
                break
        except Exception as e:
            print(f"Error al abrir cámara {idx}: {e}")

    if cap is None or not cap.isOpened():
        print("X No se pudo abrir ninguna cámara")
        return

    with camera_lock:
        camera_active = True

    cap.set(cv2.CAP_PROP_FRAME_WIDTH, 640)
    cap.set(cv2.CAP_PROP_FRAME_HEIGHT, 480)

    # Parámetros de reconocimiento
    TOLERANCE = 0.45  # Valor más bajo = más estricto
    FRAME_SKIP = 3  # Procesar cada X frames para mejor rendimiento
    frame_count = 0

    try:
        while camera_active:
            ret, frame = cap.read()
            if not ret:
                print("Error al leer frame de la cámara")
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

                    # Comparar con rostros conocidos
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
        print(f"Error en el hilo de reconocimiento: {e}")
    finally:
        if cap is not None:
            cap.release()
            print("Cámara liberada")
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
        print("Hilo de reconocimiento iniciado")

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
        time.sleep(0.033)  # ~30 FPS

@app.route('/')
def index():
    """Página principal."""
    ensure_recognition_thread_running()
    return render_template('index.html')

@app.route('/video_feed')
def video_feed():
    """Endpoint para el streaming de video."""
    return Response(generate_frames(),
                   mimetype='multipart/x-mixed-replace; boundary=frame')

@app.route('/get_attendance')
def get_attendance():
    """Endpoint para obtener los datos de asistencia."""
    # Ordenar por fecha más reciente
    sorted_df = attendance_df.sort_values('Fecha', ascending=False)
    attendance_data = sorted_df.to_dict('records')
    return jsonify(attendance_data)

@app.route('/recognition_status')
def recognition_status():
    """Endpoint para obtener el estado del reconocimiento actual."""
    return jsonify(recognized_person if recognized_person else {})

@app.route('/restart_camera')
def restart_camera():
    """Endpoint para reiniciar la cámara."""
    global recognition_thread, camera_active

    try:
        if recognition_thread and recognition_thread.is_alive():
            with camera_lock:
                camera_active = False
            time.sleep(2)  # Esperar a que el hilo termine

        ensure_recognition_thread_running()
        return jsonify({"status": "success", "message": "Cámara reiniciada correctamente"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)})

if __name__ == '__main__':
    # Asegúrate de que exista el directorio static
    if not os.path.exists('static'):
        os.makedirs('static')

    # Crear imagen de espera si no existe
    if not os.path.exists('static/waiting.jpg'):
        blank = np.zeros((480, 640, 3), dtype=np.uint8)
        cv2.putText(blank, "Iniciando camara...", (180, 240),
                   cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 255, 255), 2)
        cv2.imwrite('static/waiting.jpg', blank)

    print("Iniciando servidor web...")
    app.run(debug=False, host='0.0.0.0', port=5000, threaded=True)