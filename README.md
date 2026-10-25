# Three Slicer Responsive

Prototipo navegable de la interfaz de Three Slicer adaptada a móvil y tablet, junto con la especificación técnica para implementar el rediseño en la aplicación.

## Probar la interfaz

Abre [index.html](./index.html) en un navegador moderno o publica el repositorio con GitHub Pages. La vista cambia según el ancho de pantalla:

- **Móvil (<768 px):** visor 3D conceptual a pantalla completa, navegación inferior y panel de ajustes plegable con pestañas Rápido, Avanzado y Modelo.
- **Tablet (768–1100 px):** barra de herramientas, visor central y panel lateral de ajustes.
- **Escritorio (>1100 px):** composición completa con herramientas, visor y panel de inspección.

El panel móvil se puede abrir desde **Ajustes** o deslizando la bandeja hacia arriba. Los botones **Laminar** y **Exportar** muestran un mensaje de demostración.

## Alcance

Este repositorio contiene un prototipo visual y de interacción. No integra el motor de laminado, la carga real de modelos, ni la exportación de G-code. El modelo geométrico de la demo es ilustrativo.

La propuesta conserva las tareas centrales del slicer y reorganiza los controles para el tamaño de pantalla: ajustes frecuentes al alcance del pulgar en móvil y un inspector persistente en tablet.

## Especificación técnica

Consulta [docs/Three_Slicer_especificacion_tecnica_responsive.md](./docs/Three_Slicer_especificacion_tecnica_responsive.md) para la arquitectura de componentes, breakpoints, interacción táctil, accesibilidad, fases de implementación y criterios de aceptación.

## Uso

No hay dependencias ni proceso de compilación. Sirve index.html desde cualquier servidor estático. Para activar GitHub Pages, selecciona la rama main y la carpeta raíz en la configuración **Settings → Pages**.
