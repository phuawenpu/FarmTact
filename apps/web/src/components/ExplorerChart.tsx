import { useEffect, useId, useLayoutEffect, useMemo, useRef, useState } from 'react'

export interface ChartPoint { id: string; date: string; value: number; label: string; future?: boolean; series?: string }

type PlottedPoint = ChartPoint & { timestamp: number; index: number; seriesName: string }

const colours = ['#315f42', '#b46148', '#486f8a', '#8a6a2d', '#735b91', '#267b78', '#9a4f68', '#65732f']

function timestamp(date: string) {
  const parsed = Date.parse(date)
  return Number.isFinite(parsed) ? parsed : null
}

function compactDate(date: string) {
  const parsed = timestamp(date)
  if (parsed === null) return date
  return new Intl.DateTimeFormat('en-SG', { day: 'numeric', month: 'short', year: 'numeric', timeZone: 'UTC' }).format(parsed)
}

export function ExplorerChart({ points, unit, planningDate, onSelect }: { points: ChartPoint[]; unit: string; planningDate?: string; onSelect?: (id: string) => void }) {
  const accessibleId = useId()
  const containerRef = useRef<HTMLDivElement>(null)
  const [chartWidth, setChartWidth] = useState(720)
  const plotted = useMemo<PlottedPoint[]>(() => points.flatMap((point, index) => {
    const parsed = timestamp(point.date)
    return parsed === null || !Number.isFinite(point.value) ? [] : [{ ...point, timestamp: parsed, index, seriesName: point.series || point.label }]
  }), [points])
  const [activeId, setActiveId] = useState<string | null>(() => plotted[0]?.id ?? null)
  const pointRefs = useRef(new Map<number, SVGCircleElement>())
  const activeIndex = Math.max(0, plotted.findIndex(point => point.id === activeId))
  const activePoint = plotted[activeIndex]

  useEffect(() => {
    if (!plotted.some(point => point.id === activeId)) setActiveId(plotted[0]?.id ?? null)
  }, [activeId, plotted])

  useLayoutEffect(() => {
    const container = containerRef.current
    if (!container) return
    const update = (width: number) => setChartWidth(Math.max(280, Math.floor(width)))
    update(container.getBoundingClientRect().width)
    if (typeof ResizeObserver === 'undefined') return
    const observer = new ResizeObserver(entries => update(entries[0]?.contentRect.width || container.getBoundingClientRect().width))
    observer.observe(container)
    return () => observer.disconnect()
  }, [])

  if (!plotted.length) return <div className="explorer-empty">No numeric records with valid dates match these filters.</div>

  const width = chartWidth, height = 280, left = width < 380 ? 52 : 58, right = 14, top = 42, bottom = 52
  const values = plotted.map(point => point.value)
  const min = Math.min(...values), max = Math.max(...values)
  const firstDate = Math.min(...plotted.map(point => point.timestamp)), lastDate = Math.max(...plotted.map(point => point.timestamp))
  const x = (date: number) => left + ((date - firstDate) / Math.max(1, lastDate - firstDate)) * (width - left - right)
  const y = (value: number) => height - bottom - ((value - min) / Math.max(1, max - min)) * (height - top - bottom)
  const grouped = plotted.reduce<Map<string, PlottedPoint[]>>((all, point) => {
    const series = all.get(point.seriesName) || []
    series.push(point); all.set(point.seriesName, series)
    return all
  }, new Map())
  for (const series of grouped.values()) series.sort((a, b) => a.timestamp - b.timestamp || a.index - b.index)
  const planningTimestamp = planningDate ? timestamp(planningDate) : null
  const showDivider = planningTimestamp !== null && planningTimestamp >= firstDate && planningTimestamp <= lastDate

  const move = (index: number) => {
    const next = Math.max(0, Math.min(plotted.length - 1, index))
    setActiveId(plotted[next].id)
    pointRefs.current.get(next)?.focus()
  }
  const select = (point: PlottedPoint) => { setActiveId(point.id); onSelect?.(point.id) }

  return <div ref={containerRef} className="explorer-chart-wrap">
    <svg className="explorer-chart" style={{ display: 'block', minWidth: 0, width: '100%', height }} viewBox={`0 0 ${width} ${height}`} role="group" aria-labelledby={`${accessibleId}-title ${accessibleId}-description`}>
      <title id={`${accessibleId}-title`}>Time series in {unit}</title>
      <desc id={`${accessibleId}-description`}>From {compactDate(new Date(firstDate).toISOString())} to {compactDate(new Date(lastDate).toISOString())}. Values range from {min.toLocaleString('en-SG')} to {max.toLocaleString('en-SG')} {unit}. Use Tab to reach points and arrow keys to move between them.</desc>
      <line x1={left} x2={width-right} y1={height-bottom} y2={height-bottom} className="chart-axis"/>
      <line x1={left} x2={left} y1={top} y2={height-bottom} className="chart-axis"/>
      <text x={left-8} y={top+4} textAnchor="end" fill="#536158" fontSize="11">{max.toLocaleString('en-SG')} {unit}</text>
      <text x={left-8} y={height-bottom+4} textAnchor="end" fill="#536158" fontSize="11">{min.toLocaleString('en-SG')} {unit}</text>
      <text x={left} y={height-20} textAnchor="start" fill="#536158" fontSize="11">{compactDate(new Date(firstDate).toISOString())}</text>
      <text x={width-right} y={height-20} textAnchor="end" fill="#536158" fontSize="11">{compactDate(new Date(lastDate).toISOString())}</text>
      {showDivider && <><line x1={x(planningTimestamp)} x2={x(planningTimestamp)} y1={top-10} y2={height-bottom} className="chart-divider"/><text x={Math.min(width-98,x(planningTimestamp)+6)} y={top-14} className="chart-divider-label">Planning date</text></>}
      {[...grouped.entries()].map(([name, series], seriesIndex) => {
        const colour = colours[seriesIndex % colours.length]
        const observed = series.filter(point => !point.future)
        const future = series.filter(point => point.future)
        return <g key={name} aria-label={name}>
          {observed.length > 1 && <polyline points={observed.map(point => `${x(point.timestamp)},${y(point.value)}`).join(' ')} fill="none" stroke={colour} strokeWidth="3"/>}
          {future.length > 1 && <polyline points={future.map(point => `${x(point.timestamp)},${y(point.value)}`).join(' ')} fill="none" stroke={colour} strokeWidth="3" strokeDasharray="7 6"/>}
        </g>
      })}
      {plotted.map((point,index) => {
        const seriesIndex = [...grouped.keys()].indexOf(point.seriesName)
        const colour = colours[seriesIndex % colours.length]
        return <g key={`${point.seriesName}:${point.id}:${index}`}>
          <circle cx={x(point.timestamp)} cy={y(point.value)} r="22" fill="transparent" style={{ cursor: 'pointer' }} aria-hidden="true" onClick={() => select(point)}/>
          <circle ref={node => { if (node) pointRefs.current.set(index,node); else pointRefs.current.delete(index) }} cx={x(point.timestamp)} cy={y(point.value)} r={activePoint?.id === point.id ? 7 : 5} fill={point.future ? 'white' : colour} stroke={colour} strokeWidth={point.future ? 3 : 2} tabIndex={0} role="button" aria-pressed={activePoint?.id === point.id} aria-label={`${point.seriesName}, ${compactDate(point.date)}: ${point.value.toLocaleString('en-SG')} ${unit}${point.future ? ', future or planned' : ', historical'}`} onFocus={() => setActiveId(point.id)} onClick={() => select(point)} onKeyDown={event => {
            if (event.key === 'ArrowRight' || event.key === 'ArrowDown') { event.preventDefault(); move(index+1) }
            if (event.key === 'ArrowLeft' || event.key === 'ArrowUp') { event.preventDefault(); move(index-1) }
            if (event.key === 'Home') { event.preventDefault(); move(0) }
            if (event.key === 'End') { event.preventDefault(); move(plotted.length-1) }
            if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); select(point) }
          }}/>
        </g>
      })}
    </svg>
    <div className="chart-legend" aria-label="Chart series">{[...grouped.keys()].map((name,index)=><span key={name}><i aria-hidden="true" style={{ width: 10, height: 10, borderRadius: 3, background: colours[index%colours.length], display: 'inline-block' }}/>{name}</span>)}</div>
    <p className="chart-readout" aria-live="polite"><strong>{compactDate(activePoint.date)}</strong> · {activePoint.value.toLocaleString('en-SG')} {unit} · {activePoint.seriesName} · {activePoint.future ? 'future / planned' : 'historical'}</p>
  </div>
}

export function ChartTable({ points, unit, onSelect }: { points: ChartPoint[]; unit: string; onSelect?: (id: string) => void }) {
  return <details className="chart-table"><summary>View chart as a table</summary><div className="table-scroll"><table><caption>Equivalent values for the chart above</caption><thead><tr><th>Date</th><th>Series</th><th>Value</th>{onSelect&&<th>Contributing record</th>}</tr></thead><tbody>{points.map((point,index) => <tr key={`${point.series||point.label}:${point.id}:${index}`}><td>{compactDate(point.date)}</td><td>{point.series||point.label}</td><td>{point.value.toLocaleString('en-SG')} {unit}</td>{onSelect&&<td><button type="button" style={{ minHeight: 44 }} onClick={() => onSelect(point.id)}>View contributing record {point.id}</button></td>}</tr>)}</tbody></table></div></details>
}
