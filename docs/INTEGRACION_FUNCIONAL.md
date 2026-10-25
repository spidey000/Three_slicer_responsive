# Revisión de integración funcional

## Resultado de la auditoría

La primera versión del repositorio era una maqueta HTML: dibujaba un modelo ilustrativo y sus botones solo cambiaban un mensaje. No estaba conectada con Three Slicer. Se sustituyó por una aplicación React que integra `three-slicer@0.4.0` y `three-slicer-viewer@0.4.0`.

## Conexiones implementadas

| Interfaz | API real | Resultado |
|---|---|---|
| Escena 3D y herramientas nativas | `three-slicer-viewer` `<Viewport>` | Conserva carga, arrastre de modelos, transformaciones, objetos, placas, pintura, previsualización y exportación del visor. |
| Motor de laminado | `useSlicer` + `makeSlicerWorker` de `three-slicer/client` | Ejecuta el kernel WebAssembly en el navegador. |
| Perfiles de impresora | `bundledCatalog`, `printersByVendor`, `printerSettings` | La impresora seleccionada actualiza el mismo mapa de ajustes que consume el motor. |
| Perfiles de proceso y material | `processPresets()`, `filamentPresets()` | Los perfiles aplican los valores del catálogo al estado compartido. |
| Ajustes avanzados | `SettingsPanel` + `schema`, `uiTree`, `makeCfg` y `disabledKeys` | Usa el formulario, esquema y reglas de disponibilidad de Three Slicer. |
| Botón móvil Laminar | Prop `sliceRequest` | Incrementa un token y solicita un laminado al visor; el estado de progreso y resultado llega por `onEvent` y `onSliced`. |
| Cajón responsive móvil | `SettingsPanel` y catálogos reales | Sustituye la columna lateral en móvil y escribe en el mismo estado conectado al kernel. |
| Panel lateral tablet/escritorio | Slots `processPanel`, `motionPanel`, `filamentPanel` | Reutiliza los paneles originales y sus enlaces con impresora, filamento y motor. |

## Funciones que proporciona el visor

El prototipo delega estas operaciones en los controles y el motor upstream, en lugar de reimplementarlas en botones simulados: carga de STL/OBJ/3MF/AMF/PLY/STEP; proyectos y placas; manipulación de objetos; perfiles; soportes; pintura de soportes y materiales; slicing FFF/SLA que admita el kernel; vista previa de trayectorias y capas; G-code y archivos de resina compatibles; y exportaciones que implemente el visor.

## Responsive y límites

El visor mantiene su Shadow DOM. La demo añade reglas de móvil y tablet dentro de su raíz abierta, vinculadas a la versión fijada del paquete. Por debajo de 768 px esconde solo el sidebar nativo y ofrece los ajustes y el comando de laminado desde el cajón/banda inferior. Entre 768 y 1100 px conserva el sidebar y lo estrecha a 300 px.

GitHub Pages requiere que el propietario seleccione una vez **Settings → Pages → Build and deployment → Source: GitHub Actions**. La integración GitHub puede publicar el código, pero no puede crear esa configuración del sitio: GitHub Actions responde `Resource not accessible by integration` al intentar habilitarla. Después de activar Pages, el workflow realiza las publicaciones futuras.

GitHub Pages no permite servir cabeceras COOP/COEP. El paquete escoge el worker compatible con el entorno; la variante multihilo necesita aislamiento entre orígenes, por lo que Pages puede utilizar el kernel de un hilo. WebGL es necesario para el visor. Las operaciones locales no suben los modelos a un backend.

## Comprobación realizada

`npm run build` completa correctamente con los paquetes 0.4.0 fijados. La salida incluye la aplicación, el worker de slicing, los workers auxiliares y el artefacto WASM. Para comprobar el flujo final de Pages, consulta la ejecución más reciente de GitHub Actions después del push.
