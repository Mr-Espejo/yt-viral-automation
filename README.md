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

### 3. 🧩 Composition Pipeline (`composition_pipeline/` & `combination_pipeline/`)
Encargado de la creación de contenido final a partir de múltiples fuentes.
- **Fase 8: Combination Generator**: Generación determinista de instrucciones de combinación (instrucciones JSON) para videos pares (Top/Bottom).
- **Fase 9: Composition Engine**: Motor de renderizado FFmpeg que construye shorts verticales (9:16) con layouts dinámicos (Split Screen), normalización de audio a -14 LUFS y estrategias de reencuadre (Crop Fill, Zoom, Blur).

### 4. 📦 Shared & Storage
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
python -m mining_pipeline.main
```

### Paso 2: Procesamiento y Normalización
Prepara los videos descargados para edición o análisis.
```bash
python -m edit_pipeline.main
```

### Paso 3: Generación de Combinaciones (Fase 8)
Genera las instrucciones metadata de qué videos emparejar sin duplicados.
```bash
python -m combination_pipeline.run_generator
```

### Paso 4: Composición y Renderizado (Fase 9)
Puedes renderizar un solo video manual o procesar todas las combinaciones generadas.

**A. Procesar todas las combinaciones (Recomendado):**
```bash
python -m composition_pipeline.main --combinations storage/metadata/video_combinations.json
```

**B. Renderizar un solo video manual:**
```bash
python -m composition_pipeline.main --config composition_pipeline/composition.yaml --output final_short.mp4
```

### Paso 5: Subida a YouTube (Fase 10)
Publica los videos procesados en YouTube con control de cuotas y seguimiento de publicaciones.

**Características:**
- **Límite Diario**: Máximo 9 videos por sesión de subida.
- **Seguimiento (Tracking)**: Identifica videos ya subidos para evitar duplicados.
- **Modos de Subida**:
  - `auto`: Prioriza los videos de `composed` (ediciones nuevas) si existen.
  - `composed`: Solo sube videos creados por el Composition Engine.
  - `priority`: Solo sube videos originales optimizados por el Edit Pipeline.

**Comandos:**
```bash
# Subida automática (recomendado)
python -m upload_pipeline.main --mode auto

# Forzar subida de videos combinados (Composed)
python -m upload_pipeline.main --mode composed

# Forzar subida de videos originales optimizados (Priority)
python -m upload_pipeline.main --mode priority
```

---

## 📂 Organización de Datos (Storage)

Todos los resultados se organizan en la raíz del proyecto:
- `storage/metadata/`: CSVs de minería, JSONs técnicos y combinaciones.
- `storage/videos/viral/`: Videos originales descargados.
- `storage/videos/normalized/`: Videos estandarizados en 1080p.
- `storage/videos/composed/`: **Videos finales listos para subir.**
- `storage/videos/audio/`: Pistas WAV extraídas.
- `storage/videos/frames/`: Secuencias de imágenes de los videos.

---

## ⚖️ Principios de Ingeniería
- **SOLID**: Cada clase tiene una única responsabilidad.
- **Arquitectura Limpia**: Los pipelines están desacoplados.
- **Idempotencia**: El sistema detecta archivos ya procesados para evitar trabajo redundante.
- **Determinismo**: La normalización y composición aseguran resultados reproducibles.
- **Composición Técnica**: El motor de video actúa por reglas técnicas, no por decisiones creativas humanas.
