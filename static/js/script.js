// Variables para controlar los intentos de la cámara
let cameraRetries = 0;
const MAX_RETRIES = 3;
let videoErrorCount = 0;

// Manejar errores de la cámara
function handleVideoError() {
    videoErrorCount++;
    
    // Solo mostrar el error después de varios intentos fallidos
    if (videoErrorCount > 3) {
        document.getElementById("camera-error").classList.remove("d-none");
        console.error("Error al cargar el vídeo feed");
    }
}

// Reiniciar la cámara
function restartCamera() {
    if (cameraRetries >= MAX_RETRIES) {
        alert(
            "No se ha podido conectar con la cámara después de varios intentos. Por favor, verifique la conexión."
        );
        return;
    }

    cameraRetries++;
    
    // Mostrar estado de reinicio
    const videoFeed = document.getElementById("video-feed");
    const errorElement = document.getElementById("camera-error");

    errorElement.querySelector("h5").textContent = "Reiniciando cámara...";
    errorElement.querySelector("p").textContent = 
      "Por favor espera un momento...";
    errorElement.querySelector("button").disabled = true;

    // Llama al endpoint para reiniciar la cámara
    fetch("/restart_camera")
        .then((response) => response.json())
        .then((data) => {
            console.log("Respuesta del servidor:", data);

            if (data.status === "success") {
                // Reiniciar el feed de video cambiando la URL (truco para forzar recarga)
                const timestamp = new Date().getTime();
                videoFeed.src = `{{ url_for('video_feed') }}?t=${timestamp}`;

                // Ocultar error después de un tiempo para dar tiempo a cargar
                setTimeout(() => {
                    errorElement.classList.add("d-none");
                    videoErrorCount = 0;
                }, 3000);
            } else {
                throw new Error(data.message || "Error al reiniciar la cámara");
            }
        })
        .catch((error) => {
            console.error("Error:", error);
            errorElement.querySelector("h5").textContent = 
               "Error al reiniciar la cámara";
            errorElement.querySelector("p").textContent = 
                error.message || "Ocurrió un error inesperado.";
        })
        .finally(() => {
            errorElement.querySelector("button").disabled = false;
        });
}

// Actualizar hora actual
function updateCurrentTime() {
    const now = new Date();
    const timeString = now.toLocaleTimeString();
    const dateString = now.toLocaleDateString("es-ES", {
        weekday: "long",
        year: "numeric",
        month: "long",
        day: "numeric",
    });
    document.getElementById(
        "current-time"
    ).textContent = `${dateString} - ${timeString}`;
}

// Actualizar tabla de asistencia
async function updateAttendanceTable() {
    try {
        const response = await fetch("/get_attendance");
        if (!response.ok) throw new Error("Error al obtener datos");

        const data = await response.json();
        const tbody = document.getElementById("attendance-data");
        
        if (data.length === 0) {
            tbody.innerHTML = '<tr><td colspan="3" class="text-center py-3">No hay registros de asistencia</td></tr>';
            return;
        }
        
        // Filtrar asistencias de hoy
        const today = new Date().toISOString().split("T")[0];
        const todayAttendance = data.filter((record) =>
            record.Fecha.startsWith(today)
        );
        
        // Actualizar contador de asistencias
        document.getElementById("today-attendance").textContent = todayAttendance.length;
        document.getElementById("attendance-count").textContent = `${data.length} asistencias registradas`;

        // Actualizar hora de última actualización
        document.getElementById("last-updated").textContent = `Última actualización: ${new Date().toLocaleTimeString()}`;

        // Generar filas de la tabla
        tbody.innerHTML = data
            .map((record, index) => {
                const date = new Date(record.Fecha);
                const formattedDate = date.toLocaleString("es-ES");

                // Verificar si es de hoy para resaltar
                const isToday = record.Fecha.startsWith(today);
                const rowClass = isToday ? "table-success" : "";
                return `
                <tr class="${rowClass}">
                    <td>${index + 1}</td>
                    <td><strong>${record.Nombre}</strong></td>
                    <td>${formattedDate}</td>
                </tr>
                `;
            })
            .join("");
    } catch (error) {
        console.error("Error:", error);
    }
}

// Consultar el estado de reconocimiento actual
async function updateRecognitionStatus() {
    try {
        const response = await fetch("/recognition_status");
        if (!response.ok) throw new Error("Error al obtener estado");
        
        const data = await response.json();
        const noRecognition = document.getElementById("no-recognition");
        const recognitionDetails = document.getElementById("recognition-details");
        const recognitionCard = document.getElementById("recognition-info");
        const recognitionOverlay = document.getElementById("recognition-message");

        // Actualizar contador total de estudiantes
        document.getElementById("total-students").textContent =
            document.getElementById("total-students").getAttribute("data-count") || 
            "0";

        if (!data.name) {
            // No hay reconocimiento activo
            noRecognition.classList.remove("d-none");
            recognitionDetails.classList.add("d-none");
            recognitionCard.classList.remove("highlight");
            recognitionOverlay.textContent = "Esperando reconocimiento...";
            return;
        }

        // Mostrar detalles del reconocimiento
        noRecognition.classList.add("d-none");
        recognitionDetails.classList.remove("d-none");

        // Aplicar efecto de iluminación cuando hay un nuevo reconocimiento
        recognitionCard.classList.add("highlight");
        setTimeout(() => recognitionCard.classList.remove("highlight"), 2000);

        // Actualizar datos de reconocimiento
        document.getElementById("person-name").textContent = data.name;

        const confidencePercent = Math.round(data.confidence * 100);
        document.getElementById("confidence-bar").style.width = `${confidencePercent}%`;
        document.getElementById("confidence-text").textContent = `Confianza: ${confidencePercent}%`;

        // Establecer estado y color del badge
        const statusBadge = document.getElementById("recognition-status-badge");
        statusBadge.textContent = data.status;

        if (data.status === "Registrado") {
            statusBadge.className = "badge bg-success";
            recognitionOverlay.textContent = `${data.name} - Registrado`;
        } else {
            statusBadge.className = "badge bg-warning";
            recognitionOverlay.textContent = `${data.name} - Ya registrado`;
        }

        // Actualizar tabla si hubo un nuevo registro
        if (data.status === "Registrado") {
            updateAttendanceTable();
        }
    } catch (error) {
        console.error("Error:", error);
    }
}

// Inicializar contador de estudiantes totales
async function initStudentCount() {
    try {
        const response = await fetch("/get_attendance");
        if (!response.ok) throw new Error("Error al obtener datos");

        const data = await response.json();

        // Extraer nombres únicos (estudiantes únicos)
        const uniqueStudents = [...new Set(data.map((record) => record.Nombre))];
        document.getElementById("total-students").textContent = uniqueStudents.length;
        document.getElementById("total-students").setAttribute("data-count", uniqueStudents.length);
    } catch (error) {
        console.error("Error:", error);
    }
}

// Inicializar todo
document.addEventListener("DOMContentLoaded", function () {
    // Actualizar hora
    updateCurrentTime();
    setInterval(updateCurrentTime, 1000);

    // Inicializar datos
    updateAttendanceTable();
    initStudentCount();

    // Consultar periódicamente nuevos reconocimientos
    setInterval(updateRecognitionStatus, 1000);

    // Actualizar tabla periódicamente
    setInterval(updateAttendanceTable, 10000);

    // Botón de actualización manual
    document.getElementById("refresh-btn").addEventListener("click", function () {
        updateAttendanceTable();
        this.classList.add("disabled");
        this.innerHTML = '<span class="spinner-border spinner-border-sm" role="status" aria-hidden="true"></span>';

        setTimeout(() => {
            this.classList.remove("disabled");
            this.innerHTML = '<i class="fas fa-sync-alt"></i>';
        }, 1000);
    });
});