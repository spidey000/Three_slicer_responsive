import './toggle-switch.css'

/**
 * A shadcn/ui-inspired, native accessible switch that fits ThreeSlicer's
 * existing theme without pulling in a second CSS framework.
 */
export default function ToggleSwitch({ id, label, checked, onChange, className = '', disabled = false }) {
  return <label className={'ui-toggle ' + className} htmlFor={id}>
    <input id={id} type="checkbox" role="switch" checked={checked} disabled={disabled}
      onChange={event => onChange(event.target.checked)}/>
    <span className="ui-toggle-track" aria-hidden="true"><span className="ui-toggle-thumb"/></span>
    <span className="ui-toggle-caption">{label}</span>
  </label>
}
