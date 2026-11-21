import { useId } from 'react';
import { CartesianGrid, ErrorBar, Scatter, ScatterChart, Tooltip, XAxis, YAxis } from 'recharts';

// Shared roles keep the same meaning across research pages and themes.
export const RESEARCH_COLOURS = { ours: '#0284c7', baseline: '#d97706', control: '#8b5cf6', accepted: '#059669' };
export const percentage = value => value == null ? 'Undefined' : `${(value * 100).toFixed(1)}%`;
export const decimal = value => value == null ? 'Undefined' : value.toFixed(3);
const finite = value => typeof value === 'number' && Number.isFinite(value);
export function chartPoint(point) {
  if (!finite(point.x) || !finite(point.y)) return null;
  const error = (value, ci) => ci && finite(ci.low) && finite(ci.high)
    ? [value - ci.low, ci.high - value] : null;
  return { ...point, errorX: error(point.x, point.xCI), errorY: error(point.y, point.yCI) };
}
const intervalText = (interval, format) => interval?.low != null && interval?.high != null
  ? `${format(interval.low)} to ${format(interval.high)}` : 'Undefined';

/** Points are exact saved values. Missing values stay absent from the plot and explicit in the table. */
export default function ResearchChart({ title, year, n, originals, resamples, caption, series,
  stage = 'selection', xLabel, yLabel, xFormat = percentage, yFormat = percentage, xDomain = [0, 1], yDomain = [0, 1], xTicks }) {
  const id = useId();
  return <figure className="halite-card min-w-0 p-4 sm:p-6" aria-labelledby={`${id}-title`}>
    <h2 id={`${id}-title`} className="font-brand text-lg text-primary">{title}</h2>
    <p className="mt-1 text-sm text-secondary">{year} {stage} · n={n} pairs · {originals} original reports · 95% cluster-bootstrap intervals ({resamples} resamples)</p>
    <div className="mt-4 min-w-0" aria-hidden="true">
      <ScatterChart responsive style={{ width: '100%', height: 340 }} margin={{ top: 16, right: 24, bottom: 32, left: 12 }}>
        <CartesianGrid stroke="currentColor" className="text-secondary" opacity={0.18} />
        <XAxis type="number" dataKey="x" domain={xDomain} ticks={xTicks} tickFormatter={xFormat} name={xLabel} tick={{ fill: 'currentColor', fontSize: 12 }} label={{ value: xLabel, position: 'bottom', fill: 'currentColor', fontSize: 12 }} />
        <YAxis type="number" dataKey="y" domain={yDomain} tickFormatter={yFormat} name={yLabel} tick={{ fill: 'currentColor', fontSize: 12 }} width={64} />
        <Tooltip cursor={{ strokeDasharray: '3 3' }} content={({ active, payload }) => {
          const point = payload?.[0]?.payload;
          return active && point ? <div className="halite-card p-3 text-xs text-primary">
            <p>{point.label}</p><p>{xLabel}: {xFormat(point.x)}</p><p>{yLabel}: {yFormat(point.y)}</p>
            <p>95% interval: {intervalText(point.yCI, yFormat)}</p>
          </div> : null;
        }} />
        {series.map(item => <Scatter key={item.id} name={item.label} data={item.points.map(chartPoint).filter(Boolean)} fill={RESEARCH_COLOURS[item.role]} line={item.line !== false ? { stroke: RESEARCH_COLOURS[item.role] } : false} isAnimationActive={false}>
          <ErrorBar dataKey="errorX" direction="x" stroke={RESEARCH_COLOURS[item.role]} width={3} isAnimationActive={false} />
          <ErrorBar dataKey="errorY" direction="y" stroke={RESEARCH_COLOURS[item.role]} width={3} isAnimationActive={false} />
        </Scatter>)}
      </ScatterChart>
    </div>
    <ul className="mt-2 flex flex-wrap gap-4 text-sm text-primary" aria-label={`${title} legend`}>
      {series.map(item => <li key={item.id} className="flex items-center gap-2"><span aria-hidden="true" className="h-3 w-3 rounded-full" style={{ backgroundColor: RESEARCH_COLOURS[item.role] }} />{item.label}</li>)}
    </ul>
    <figcaption className="mt-4 text-sm text-secondary">{caption}</figcaption>
    <details className="mt-4 text-sm text-primary"><summary className="cursor-pointer underline">View values and intervals</summary>
      <div className="mt-3 overflow-x-auto"><table className="w-full text-left text-xs">
        <caption className="sr-only">{title}: {year}, {n} pairs. Undefined values are not plotted.</caption>
        <thead><tr>{['Policy / point', xLabel, '95% interval (x)', yLabel, '95% interval (y)'].map(label => <th key={label} scope="col" className="whitespace-nowrap border-b border-theme p-2">{label}</th>)}</tr></thead>
        <tbody>{series.flatMap(item => item.points.map((point, index) => <tr key={`${item.id}:${index}`}>
          <th scope="row" className="border-b border-theme p-2 font-normal">{item.label}{point.label ? ` · ${point.label}` : ''}</th>
          <td className="border-b border-theme p-2">{xFormat(point.x)}</td><td className="border-b border-theme p-2">{intervalText(point.xCI, xFormat)}</td>
          <td className="border-b border-theme p-2">{yFormat(point.y)}</td><td className="border-b border-theme p-2">{intervalText(point.yCI, yFormat)}</td>
        </tr>))}</tbody>
      </table></div>
    </details>
  </figure>;
}
