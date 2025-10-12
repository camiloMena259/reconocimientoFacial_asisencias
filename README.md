# 🎯 Sistema de Asistencias con Reconocimiento Facial v2.0

Sistema profesional de asistencias con reconocimiento facial utilizando PostgreSQL y Flask.

## 🏗️ Arquitectura del Proyecto

```
facial-attendance-system/
├── 📁 app/                          # Aplicación principal
│   ├── 📁 core/                     # Lógica de negocio
│   │   ├── config.py                # Configuraciones centralizadas
│   │   └── face_recognition.py      # Lógica de reconocimiento facial
│   │
│   ├── 📁 database/                 # Gestión de base de datos
│   │   ├── connection.py            # Conexión PostgreSQL
│   │   └── migrations/              # Scripts de migración
│   │       └── schema.sql           # Esquema de base de datos
│   │
│   ├── 📁 services/                 # Servicios de aplicación
│   │   ├── attendance_service.py    # Gestión de asistencias
│   │   └── camera_service.py        # Gestión de cámara y streaming
│   │
│   └── 📁 web/                      # Interfaz web
│       ├── routes.py                # Rutas Flask
│       └── templates/               # Plantillas HTML
│
├── 📁 scripts/                      # Scripts de utilidad
│   ├── verify_system.py             # Verificación del sistema
│   └── cleanup_project.py           # Limpieza de archivos obsoletos
│
├── 📁 students/                     # 📸 Fotos de estudiantes
├── 📁 static/                       # 🎨 CSS y JavaScript  
├── 📁 data/                         # 📊 Datos del proyecto
├── 📁 docs/                         # 📚 Documentación
├── 📁 config/                       # ⚙️ Archivos de configuración
│
├── main.py                          # 🚀 Punto de entrada principal
├── environment.yml                  # 📦 Dependencias del proyecto
└── README.md                        # 📖 Este archivo
```

## 🚀 Inicio Rápido

### 1. Verificar el Sistema
```bash
python scripts/verify_system.py
```

### 2. Ejecutar la Aplicación
```bash
python main.py
```

### 3. Abrir en el Navegador
```
http://127.0.0.1:5000
```

## ⚙️ Configuración

### Base de Datos PostgreSQL
Las configuraciones se encuentran en `app/core/config.py`:

```python
@dataclass
class DatabaseConfig:
    host: str = "localhost"
    port: int = 5432
    database: str = "prototipoPG_v2"
    username: str = "postgres"
    password: str = "camilomena"
```

### Variables de Entorno (Opcional)
Puedes usar variables de entorno para configuración:

```bash
export DB_HOST=localhost
export DB_PORT=5432
export DB_NAME=prototipoPG_v2
export DB_USER=postgres
export DB_PASSWORD=tu_password
```

## 🎯 Características Principales

### ✨ Reconocimiento Facial
- **Algoritmo**: face_recognition (basado en dlib)
- **Tolerancia**: Configurable (por defecto 0.6)
- **Cooldown**: 2 segundos entre reconocimientos
- **Modelos**: HOG (rápido) y CNN (preciso)

### 📊 Base de Datos PostgreSQL
- **Usuarios**: Gestión de estudiantes y profesores
- **Cursos**: Organización de clases
- **Sesiones**: Clases individuales con horarios
- **Asistencias**: Registro de presencia con timestamps
- **Embeddings**: Almacenamiento de características faciales

### 🌐 Interfaz Web
- **Streaming en Vivo**: Visualización de cámara en tiempo real
- **Dashboard**: Estado del sistema y estadísticas
- **APIs REST**: Consultas de asistencias y gestión
- **Responsive**: Compatible con dispositivos móviles

## 🛠️ Comandos Útiles

### Scripts de Utilidad
```bash
# Verificar sistema completo
python scripts/verify_system.py

# Limpiar archivos obsoletos  
python scripts/cleanup_project.py
```

### APIs Disponibles
```
GET  /                           # Página principal
GET  /video_feed                # Stream de video
POST /start_camera              # Iniciar cámara
POST /stop_camera               # Detener cámara
GET  /camera_status             # Estado de cámara
GET  /attendance/today          # Asistencias del día
GET  /attendance/student/<name> # Historial de estudiante
GET  /system/status             # Estado del sistema
POST /system/reload_faces       # Recargar rostros
```

## 🔧 Solución de Problemas

### Error de Conexión a PostgreSQL
```bash
# Verificar que PostgreSQL esté ejecutándose
# Windows: Servicios > PostgreSQL
# Verificar credenciales en app/core/config.py
```

### No Se Detecta la Cámara
```bash
# Verificar permisos de cámara
# Cambiar camera_index en app/core/config.py si tienes múltiples cámaras
```

### No Hay Rostros Cargados
```bash
# Verificar que las imágenes estén en /students/
# Ejecutar migración de embeddings si es necesario
```

## 📈 Próximas Mejoras

- [ ] **Dashboard Avanzado**: Gráficos de asistencia y estadísticas
- [ ] **Múltiples Cámaras**: Soporte para varias ubicaciones
- [ ] **Reconocimiento por Grupos**: Clases específicas
- [ ] **Notificaciones**: Alertas por ausencias
- [ ] **Exportación**: Reportes en PDF/Excel
- [ ] **API Mobile**: Aplicación móvil complementaria

## 👥 Contribuir

1. Fork del repositorio
2. Crear rama de feature (`git checkout -b feature/AmazingFeature`)
3. Commit de cambios (`git commit -m 'Add AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Licencia

Este proyecto está bajo la Licencia MIT. Ver `LICENSE` para más detalles.

## 🙏 Agradecimientos

- **face_recognition**: Por la excelente librería de reconocimiento facial
- **PostgreSQL**: Por la robusta base de datos
- **Flask**: Por el framework web ligero y eficiente
- **OpenCV**: Por las capacidades de procesamiento de video

---

**Desarrollado con ❤️ para automatizar la gestión de asistencias**