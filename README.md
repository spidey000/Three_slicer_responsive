# Three Slicer Responsive · Adventurer 4

Aplicación local responsive para Flashforge Adventurer 4. Lamina mediante `three-slicer` (WebAssembly), visualiza mediante `three-slicer-viewer` y usa [FFAD4Manager](https://github.com/spidey000/FFAD4Manager) como puente para conectar con la impresora.

**[Instalación local y flujo Slice → Print / Solo enviar](./docs/AD4_LOCAL.md).** GitHub Pages ofrece una demostración del laminador; la conexión con la impresora funciona al ejecutar el servidor local.

## Demo alojada

GitHub Actions compila la aplicación y la publica en GitHub Pages al actualizar `main`:

**https://spidey000.github.io/Three_slicer_responsive/**

[Vista de revisión móvil y tablet](https://spidey000.github.io/Three_slicer_responsive/preview.html) con dos marcos interactivos a anchuras reales.

En la primera publicación, configura una vez **Settings → Pages → Build and deployment → Source: GitHub Actions**. Después, GitHub Actions compila y publica la aplicación al actualizar `main`. Si la URL aún no está disponible, revisa **Actions**.

## Funciones conectadas

- Carga de modelos por los controles nativos del visor o arrastrando archivos: STL, OBJ, 3MF, AMF, PLY y STEP.
- Motor real de laminado WebAssembly con perfil de impresora Adventurer 4 de 0,4 mm fijo, proceso y material OrcaSlicer; sin selector de otras impresoras.
- Transformación de modelos, edición de objetos, varias placas, soportes y pintura de soporte/material.
- Vista previa de trayectorias, navegación por capas, estadísticas de impresión y exportación desde los controles originales.
- Barra de [exploración y simulación del recorrido](./docs/REPRODUCCION_TRAYECTORIA.md): capa, movimiento, reproducción, avance rápido, pausa y parada. Mueve el marcador de boquilla sobre la trayectoria real ya laminada.
- Apertura y vista previa de G-code y proyectos de resina compatibles, con las opciones que soporta el paquete.
- En móvil, el panel lateral se convierte en un cajón de ajustes. El resto de acciones continúa usando los componentes nativos del visor.
- Un icono de cámara abre una captura real mediante el puente local; cuando no hay conexión muestra una imagen de prueba con marca de agua.
- Al terminar el laminado aparece Imprimir y Solo enviar; Auto slice es opcional. Los cambios de modelo o ajustes invalidan el G-code anterior y restauran Laminar.

La demo mantiene un único estado de configuración compartido entre perfiles, `SettingsPanel` y `Viewport`. El botón móvil **Laminar** envía una solicitud al visor real; el archivo G-code se exporta desde los controles nativos.

## Desarrollo local

Requiere Node.js 20 o posterior.

```bash
npm install
npm run dev
```

Para verificar la compilación de producción:

```bash
npm run build
npm run preview
```

La app añade las reglas responsive al Shadow DOM abierto de `three-slicer-viewer`. El adaptador de Preview se limita a sus controles nativos; no duplica el motor de laminado ni el renderizador de trayectorias.

## Límites del alojamiento

GitHub Pages sirve la app como sitio estático. La carga, el laminado y la vista previa se ejecutan en el navegador; los modelos no se envían a un servidor. Hace falta WebGL. GitHub Pages no permite configurar las cabeceras COOP/COEP que necesita `SharedArrayBuffer`, por lo que el motor debe funcionar con el worker de un hilo cuando el navegador lo requiera.

## Origen y licencias

La integración consume los paquetes del proyecto [`kimgh06/Three_Slicer`](https://github.com/kimgh06/Three_Slicer). El motor `three-slicer` se distribuye bajo AGPL-3.0-or-later y el visor `three-slicer-viewer` bajo MIT; este proyecto se publica bajo AGPL-3.0-or-later. Consulta [LICENSE](./LICENSE) y los avisos de terceros del proyecto original.
