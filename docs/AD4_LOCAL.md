# Three Slicer web + Adventurer 4 local

La aplicación local usa exclusivamente el perfil **Flashforge Adventurer 4 Series 0.4 Nozzle** del catálogo OrcaSlicer incluido en `three-slicer@0.4.0`. Carga su perfil de proceso recomendado y el primer filamento recomendado disponible. El selector de impresoras desaparece; proceso, material y ajustes permanecen editables. Antes de imprimir, comprueba físicamente boquilla, filamento, superficie y nivelación.

## Arranque

En la máquina conectada a la misma red de la AD4:

```sh
git clone https://github.com/spidey000/FFAD4Manager.git
python3 -m venv .venv
. .venv/bin/activate
pip install -e ./FFAD4Manager
ffadv4manager config set --host 192.168.1.50

cd Three_slicer_responsive
npm ci
npm run build
npm run local
```

Abre `http://127.0.0.1:8765/Three_slicer_responsive/`. Para desarrollo, ejecuta también `npm run dev`: Vite envía `/api` al puente local. El puente escucha **solo** en `127.0.0.1`; no expongas su puerto directamente a Internet. Puedes proporcionar `AD4_HOST`, `AD4_CLI` y `AD4_WEB_PORT` como variables de entorno. Si usas `AD4_WEB_PORT` distinto de `8765`, ajusta también el proxy de Vite.

## Flujo

1. Carga un modelo y modifica proceso, material o cualquier parámetro. **Laminar** usa el motor WebAssembly. El interruptor **Auto slice** vuelve a laminar tras cambios.
2. Al recibir `onSliced`, la web conserva el G-code exacto del resultado y muestra **Imprimir** y **Solo enviar**. Un cambio de configuración o de objetos invalida el resultado y restaura **Laminar**.
3. `POST /api/printer/jobs?start=true` pasa el G-code al puente. Éste crea un archivo temporal y llama a `ffadv4manager upload ARCHIVO --start`: el CLI convierte G-code a GX automáticamente, verifica el nombre en la lista de la impresora y después selecciona/inicia. `start=false` llama a `upload` sin iniciar.
4. El estado se consulta con `ffadv4manager status --json` y la cámara usa `ffadv4manager camera snapshot`. Si falla la conexión, el modal presenta la imagen con marca de agua de prueba.

El CLI rechaza subir cuando detecta una impresión activa (no se utiliza `--force`). Su comprobación M661 confirma el nombre, **no** la integridad del contenido; «Solo enviar» evita M23/M24 desde el software, pero su documentación pide supervisar el resultado en una AD4 real. La conversión GX empaqueta G-code, no reescribe órdenes incompatibles. Esta integración no se ha probado con una impresora física conectada en este entorno.

## API local

| Ruta | Función |
| --- | --- |
| `GET /api/printer/status` | Estado JSON del CLI |
| `GET /api/printer/camera` | Primer fotograma JPEG del MJPEG |
| `POST /api/printer/jobs?start=true\|false` | G-code `text/plain` (máximo 100 MB); subir e iniciar o solo subir |

El puente llama al CLI como proceso con argumentos separados (sin shell), usa directorio temporal y responde con errores JSON. El sitio publicado en GitHub Pages conserva el laminador, pero sus funciones de impresora requieren esta instancia local.
