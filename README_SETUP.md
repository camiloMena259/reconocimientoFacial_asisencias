Guía de instalación (Windows PowerShell)

Este proyecto usa Python y varias librerías que requieren compilación (p.ej. dlib). Recomiendo usar Miniconda/Anaconda en Windows para simplificar la instalación.

1) Instalar Miniconda (si no lo tienes)
- Ve a https://docs.conda.io/en/latest/miniconda.html y descarga el instalador para Windows (Miniconda3).
- Ejecuta el instalador y sigue las opciones por defecto. Asegúrate de marcar "Add Anaconda to my PATH" si quieres (opcional). También puedes usar la app Anaconda Prompt.

2) Abrir PowerShell y verificar conda
```powershell
conda --version
```

3) Crear el entorno desde `environment.yml` (recomendado)
- Desde la carpeta del proyecto (donde está `environment.yml`):
```powershell
conda env create -f environment.yml
conda activate envEstudiantes
```

4) (Alternativa) Crear entorno manual y luego instalar paquetes
```powershell
conda create --name envEstudiantes python=3.8.10 -y
conda activate envEstudiantes
# instalar paquetes principales desde conda-forge
conda install -c conda-forge numpy pandas opencv dlib -y
# instalar pip packages
pip install face_recognition flask opencv-python
```

5) Verificar instalación
```powershell
python -c "import face_recognition, cv2, pandas, flask, numpy; print('Instalación OK')"
```

6) Ejecutar la app
```powershell
python app.py
```
- Abre http://localhost:5000 en tu navegador.

Notas y problemas comunes
- Si `dlib` falla con conda, intenta `conda install -c conda-forge dlib`.
- Si `pip install face_recognition` falla y `dlib` no está presente, la instalación no funcionará.
- Si tienes problemas con compilación en Windows, instala Visual Studio Build Tools y CMake (opción menos preferida si puedes usar conda-forge).

Si quieres, puedo:
- Ajustar `environment.yml` si prefieres otras versiones.
- Generar un script PowerShell (`setup_env.ps1`) que automatice los pasos (descarga opcional de Miniconda no incluida).
