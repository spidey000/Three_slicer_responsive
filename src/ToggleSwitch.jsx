import './toggle-switch.css'

// Accessible, native-checkbox pill inspired by the iOS vc-toggle design.
// The feature name lives inside the track; no outer switch card is rendered.
export default function ToggleSwitch({ id, label, checked, onChange, className = '', disabled = false }) {
  return <label className={['ui-toggle', className].filter(Boolean).join(' ')} htmlFor={id}>
    <input id={id} type="checkbox" role="switch" aria-label={label}
      checked={checked} disabled={disabled} onChange={event => onChange(event.target.checked)}/>
    <span className="ui-toggle-track" aria-hidden="true">
      <span className="ui-toggle-caption">{label}</span>
      <span className="ui-toggle-thumb"/>
    </span>
  </label>
}
