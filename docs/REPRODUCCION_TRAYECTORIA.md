# Exploración y simulación del recorrido

Tras laminar un modelo FFF (o abrir G-code compatible), el visor de Three Slicer cambia a **Preview**. Su vista de trayectoria representa los segmentos extruidos, los desplazamientos y un marcador de boquilla. La barra nueva, situada bajo el visualizador, controla esa misma vista:

- **Capas** muestra de la primera a la seleccionada; **Solo capa** aísla la seleccionada.
- **Movimiento** recorre los movimientos de la capa visible en el orden que registra el visor, tanto extrusiones como desplazamientos. La boquilla señala la posición correspondiente.
- **▶** reproduce a 80 movimientos por segundo simulado; **⏩** a ocho veces esa velocidad; **Ⅱ** pausa; **■** detiene y vuelve al primer movimiento de la primera capa. La barra de capas permite saltar a cualquier capa.

Es una animación de la trayectoria calculada, **no una predicción temporal exacta** de la impresión: se avanza por número de movimientos, sin modelar aceleraciones, esperas, temperatura ni comandos auxiliares. No comunica con la impresora. La vista por movimientos solo corresponde a FFF; las impresiones de resina exponen capas, pero no movimiento secuencial de boquilla.

## Integración técnica

`Viewport` 0.4.0 emite `canvasMode`, `layerCount`, `layerRange` y `moveScrub`, pero no acepta un valor controlado de capa o movimiento. `src/previewBridge.js` encapsula el acceso a los controles nativos de Preview en el Shadow DOM abierto del visor (identificados por `data-testid`), y despacha sus cambios para que el estado, el recorte de segmentos y el marcador de boquilla continúen gobernados por Three Slicer. En móvil, el panel lateral nativo permanece montado pero oculto visualmente; los controles nuevos actúan sobre él. Si se actualiza `three-slicer-viewer`, comprobar esos identificadores y sustituir este adaptador por una API pública si el paquete la añade.

La reproducción usa `requestAnimationFrame`; pausa al cambiar de placa, salir de Preview, laminar de nuevo o mover manualmente los deslizadores. Se limita la tasa de actualización de las etiquetas para no volver a renderizar todo el visor en cada fotograma. El espacio inferior queda reservado dentro de la columna 3D para que las tarjetas, los botones de placa y la barra no se solapen en tablet o móvil.
