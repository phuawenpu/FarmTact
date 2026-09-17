import type { FarmerAssumptions, PlanningSession } from "../lib/planning";

type Props = {
  session: PlanningSession;
  value: FarmerAssumptions;
  onChange: (value: FarmerAssumptions) => void;
};

type RowKey = "tentative_orders" | "future_demand" | "seasonal" | "order_changes";
type Row = Record<string, unknown>;

const grid: React.CSSProperties = {
  display: "grid",
  gridTemplateColumns: "repeat(auto-fit, minmax(min(100%, 11rem), 1fr))",
  gap: ".75rem",
};
const group: React.CSSProperties = { display: "grid", gap: ".75rem", minWidth: 0 };
const rowStyle: React.CSSProperties = {
  ...grid,
  padding: ".75rem",
  border: "1px solid var(--line, #d8d5cc)",
  borderRadius: ".65rem",
};

function text(row: Row, key: string) {
  const current = row[key];
  return current == null ? "" : String(current);
}

function number(row: Row, key: string) {
  const current = row[key];
  return typeof current === "number" || typeof current === "string" ? current : "";
}

export default function PlanningAssumptionFields({ session, value, onChange }: Props) {
  const arrays = (key: RowKey): Row[] => (value[key] || []) as Row[];
  const updateRows = (key: RowKey, rows: Row[]) => onChange({ ...value, [key]: rows });
  const updateRow = (key: RowKey, index: number, patch: Row) =>
    updateRows(key, arrays(key).map((row, rowIndex) => rowIndex === index ? { ...row, ...patch } : row));
  const removeRow = (key: RowKey, index: number) =>
    updateRows(key, arrays(key).filter((_, rowIndex) => rowIndex !== index));
  const setOptionalNumber = (key: RowKey, index: number, field: string, raw: string) => {
    const next = { ...arrays(key)[index] };
    if (raw === "") delete next[field];
    else next[field] = Number(raw);
    updateRows(key, arrays(key).map((row, rowIndex) => rowIndex === index ? next : row));
  };

  const planningStart = session.farm.planning_date || session.farm.cutoff.slice(0, 10);
  const planningEnd = (() => {
    if (!planningStart) return "";
    const date = new Date(`${planningStart}T00:00:00Z`);
    date.setUTCDate(date.getUTCDate() + Math.max(0, session.farm.horizon_days - 1));
    return date.toISOString().slice(0, 10);
  })();
  const cropIds = Array.from(new Set([
    ...Object.keys(session.farm.recipe_calendar || {}),
    ...session.farm.orders.map((order) => order.crop_id),
  ])).filter(Boolean);
  const reservationWindow = session.tactical_context?.grow_space?.reservation_window;
  const reservationBed = session.tactical_context?.grow_space?.id || session.farm.beds[0]?.id || "";
  const capacity = value.capacity || {};
  const setCapacity = (field: "nursery_sites" | "labour_hours_per_week" | "cash_sgd", raw: string) => {
    const next = { ...capacity };
    if (raw === "") delete next[field];
    else next[field] = Number(raw);
    onChange({ ...value, capacity: next });
  };
  const cropSelect = (label: string, current: string, change: (next: string) => void) => (
    <label>{label}<select value={current} onChange={(event) => change(event.target.value)}>
      <option value="">Select crop</option>
      {cropIds.map((cropId) => <option key={cropId} value={cropId}>{cropId.replaceAll("_", " ")}</option>)}
    </select></label>
  );

  return <div style={group}>
    <fieldset style={group}>
      <legend>Available capacity</legend>
      <p>Blank fields keep the farm's recorded capacity. Enter a value only to test a change.</p>
      <div style={grid}>
        <label>Nursery sites<input type="number" min="0" step="1" value={capacity.nursery_sites ?? ""} placeholder={String(session.farm.resources.nursery_sites)} onChange={(event) => setCapacity("nursery_sites", event.target.value)} /></label>
        <label>Labour hours per week<input type="number" min="0" step="0.1" value={capacity.labour_hours_per_week ?? ""} placeholder={String(session.farm.resources.labour_hours_per_week)} onChange={(event) => setCapacity("labour_hours_per_week", event.target.value)} /></label>
        <label>Cash available (SGD)<input type="number" min="0" step="0.01" value={capacity.cash_sgd ?? ""} placeholder={String(session.farm.resources.cash_sgd)} onChange={(event) => setCapacity("cash_sgd", event.target.value)} /></label>
      </div>
    </fieldset>

    <Rows title="Tentative orders" rows={arrays("tentative_orders")} onAdd={() => updateRows("tentative_orders", [...arrays("tentative_orders"), { order_id: "", crop_id: "", due_date: planningStart, quantity_kg: 0, status: "tentative" }])} onRemove={(index) => removeRow("tentative_orders", index)}>
      {(row, index) => <>
        <label>Order reference<input value={text(row, "order_id")} onChange={(event) => updateRow("tentative_orders", index, { order_id: event.target.value })} /></label>
        {cropSelect("Crop", text(row, "crop_id"), (crop_id) => updateRow("tentative_orders", index, { crop_id }))}
        <label>Due date<input type="date" min={planningStart} max={planningEnd} value={text(row, "due_date")} onChange={(event) => updateRow("tentative_orders", index, { due_date: event.target.value })} /></label>
        <label>Quantity (kg)<input type="number" min="0" step="0.01" value={number(row, "quantity_kg")} onChange={(event) => setOptionalNumber("tentative_orders", index, "quantity_kg", event.target.value)} /></label>
        <label>Price (SGD/kg)<input type="number" min="0" step="0.01" value={number(row, "price_sgd_per_kg")} onChange={(event) => setOptionalNumber("tentative_orders", index, "price_sgd_per_kg", event.target.value)} /></label>
      </>}
    </Rows>

    <Rows title="Future demand" rows={arrays("future_demand")} onAdd={() => updateRows("future_demand", [...arrays("future_demand"), { crop_id: "", start_date: planningStart, end_date: planningEnd, percent: 100 }])} onRemove={(index) => removeRow("future_demand", index)}>
      {(row, index) => <>
        {cropSelect("Crop", text(row, "crop_id"), (crop_id) => updateRow("future_demand", index, { crop_id }))}
        <DateWindow row={row} startLabel="From" endLabel="Through" min={planningStart} max={planningEnd} onStart={(start_date) => updateRow("future_demand", index, { start_date })} onEnd={(end_date) => updateRow("future_demand", index, { end_date })} />
        <label>Expected demand (%)<input type="number" min="50" max="150" step="1" value={number(row, "percent")} onChange={(event) => setOptionalNumber("future_demand", index, "percent", event.target.value)} /></label>
      </>}
    </Rows>

    <Rows title="Seasonal yield and delay" rows={arrays("seasonal")} onAdd={() => updateRows("seasonal", [...arrays("seasonal"), { crop_id: "", system: "sheltered_hydroponic", start_date: planningStart, end_date: planningEnd, reason: "", provenance: "synthetic_assumption" }])} onRemove={(index) => removeRow("seasonal", index)}>
      {(row, index) => <>
        {cropSelect("Crop", text(row, "crop_id"), (crop_id) => updateRow("seasonal", index, { crop_id }))}
        <DateWindow row={row} startLabel="From" endLabel="Through" min={planningStart} max={planningEnd} onStart={(start_date) => updateRow("seasonal", index, { start_date })} onEnd={(end_date) => updateRow("seasonal", index, { end_date })} />
        <label>Yield retained (%)<input type="number" min="50" max="100" step="1" value={number(row, "yield_percent")} placeholder="Required" onChange={(event) => setOptionalNumber("seasonal", index, "yield_percent", event.target.value)} /></label>
        <label>Harvest delay (days)<input type="number" min="0" max="14" step="1" value={number(row, "delay_days")} placeholder="Required" onChange={(event) => setOptionalNumber("seasonal", index, "delay_days", event.target.value)} /></label>
        <label style={{ gridColumn: "1 / -1" }}>Reason<input value={text(row, "reason")} onChange={(event) => updateRow("seasonal", index, { reason: event.target.value })} /></label>
      </>}
    </Rows>

    <Rows title="Confirmed order changes" rows={arrays("order_changes")} onAdd={() => updateRows("order_changes", [...arrays("order_changes"), { operation: "add", order_id: "", crop_id: "", due_date: planningStart }])} onRemove={(index) => removeRow("order_changes", index)}>
      {(row, index) => {
        const operation = text(row, "operation") || "add";
        return <>
          <label>Change<select value={operation} onChange={(event) => {
            const next: Row = { ...row, operation: event.target.value };
            if (event.target.value === "cancel") for (const field of ["crop_id", "due_date", "quantity_kg", "price_sgd_per_kg"]) delete next[field];
            updateRows("order_changes", arrays("order_changes").map((item, rowIndex) => rowIndex === index ? next : item));
          }}><option value="add">Add order</option><option value="amend">Amend order</option><option value="cancel">Cancel order</option></select></label>
          <label>Order reference{operation === "add" ? <input value={text(row, "order_id")} onChange={(event) => updateRow("order_changes", index, { order_id: event.target.value })} /> : <select value={text(row, "order_id")} onChange={(event) => updateRow("order_changes", index, { order_id: event.target.value })}><option value="">Select confirmed order</option>{session.farm.orders.map((order) => <option key={order.id} value={order.id}>{order.id}</option>)}</select>}</label>
          {operation !== "cancel" && <>
            {cropSelect("Crop", text(row, "crop_id"), (crop_id) => updateRow("order_changes", index, { crop_id }))}
            <label>Due date<input type="date" min={planningStart} max={planningEnd} value={text(row, "due_date")} onChange={(event) => updateRow("order_changes", index, { due_date: event.target.value })} /></label>
            <label>Quantity (kg)<input type="number" min="0" step="0.01" value={number(row, "quantity_kg")} onChange={(event) => setOptionalNumber("order_changes", index, "quantity_kg", event.target.value)} /></label>
            <label>Price (SGD/kg)<input type="number" min="0" step="0.01" value={number(row, "price_sgd_per_kg")} onChange={(event) => setOptionalNumber("order_changes", index, "price_sgd_per_kg", event.target.value)} /></label>
          </>}
        </>;
      }}
    </Rows>

    <fieldset style={group}>
      <legend>Bed reservations</legend>
      {(value.reservations || []).map((row, index) => <div style={rowStyle} key={`${row.bed_id}-${index}`}>
        <label>Bed<select value={row.bed_id} onChange={(event) => onChange({ ...value, reservations: value.reservations.map((item, rowIndex) => rowIndex === index ? { ...item, bed_id: event.target.value } : item) })}><option value="">Select bed</option>{session.farm.beds.map((bed) => <option key={bed.id} value={bed.id}>{bed.name} ({bed.id})</option>)}</select></label>
        <label>Reserved from<input type="date" value={row.start_date} onChange={(event) => onChange({ ...value, reservations: value.reservations.map((item, rowIndex) => rowIndex === index ? { ...item, start_date: event.target.value } : item) })} /></label>
        <label>Reserved through<input type="date" value={row.end_date} onChange={(event) => onChange({ ...value, reservations: value.reservations.map((item, rowIndex) => rowIndex === index ? { ...item, end_date: event.target.value } : item) })} /></label>
        <button type="button" onClick={() => onChange({ ...value, reservations: value.reservations.filter((_, rowIndex) => rowIndex !== index) })}>Remove reservation</button>
      </div>)}
      <button type="button" onClick={() => onChange({ ...value, reservations: [...(value.reservations || []), { bed_id: reservationBed, start_date: reservationWindow?.start_date || "", end_date: reservationWindow?.end_date || "" }] })}>Add reservation</button>
      {!reservationWindow && <small>No server reservation window is suggested. Choose the dates to test.</small>}
    </fieldset>
  </div>;
}

function Rows({ title, rows, onAdd, onRemove, children }: { title: string; rows: Row[]; onAdd: () => void; onRemove: (index: number) => void; children: (row: Row, index: number) => React.ReactNode }) {
  return <fieldset style={group}><legend>{title}</legend>{rows.map((row, index) => <div style={rowStyle} key={index}>{children(row, index)}<button type="button" onClick={() => onRemove(index)}>Remove</button></div>)}<button type="button" onClick={onAdd}>Add {title.toLocaleLowerCase()}</button></fieldset>;
}

function DateWindow({ row, startLabel, endLabel, min, max, onStart, onEnd }: { row: Row; startLabel: string; endLabel: string; min: string; max: string; onStart: (value: string) => void; onEnd: (value: string) => void }) {
  return <><label>{startLabel}<input type="date" min={min} max={max} value={text(row, "start_date")} onChange={(event) => onStart(event.target.value)} /></label><label>{endLabel}<input type="date" min={min} max={max} value={text(row, "end_date")} onChange={(event) => onEnd(event.target.value)} /></label></>;
}
