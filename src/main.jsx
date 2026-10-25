import React from 'react'
import { createRoot } from 'react-dom/client'
import Demo from './Demo.jsx'
import './styles.css'

class InterfaceBoundary extends React.Component {
  state = { error: null }

  static getDerivedStateFromError(error) { return { error } }

  componentDidCatch(error, info) {
    console.error('Error al renderizar Three Slicer', error, info.componentStack)
  }

  render() {
    if (this.state.error) return <main className="startup-error" role="alert">
      <h1>No se pudo mostrar la interfaz</h1>
      <p>Recarga la página. Si el problema continúa, copia el error de la consola del navegador para poder investigarlo.</p>
      <code>{this.state.error.message}</code>
      <button type="button" onClick={() => window.location.reload()}>Recargar</button>
    </main>
    return this.props.children
  }
}

createRoot(document.getElementById('root')).render(<React.StrictMode><InterfaceBoundary><Demo /></InterfaceBoundary></React.StrictMode>)
