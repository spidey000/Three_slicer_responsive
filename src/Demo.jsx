import { useEffect, useMemo, useState } from 'react'
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
  .topbar { gap: 5px; padding: 0 6px; }
  .topbar .tb-left, .topbar .tb-right { gap: 4px; min-width: 0; }
  .tb-logo { font-size: 12px; white-space: nowrap; }
  .tb-btn { padding: 4px 6px; font-size: 11px; white-space: nowrap; }
  .tb-tabs button { padding: 5px 8px; font-size: 11px; }
  .left-rail { flex-basis: 40px; padding: 6px 0; gap: 3px; }
  .left-rail button { width: 34px; height: 34px; }
  .sidebar { display: none !important; }
  .vp-top-toolbar { top: 8px; max-width: calc(100% - 12px); }
  .vp-top-toolbar button { width: 30px; height: 30px; }
  .plate-bar { right: 8px; bottom: 67px; }
  .brush-panel { top: 50px; left: 6px; width: min(214px, calc(100% - 12px)); }
  .stats-card, .bed-warn { left: 8px; bottom: 67px; max-width: calc(100% - 110px); font-size: 11px; }
}
@media (min-width: 768px) and (max-width: 1100px) {
  .sidebar { flex-basis: 300px; width: 300px; }
  .topbar { gap: 7px; padding: 0 8px; }
  .tb-tabs button { padding-left: 12px; padding-right: 12px; }
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
        const style = document.createElement('style')
        style.dataset.responsiveDemo = ''
        style.textContent = responsiveViewerCss
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
        <div className="settings-panel"><SettingsPanel embedded settings={settings} setSettings={setSettings} {...panelData} /></div>
        <button className="drawer-slice" onClick={() => { setDrawer(false); setSliceRequest(value => value + 1) }}>Laminar modelo</button>
      </section>
    </>}
    <a className="source-link" href="https://github.com/kimgh06/Three_Slicer" target="_blank" rel="noreferrer">Motor y visor Three Slicer · WebAssembly</a>
  </main>
}
