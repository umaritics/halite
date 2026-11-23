import { useId, useRef, useState } from 'react';

/**
 * tabs: [{ id, label, content }]. Works controlled (value + onChange) or
 * uncontrolled (defaultValue). Arrow keys, Home and End move and select.
 */
export default function Tabs({
  tabs,
  value,
  defaultValue,
  onChange,
  label,
  className = '',
}) {
  const baseId = useId();
  const [inner, setInner] = useState(defaultValue ?? tabs[0]?.id);
  const refs = useRef({});
  const selectedId = value ?? inner;
  const selected = tabs.find(tab => tab.id === selectedId) || tabs[0];

  const select = (id) => {
    if (value === undefined) setInner(id);
    if (onChange) onChange(id);
    refs.current[id]?.focus();
  };

  const onKeyDown = (event, index) => {
    const last = tabs.length - 1;
    const targets = {
      ArrowRight: index === last ? 0 : index + 1,
      ArrowLeft: index === 0 ? last : index - 1,
      Home: 0,
      End: last,
    };
    if (!(event.key in targets)) return;
    event.preventDefault();
    select(tabs[targets[event.key]].id);
  };

  return (
    <div className={className}>
      <div
        role="tablist"
        aria-label={label}
        className="flex flex-wrap gap-1 border-b border-theme"
      >
        {tabs.map((tab, index) => {
          const isSelected = tab.id === selected?.id;
          return (
            <button
              key={tab.id}
              ref={node => { refs.current[tab.id] = node; }}
              type="button"
              role="tab"
              id={`${baseId}-tab-${tab.id}`}
              aria-selected={isSelected}
              aria-controls={`${baseId}-panel-${tab.id}`}
              tabIndex={isSelected ? 0 : -1}
              onClick={() => select(tab.id)}
              onKeyDown={event => onKeyDown(event, index)}
              className={[
                '-mb-px border-b-2 px-4 py-2 text-sm font-medium transition',
                'focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent',
                isSelected
                  ? 'border-accent bg-accent/10 text-accent'
                  : 'border-transparent text-secondary hover:text-primary',
              ].join(' ')}
            >
              {tab.label}
            </button>
          );
        })}
      </div>
      {selected && (
        <div
          role="tabpanel"
          id={`${baseId}-panel-${selected.id}`}
          aria-labelledby={`${baseId}-tab-${selected.id}`}
          tabIndex={0}
          className="pt-4 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent"
        >
          {selected.content}
        </div>
      )}
    </div>
  );
}
