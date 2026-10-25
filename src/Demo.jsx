import { useEffect, useMemo, useRef, useState } from 'react'
import Viewport, { useSlicer } from 'three-slicer-viewer'
import SettingsPanel from 'three-slicer-viewer/components'
import { makeSlicerWorker } from 'three-slicer/client'
import {
  bundledCatalog, printersByVendor, printerSettings, printerKeys, printerDefaultPreset,
  processPresets, filamentPresets,
} from 'three-slicer/settings'
import { schema, uiTree } from 'three-slicer/data'
import { makeCfg, disabledKeys } from 'three-slicer/toggle'
import './step_loader.js'

// Keep this hook adapter at module scope: three-slicer-viewer calls it as a hook.
const slicer = (deps) => useSlicer({ ...deps, makeWorker: makeSlicerWorker })
const panelData = { schema, uiTree, toggle: { makeCfg, disabledKeys } }
const responsiveViewerCss = `
@media (max-width: 767px) {
  .app-shell { font-size: 12px; }
  .topbar { flex: 0 0 86px; height: 86px; display: grid; grid-template-columns: minmax(0,1fr) auto;
    grid-template-rows: 38px 38px; gap: 4px 8px; padding: 3px 8px; }
  .topbar:has(.tb-gcode) { flex-basis: 122px; height: 122px; grid-template-rows: 38px 38px 34px; }
  .topbar .tb-left { grid-column: 1 / -1; grid-row: 1; min-width: 0; width: 100%; flex: none;
    overflow-x: auto; scrollbar-width: none; gap: 5px; }
  .topbar .tb-left::-webkit-scrollbar { display: none; }
  .topbar .tb-left > * { flex: 0 0 auto; }
  .topbar .tb-tabs { grid-column: 1; grid-row: 2; justify-self: start; }
  .topbar .tb-right { grid-column: 2; grid-row: 2; min-width: 0; flex: none; gap: 5px; }
  .topbar .tb-gcode { grid-column: 1 / -1; grid-row: 3; min-width: 0; overflow: hidden; }
  .topbar .tb-gcode span { overflow: hidden; text-overflow: ellipsis; white-space: nowrap; }
  .tb-logo { font-size: 12px; white-space: nowrap; }
  .tb-btn { padding: 5px 7px; font-size: 11px; white-space: nowrap; }
  .tb-tabs button { padding: 6px 12px; font-size: 11px; }
  .left-rail { flex-basis: 42px; padding: 6px 0; gap: 3px; overflow-y: auto; scrollbar-width: none; }
  .left-rail button { width: 34px; height: 34px; }
  .sidebar { display: none !important; }
  .vp-top-toolbar { top: 8px; max-width: calc(100% - 16px); }
  .vp-top-toolbar button { width: 30px; height: 30px; }
  .plate-bar { right: 8px; bottom: 96px; max-width: calc(100% - 16px); overflow-x: auto; }
  .brush-panel { top: 50px; left: 6px; width: min(214px, calc(100% - 12px)); }
  .stats-card, .bed-warn { left: 8px; bottom: 96px; max-width: min(48%, 190px); font-size: 11px; }
}
@media (min-width: 768px) and (max-width: 1100px) {
  .sidebar { flex-basis: min(300px, 35vw); width: min(300px, 35vw); }
  .topbar { gap: 7px; padding: 0 8px; }
  .tb-tabs button { padding-left: 12px; padding-right: 12px; }
}`
const responsiveSettingsCss = `
@media (max-width: 767px) {
  :host(.sp-embedded) .settings-panel { width: 100%; height: 100%; min-width: 0; min-height: 0; }
  :host(.sp-embedded) .sp-top { flex: 0 0 auto; padding: 9px 10px; }
  :host(.sp-embedded) .sp-body { flex: 1 1 auto; min-height: 0; max-height: none; overflow-y: auto; padding: 8px 10px 22px; }
  .settings-panel .row { grid-template-columns: minmax(0,1fr) auto; }
  .settings-panel .row .key { max-width: 115px; }
  .settings-panel .row input:not([type="checkbox"]):not([type="color"]),
  .settings-panel .row select, .settings-panel .row textarea { max-width: min(150px, 44vw); }
  .sp-pages { flex-wrap: nowrap; overflow-x: auto; padding-bottom: 3px; }
  .sp-pages button { flex: 0 0 auto; }
}`

function applyPreset(base, preset, keys, idKey, name) {
  const next = { ...base }
  for (const key of keys) delete next[key]
  Object.assign(next, preset)
  if (idKey) next[idKey] = name
  return next
}

export default function Demo() {
  const [settings, setSettings] = useState({})
  const [plateSettings, setPlateSettings] = useState({})
  const [mobile, setMobile] = useState(() => window.matchMedia('(max-width: 767px)').matches)
  const [drawer, setDrawer] = useState(false)
  const [sliceRequest, setSliceRequest] = useState(0)
  const [catalog, setCatalog] = useState(null)
  const [status, setStatus] = useState('Abre o arrastra un modelo para empezar')
  const [progress, setProgress] = useState(null)
  const [machine, setMachine] = useState('')
  const [cameraOpen, setCameraOpen] = useState(false)
  const [testCapturedAt, setTestCapturedAt] = useState(() => new Date())
  const cameraButton = useRef(null)
  const cameraClose = useRef(null)

  useEffect(() => {
    const query = window.matchMedia('(max-width: 767px)')
    const update = () => setMobile(query.matches)
    query.addEventListener?.('change', update)
    return () => query.removeEventListener?.('change', update)
  }, [])

  // The upstream viewer deliberately isolates its UI in Shadow DOM. Keep using that component, but add the
  // responsive layout rules into its open root so its real tools remain intact at phone/tablet widths.
  useEffect(() => {
    const install = () => {
      for (const host of document.querySelectorAll('#root *')) {
        const root = host.shadowRoot
        if (!root || !root.querySelector('.app-shell') || root.querySelector('[data-responsive-demo]')) continue
        const logo = root.querySelector('.tb-logo')
        if (logo) logo.href = import.meta.env.BASE_URL
        const style = document.createElement('style')
        style.dataset.responsiveDemo = ''
        style.textContent = responsiveViewerCss
        root.append(style)
      }
      for (const host of document.querySelectorAll('.settings-surface *')) {
        const root = host.shadowRoot
        if (!root || !root.querySelector('.settings-panel') || root.querySelector('[data-responsive-settings]')) continue
        const style = document.createElement('style')
        style.dataset.responsiveSettings = ''
        style.textContent = responsiveSettingsCss
        root.append(style)
      }
    }
    install()
    const observer = new MutationObserver(install)
    observer.observe(document.getElementById('root'), { childList: true, subtree: true })
    return () => observer.disconnect()
  }, [])

  useEffect(() => {
    let live = true
    Promise.all([processPresets(), filamentPresets()]).then(([process, filament]) => {
      if (live) setCatalog({ process, filament })
    }).catch(() => {
      if (live) setStatus('No se pudieron cargar los catálogos de perfiles')
    })
    return () => { live = false }
  }, [])

  useEffect(() => {
    if (!drawer) return
    const close = (event) => { if (event.key === 'Escape') setDrawer(false) }
    window.addEventListener('keydown', close)
    return () => window.removeEventListener('keydown', close)
  }, [drawer])

  useEffect(() => {
    if (!cameraOpen) return
    cameraClose.current?.focus()
    const close = event => { if (event.key === 'Escape') setCameraOpen(false) }
    window.addEventListener('keydown', close)
    return () => { window.removeEventListener('keydown', close); cameraButton.current?.focus() }
  }, [cameraOpen])

  const machineOptions = useMemo(() => Object.entries(printersByVendor)
    .sort(([a], [b]) => a.localeCompare(b))
    .flatMap(([vendor, entries]) => Object.keys(entries).sort().map(name => ({ vendor, name }))), [])
  const processOptions = useMemo(() => catalog && machine ? catalog.process.listFor(machine) : [], [catalog, machine])
  const filamentOptions = useMemo(() => {
    if (!catalog || !machine) return []
    const recommended = catalog.filament.recommendedFor(machine)
    return recommended.length ? recommended : catalog.filament.listFor(machine)
  }, [catalog, machine])

  const chooseMachine = (name) => {
    setMachine(name)
    if (!name) return
    const recommended = printerDefaultPreset(name)
    setSettings(current => {
      let next = applyPreset(current, printerSettings(name), printerKeys, 'printer_settings_id', name)
      if (catalog && recommended) next = applyPreset(next, catalog.process.settingsFor(recommended), catalog.process.keys, 'print_settings_id', recommended)
      return next
    })
  }
  const chooseProcess = (name) => {
    if (catalog && name) setSettings(current => applyPreset(current, catalog.process.settingsFor(name), catalog.process.keys, 'print_settings_id', name))
  }
  const chooseFilament = (name) => {
    if (catalog && name) setSettings(current => applyPreset(current, catalog.filament.settingsFor(name), catalog.filament.keys, 'filament_settings_id', name))
  }

  const panels = mobile ? { sidebar: false } : undefined
  const processPanel = (panelSettings, setPanelSettings, meta) => (
    <SettingsPanel embedded settings={panelSettings} setSettings={setPanelSettings}
      overriddenKeys={meta?.overriddenKeys} onRevertKey={meta?.onRevertKey} {...panelData} />
  )
  const progressText = progress == null ? status : `Laminando… ${Math.round(progress * 100)}%`

  return <main className="demo-shell">
    <div className="viewport-host">
      <Viewport
        slicer={slicer}
        catalog={bundledCatalog}
        settings={settings}
        setSettings={setSettings}
        plateSettings={plateSettings}
        setPlateSettings={setPlateSettings}
        processPanel={processPanel}
        motionPanel={<SettingsPanel embedded settings={settings} setSettings={setSettings}
          only={{ builder: 'TabPrinter::build_kinematics_page' }} {...panelData} />}
        filamentPanel={(filamentSettings, setFilamentSettings) => <>
          <SettingsPanel embedded settings={filamentSettings} setSettings={setFilamentSettings}
            only={{ builder: 'TabFilament::build' }} {...panelData} />
          <SettingsPanel embedded settings={filamentSettings} setSettings={setFilamentSettings}
            only={{ builder: 'TabFilament::add_filament_overrides_page' }} {...panelData} />
        </>}
        panels={panels}
        features={cameraOpen ? { shortcuts: false } : undefined}
        sliceRequest={sliceRequest}
        onEvent={(event) => {
          if (event.type === 'progress') setProgress(event.value)
          if (event.type === 'slicing' && !event.value) setProgress(null)
          if (event.type === 'error') { setProgress(null); setStatus(`Error: ${event.value}`) }
          if (event.type === 'notice') setStatus(event.value)
        }}
        onSliced={({ stats }) => {
          setProgress(null)
          setStatus(`Laminado listo · ${stats?.layers ?? '—'} capas`)
        }}
      />
    </div>

    <button ref={cameraButton} className="camera-trigger" type="button" title="Ver captura de la cámara de la impresora"
      aria-label="Ver cámara de la impresora" onClick={() => setCameraOpen(true)}>
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round" aria-hidden="true">
        <path d="M4 7h3l1.5-2h7L17 7h3a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1Z"/>
        <circle cx="12" cy="13" r="3.5"/>
      </svg>
    </button>

    {cameraOpen && <div className="camera-backdrop" onMouseDown={event => { if (event.target === event.currentTarget) setCameraOpen(false) }}>
      <section className="camera-modal" role="dialog" aria-modal="true" aria-labelledby="camera-title">
        <header className="camera-head"><div><span className="camera-eyebrow">VISTA DE CÁMARA · DEMO</span><h2 id="camera-title">Cámara de la impresora</h2></div>
          <button ref={cameraClose} type="button" className="camera-close" onClick={() => setCameraOpen(false)} aria-label="Cerrar cámara">×</button></header>
        <figure className="camera-frame"><img src={`${import.meta.env.BASE_URL}webcam-test.svg`} alt="Imagen de prueba simulando la webcam de una impresora 3D; contiene marca de agua IMAGEN DE PRUEBA" />
          <figcaption>Imagen de prueba · Ninguna impresora conectada</figcaption></figure>
        <footer className="camera-foot"><span>Captura simulada: {testCapturedAt.toLocaleString('es-ES')}</span>
          <button type="button" onClick={() => setTestCapturedAt(new Date())}>Actualizar prueba</button></footer>
      </section>
    </div>}

    {mobile && <>
      <nav className="mobile-nav" aria-label="Acciones rápidas">
        <button className="nav-setting" onClick={() => setDrawer(true)}><span aria-hidden="true">☷</span>Ajustes</button>
        <span className="nav-status" aria-live="polite">{progressText}</span>
        <button className="nav-slice" onClick={() => setSliceRequest(value => value + 1)}><span aria-hidden="true">▶</span>Laminar</button>
      </nav>
      {drawer && <div className="drawer-scrim" onClick={() => setDrawer(false)} />}
      <section className={`settings-drawer${drawer ? ' is-open' : ''}`} role="dialog" aria-modal="true" aria-label="Ajustes del laminado">
        <div className="drawer-handle" />
        <header className="drawer-header"><div><strong>Ajustes del laminado</strong><small>Perfiles y opciones reales de Three Slicer</small></div>
          <button className="close-drawer" onClick={() => setDrawer(false)} aria-label="Cerrar ajustes">×</button></header>
        <div className="profile-selects">
          <label>Impresora<select value={machine} onChange={event => chooseMachine(event.target.value)}>
            <option value="">Selecciona una impresora</option>
            {machineOptions.map(option => <option key={option.name} value={option.name}>{option.vendor} · {option.name}</option>)}
          </select></label>
          <label>Proceso<select disabled={!machine || !catalog} value={settings.print_settings_id ?? ''} onChange={event => chooseProcess(event.target.value)}>
            <option value="">Perfil de proceso</option>{processOptions.map(name => <option key={name} value={name}>{name}</option>)}
          </select></label>
          <label>Material<select disabled={!machine || !catalog} value={settings.filament_settings_id ?? ''} onChange={event => chooseFilament(event.target.value)}>
            <option value="">Perfil de material</option>{filamentOptions.map(name => <option key={name} value={name}>{name}</option>)}
          </select></label>
        </div>
        <div className="settings-surface"><SettingsPanel embedded settings={settings} setSettings={setSettings} {...panelData} /></div>
        <button className="drawer-slice" onClick={() => { setDrawer(false); setSliceRequest(value => value + 1) }}>Laminar modelo</button>
      </section>
    </>}
  </main>
}
