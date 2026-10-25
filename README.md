# Three Slicer Responsive

Demo web responsive que utiliza las funciones reales de Three Slicer mediante sus paquetes publicados: `three-slicer` (motor WebAssembly) y `three-slicer-viewer` (visor y controles React).

## Demo alojada

GitHub Actions compila la aplicación y la publica en GitHub Pages al actualizar `main`:

**https://spidey000.github.io/Three_slicer_responsive/**

La primera compilación puede tardar unos minutos. Si la URL aún no está disponible, revisa la pestaña **Actions** del repositorio.

## Funciones conectadas

- Carga de modelos por los controles nativos del visor o arrastrando archivos: STL, OBJ, 3MF, AMF, PLY y STEP.
- Motor real de laminado WebAssembly, perfiles de impresora, proceso y material, ajustes con el esquema y reglas de Three Slicer.
- Transformación de modelos, edición de objetos, varias placas, soportes y pintura de soporte/material.
- Vista previa de trayectorias, navegación por capas, estadísticas de impresión y exportación desde los controles originales.
- Apertura y vista previa de G-code y proyectos de resina compatibles, con las opciones que soporta el paquete.
- En móvil, el panel lateral se convierte en un cajón de ajustes. El resto de acciones continúa usando los componentes nativos del visor.

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

El script `prebuild` añade las reglas responsive al CSS aislado de la versión fijada de `three-slicer-viewer`. Esto permite adaptar el shell interno de su Shadow DOM sin duplicar el visor ni sustituir sus acciones.

## Límites del alojamiento

GitHub Pages sirve la app como sitio estático. La carga, el laminado y la vista previa se ejecutan en el navegador; los modelos no se envían a un servidor. Hace falta WebGL. GitHub Pages no permite configurar las cabeceras COOP/COEP que necesita `SharedArrayBuffer`, por lo que el motor debe funcionar con el worker de un hilo cuando el navegador lo requiera.

## Origen y licencias

La integración consume los paquetes del proyecto [`kimgh06/Three_Slicer`](https://github.com/kimgh06/Three_Slicer). El motor `three-slicer` se distribuye bajo AGPL-3.0-or-later y el visor `three-slicer-viewer` bajo MIT; este proyecto se publica bajo AGPL-3.0-or-later. Consulta [LICENSE](./LICENSE) y los avisos de terceros del proyecto original.
