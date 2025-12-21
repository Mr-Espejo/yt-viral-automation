# 📺 YouTube Viral Automation

Una plataforma escalable diseñada para la minería de datos, análisis de viralidad y procesamiento de contenido de YouTube utilizando una arquitectura modular basada en **Pipelines**.

---

## 🏗️ Arquitectura del Sistema

El proyecto está dividido en pipelines independientes que se comunican a través de un sistema de almacenamiento centralizado (**Storage**).

### 1. 🔍 Mining Pipeline (`mining_pipeline/`)
Encargado de la interacción con YouTube.
- **Fase 1-2**: Configuración y resolución de canales (@handle, ID, URL).
- **Fase 3**: Minería de metadatos (vistas, likes, comentarios).
- **Fase 4**: Análisis de viralidad y detección de "Outliers".
- **Fase 5**: Descarga automatizada de videos virales (MP4).

### 2. 🎞️ Edit Pipeline (`edit_pipeline/`)
Encargado del procesamiento técnico de medios.
- **Fase 7**: Normalización de video (H.264/AAC, 1080p, 30fps).
- **Extracción de Assets**: Separación de audio (WAV) y generación de keyframes (JPG).
- **Metadatos Técnicos**: Generación de reportes JSON con duración, bitrate y segmentación.

### 3. 📦 Shared & Storage
- **`shared/`**: Lógica común como el `StorageManager` para persistencia.
- **`storage/`**: El "Data Lake" donde se centralizan metadatos y videos.

---

## 🚀 Instalación y Requisitos

### Requisitos del Sistema
1. **Python 3.10+**
2. **FFmpeg**: Necesario para el procesamiento de video.
   - **Windows**: Descargar desde [gyan.dev](https://www.gyan.dev/ffmpeg/builds/) y añadir al PATH.
   - **Linux**: `sudo apt install ffmpeg`

### Configuración de Python
```bash
# Instalar dependencias
pip install -r requirements.txt
```

---

## ⚙️ Configuración

Edita el archivo `mining_pipeline/config.yaml`:
```yaml
api_key: "TU_API_KEY_AQUI"
channel: "@nombre_canal"
min_views: 1000000
min_engagement: 0.05
storage:
  root: "./storage" # Carpeta raíz para todos los datos
```

---

## 🛠️ Cómo Ejecutar

### Paso 1: Minería y Descarga
Ejecuta el pipeline de extracción de datos de YouTube.
```bash
cd mining_pipeline
python main.py
```

### Paso 2: Procesamiento y Normalización
Prepara los videos descargados para edición o análisis.
```bash
cd edit_pipeline
python main.py
```

---

## 📂 Organización de Datos (Storage)

Todos los resultados se organizan en la raíz del proyecto:
- `storage/metadata/`: CSVs de minería y JSONs técnicos.
- `storage/videos/viral/`: Videos originales descargados.
- `storage/videos/normalized/`: Videos estandarizados en 1080p.
- `storage/videos/audio/`: Pistas WAV extraídas.
- `storage/videos/frames/`: Secuencias de imágenes de los videos.

---

## ⚖️ Principios de Ingeniería
- **SOLID**: Cada clase tiene una única responsabilidad.
- **Arquitectura Limpia**: Los pipelines están desacoplados.
- **Idempotencia**: El sistema detecta archivos ya procesados para evitar trabajo redundante.
- **Determinismo**: La normalización asegura que todos los assets tengan las mismas propiedades técnicas.
