// Manejar errores de la cámara
function handleVideoError() {
    console.error("Error al cargar el vídeo feed");
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

        if (!data.person) {
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
        document.getElementById("person-name").textContent = data.person.name;

        const confidencePercent = Math.round(data.person.confidence * 100);
        document.getElementById("confidence-bar").style.width = `${confidencePercent}%`;
        document.getElementById("confidence-text").textContent = `Confianza: ${confidencePercent}%`;

        // Establecer estado y color del badge
        const statusBadge = document.getElementById("recognition-status-badge");
        statusBadge.textContent = data.person.status;

        if (data.person.status === "Registrado") {
            statusBadge.className = "badge bg-success";
            recognitionOverlay.textContent = `${data.person.name} - Registrado`;
        } else {
            statusBadge.className = "badge bg-warning";
            recognitionOverlay.textContent = `${data.person.name} - Ya registrado`;
        }

        // Actualizar tabla si hubo un nuevo registro
        if (data.person.status === "Registrado") {
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

    // Inicializar funcionalidad de registro de usuarios
    initUserRegistration();
});

// ===== FUNCIONALIDAD DE REGISTRO DE USUARIOS =====
let currentStep = 1;
let capturedPhotos = [];
let isCapturing = false;

function initUserRegistration() {
    const modal = document.getElementById('registerModal');
    const startCaptureBtn = document.getElementById('start-capture-btn');
    const capturePhotoBtn = document.getElementById('capture-photo-btn');
    const resetCaptureBtn = document.getElementById('reset-capture-btn');
    const confirmBtn = document.getElementById('confirm-registration-btn');
    const retakeBtn = document.getElementById('retake-photos-btn');
    const cancelBtn = document.getElementById('cancel-btn');

    // Evento al abrir el modal
    modal.addEventListener('show.bs.modal', function () {
        resetRegistrationModal();
    });

    // Evento al cerrar el modal
    modal.addEventListener('hide.bs.modal', function () {
        exitRegistrationMode();
    });

    // Comenzar captura
    startCaptureBtn.addEventListener('click', function () {
        const name = document.getElementById('user-name').value.trim();
        const lastname = document.getElementById('user-lastname').value.trim();

        if (!name || !lastname) {
            alert('Por favor completa nombre y apellido antes de continuar');
            return;
        }

        enterRegistrationMode();
    });

    // Capturar foto
    capturePhotoBtn.addEventListener('click', capturePhoto);

    // Reiniciar captura
    resetCaptureBtn.addEventListener('click', resetCapture);

    // Confirmar registro
    confirmBtn.addEventListener('click', confirmRegistration);

    // Tomar fotos nuevamente
    retakeBtn.addEventListener('click', retakePhotos);

    // Cancelar
    cancelBtn.addEventListener('click', function () {
        exitRegistrationMode();
    });
}

function resetRegistrationModal() {
    currentStep = 1;
    capturedPhotos = [];
    
    // Limpiar formulario
    document.getElementById('user-name').value = '';
    document.getElementById('user-lastname').value = '';
    document.getElementById('user-email').value = '';
    
    // Mostrar paso 1
    showStep('step-form');
    
    // Resetear contadores
    updatePhotoCounter(0);
    document.getElementById('photo-thumbnails').innerHTML = '';
}

function showStep(stepId) {
    // Ocultar todos los pasos
    document.querySelectorAll('.registration-step').forEach(step => {
        step.classList.add('d-none');
    });
    
    // Mostrar el paso activo
    document.getElementById(stepId).classList.remove('d-none');
    
    // Actualizar botones del footer
    updateFooterButtons(stepId);
}

function updateFooterButtons(stepId) {
    const confirmBtn = document.getElementById('confirm-registration-btn');
    const retakeBtn = document.getElementById('retake-photos-btn');
    
    // Ocultar todos los botones
    confirmBtn.classList.add('d-none');
    retakeBtn.classList.add('d-none');
    
    if (stepId === 'step-preview') {
        confirmBtn.classList.remove('d-none');
        retakeBtn.classList.remove('d-none');
    }
}

async function enterRegistrationMode() {
    try {
        const response = await fetch('/toggle_mode', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({ mode: 'registro' })
        });
        
        const result = await response.json();
        
        if (result.success) {
            showStep('step-capture');
            currentStep = 2;
            isCapturing = true;
        } else {
            alert('Error al cambiar a modo registro: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión');
    }
}

async function exitRegistrationMode() {
    try {
        if (isCapturing) {
            await fetch('/toggle_mode', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({ mode: 'asistencia' })
            });
            isCapturing = false;
        }
    } catch (error) {
        console.error('Error al salir del modo registro:', error);
    }
}

async function capturePhoto() {
    if (capturedPhotos.length >= 4) {
        return;
    }
    
    try {
        const response = await fetch('/capture_photo', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            updatePhotoCounter(result.capture_count);
            addPhotoThumbnail(result.capture_count);
            
            if (result.capture_count >= 4) {
                // Captura completa, mostrar preview
                setTimeout(() => {
                    showPhotoPreview();
                }, 500);
            }
        } else {
            alert('Error al capturar foto: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión');
    }
}

function updatePhotoCounter(count) {
    document.getElementById('photo-counter').textContent = `${count}/4`;
}

function addPhotoThumbnail(photoNumber) {
    const thumbnailsContainer = document.getElementById('photo-thumbnails');
    
    // Crear thumbnail placeholder (se actualizará después)
    const thumbnail = document.createElement('div');
    thumbnail.className = 'photo-thumbnail-placeholder';
    thumbnail.innerHTML = `
        <div class="photo-thumbnail bg-success d-flex align-items-center justify-content-center text-white">
            <i class="fas fa-check"></i>
        </div>
    `;
    
    thumbnailsContainer.appendChild(thumbnail);
}

async function showPhotoPreview() {
    try {
        // Obtener las fotos capturadas del servidor
        const response = await fetch('/get_captured_photos');
        const result = await response.json();
        
        if (result.success) {
            capturedPhotos = result.photos;
            displayPhotoPreview(result.photos);
            showStep('step-preview');
            currentStep = 3;
        } else {
            alert('Error al obtener fotos: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error al cargar preview');
    }
}

function displayPhotoPreview(photos) {
    const previewGrid = document.getElementById('photo-preview-grid');
    
    previewGrid.innerHTML = photos.map((photo, index) => `
        <div class="col-md-3 col-6 mb-3">
            <div class="photo-item">
                <img src="${photo}" alt="Foto ${index + 1}" class="photo-preview">
                <div class="photo-label">Foto ${index + 1}</div>
            </div>
        </div>
    `).join('');
}

async function resetCapture() {
    try {
        const response = await fetch('/reset_registration', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            }
        });
        
        const result = await response.json();
        
        if (result.success) {
            capturedPhotos = [];
            updatePhotoCounter(0);
            document.getElementById('photo-thumbnails').innerHTML = '';
            showStep('step-capture');
        } else {
            alert('Error al reiniciar: ' + result.message);
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión');
    }
}

function retakePhotos() {
    resetCapture();
}

async function confirmRegistration() {
    const name = document.getElementById('user-name').value.trim();
    const lastname = document.getElementById('user-lastname').value.trim();
    const email = document.getElementById('user-email').value.trim();
    
    if (!name || !lastname) {
        alert('Nombre y apellido son requeridos');
        return;
    }
    
    // Mostrar paso de procesamiento
    showStep('step-processing');
    
    try {
        const response = await fetch('/save_user', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify({
                nombre: name,
                apellido: lastname,
                email: email
            })
        });
        
        const result = await response.json();
        
        if (result.success) {
            alert('¡Usuario registrado exitosamente!\n' + result.message);
            
            // Cerrar modal
            const modal = bootstrap.Modal.getInstance(document.getElementById('registerModal'));
            modal.hide();
            
            // Actualizar contadores
            updateAttendanceTable();
            initStudentCount();
            
        } else {
            alert('Error al registrar usuario: ' + result.message);
            showStep('step-preview'); // Volver al preview
        }
    } catch (error) {
        console.error('Error:', error);
        alert('Error de conexión al guardar usuario');
        showStep('step-preview'); // Volver al preview
    }
}