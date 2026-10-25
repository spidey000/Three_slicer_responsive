# Webcam de la impresora: contrato de integración

El botón con la cámara abre ahora un modal funcional. La imagen actual es un SVG ilustrativo con la marca de agua **IMAGEN DE PRUEBA**. «Actualizar prueba» solo actualiza la hora simulada; no hace una petición a una impresora.

Cuando exista una conexión real, se debe conservar el botón y el modal y sustituir el origen de la imagen por un `Blob` JPEG o PNG devuelto por el servidor. Evita incluir credenciales de la impresora en el frontend público. El backend puede actuar como proxy autenticado hacia la cámara y verificar el tipo de contenido.

```js
// PSEUDOCÓDIGO: contrato ficticio, sin endpoint real conectado.
async function obtenerCapturaImpresora({ printerId, signal }) {
  const respuesta = await fetch(`/api/printers/${encodeURIComponent(printerId)}/camera/snapshot`, {
    method: 'GET',
    headers: { Accept: 'image/jpeg, image/png' },
    credentials: 'include', // la sesión se valida en el servidor
    cache: 'no-store',
    signal,
  })
  if (!respuesta.ok) throw new Error(`La cámara respondió ${respuesta.status}`)
  const tipo = respuesta.headers.get('content-type')?.split(';')[0].trim().toLowerCase()
  if (!['image/jpeg', 'image/png'].includes(tipo)) throw new Error('Formato no compatible')
  const archivo = await respuesta.blob()
  if (archivo.size > 10_000_000) throw new Error('Captura demasiado grande')
  return { url: URL.createObjectURL(archivo), mime: tipo, capturedAt: new Date() }
}

// Al abrir o actualizar el modal: abortar la petición anterior, indicar cargando,
// obtener la captura, revocar la URL anterior con URL.revokeObjectURL(url) y renderizar
// la nueva URL. En un error, mostrarlo en el modal sin sustituirlo por una imagen vieja.
// Al cerrar/desmontar: abortar la petición y revocar la URL actual.
```

El servidor ficticio `GET /api/printers/:printerId/camera/snapshot` debería obtener una captura puntual de la cámara configurada para esa impresora, autenticar al usuario, restringir el origen de la impresora autorizado y devolver bytes `image/jpeg` o `image/png`. No hace falta exposición directa de la webcam ni streaming para esta función.
