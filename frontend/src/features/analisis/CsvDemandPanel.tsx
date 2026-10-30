import { useRef, useState } from 'react'
import { analisisApi, type CsvColumns, type CsvDemandAnalysis, type DemandHorizon } from '@/api/analisis'
import { Button, Card, Field, Input, Select } from '@/components/ui'
import { DemandChart } from './DemandChart'

const format = (value: number) => value.toLocaleString('es-PE', { maximumFractionDigits: 3 })
const guess = (columns: string[], names: string[]) => columns.find(c => names.includes(c.trim().toLowerCase())) ?? ''

export function CsvDemandPanel() {
  const [content, setContent] = useState('')
  const [filename, setFilename] = useState('')
  const [preview, setPreview] = useState<CsvColumns | null>(null)
  const [dateColumn, setDateColumn] = useState('')
  const [quantityColumn, setQuantityColumn] = useState('')
  const [productColumn, setProductColumn] = useState('')
  const [series, setSeries] = useState('')
  const [horizon, setHorizon] = useState<DemandHorizon>(30)
  const [result, setResult] = useState<CsvDemandAnalysis | null>(null)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const version = useRef(0)
  const clearResult = () => { version.current++; setResult(null); setSeries(''); setError(''); setBusy(false) }

  const openFile = async (file: File | undefined) => {
    const current = ++version.current
    setContent(''); setFilename(file?.name ?? ''); setPreview(null); setResult(null); setError(''); setSeries(''); setBusy(false)
    if (!file) return
    if (!/\.csv$/i.test(file.name)) { setError('Selecciona un archivo .csv. Exporta Excel como CSV UTF-8.'); return }
    if (file.size > 2_000_000) { setError('El archivo no puede superar 2 MB.'); return }
    setBusy(true)
    try {
      const text = await file.text()
      if (current !== version.current) return
      if (text.includes('\uFFFD')) throw new Error('No se pudo leer el archivo. Expórtalo como CSV UTF-8.')
      const data = await analisisApi.csvColumns(text)
      if (current !== version.current) return
      setContent(text); setPreview(data)
      setDateColumn(guess(data.columnas, ['fecha', 'date', 'ds', 'timestamp']))
      setQuantityColumn(guess(data.columnas, ['cantidad', 'demanda', 'ventas', 'quantity', 'y', 'consumo']))
      setProductColumn(guess(data.columnas, ['producto', 'product', 'sku', 'id_producto']))
    } catch (e) { if (current === version.current) setError(e instanceof Error ? e.message : 'No se pudo leer el CSV.') }
    finally { if (current === version.current) setBusy(false) }
  }

  const analyze = async (forecast = false, selected = series) => {
    const current = ++version.current
    setError(''); setBusy(true)
    try {
      const data = await analisisApi.analyzeCsv({ contenido: content, columna_fecha: dateColumn, columna_cantidad: quantityColumn,
        ...(productColumn ? { columna_producto: productColumn } : {}), ...(selected ? { serie: selected } : {}), pronosticar: forecast })
      if (current !== version.current) return
      setResult(data); setSeries(data.serie)
    } catch (e) { if (current === version.current) setError(e instanceof Error ? e.message : 'No se pudo analizar el CSV.') }
    finally { if (current === version.current) setBusy(false) }
  }

  const options = preview?.columnas.map(c => ({ value: c, label: c })) ?? []
  const valid = !!content && !!dateColumn && !!quantityColumn && dateColumn !== quantityColumn
    && (!productColumn || (productColumn !== dateColumn && productColumn !== quantityColumn))
  return <div className="space-y-5">
    <Card title="Analizar un archivo CSV" description="Carga tus datos y elige las columnas. No necesitas declarar tipos de datos: convertimos fechas y cantidades automáticamente.">
      <div className="space-y-4">
        <p className="text-sm">Necesitas una columna de <strong>fecha</strong> y una de <strong>cantidad demandada</strong> (ventas, consumo o unidades solicitadas). El nombre de las columnas puede ser cualquiera: lo eliges abajo. Las demás columnas se ignoran.</p>
        <ul className="list-disc space-y-1 pl-5 text-sm text-fg-muted">
          <li>Fecha: AAAA-MM-DD, DD/MM/AAAA, una fecha con hora o una fecha numérica de Excel.</li>
          <li>Cantidad: un número mayor o igual a cero, entero o decimal; admite punto o coma decimal y números guardados como texto. Si un valor no se puede interpretar, indicaremos su fila para corregirlo.</li>
          <li>Producto: opcional. Permite analizar cada producto por separado. Cada serie debe tener una sola unidad; no mezcles kg con unidades.</li>
          <li>Usa demanda observada, no precios ni stock disponible. Las filas del mismo producto y día se suman; los días ausentes no se inventan.</li>
        </ul>
        <details><summary className="cursor-pointer text-sm font-medium">Ver ejemplo de las columnas</summary>
          <pre className="mt-2 overflow-auto rounded-lg bg-surface-2 p-3 text-xs">{'fecha,producto,cantidad\n2026-10-01,Arroz,12\n2026-10-02,Arroz,15\n2026-10-01,Chocolate,8'}</pre>
        </details>
        <Field label="Archivo CSV" hint="CSV UTF-8; separador coma, punto y coma, tabulación o |. Máximo 2 MB y 20 000 filas.">
          <Input type="file" accept=".csv,text/csv" onChange={e => void openFile(e.target.files?.[0])} />
        </Field>
        {preview && <>
          <p className="text-sm">{filename} · {format(preview.filas)} registros encontrados</p>
          <div className="grid gap-4 sm:grid-cols-3">
            <Field label="Columna de fecha" required><Select value={dateColumn} options={options} onChange={e => { clearResult(); setDateColumn(e.target.value) }} /></Field>
            <Field label="Columna de cantidad demandada" required><Select value={quantityColumn} options={options} onChange={e => { clearResult(); setQuantityColumn(e.target.value) }} /></Field>
            <Field label="Columna de producto (opcional)"><Select placeholder={false} value={productColumn} options={[{ value: '', label: 'Una sola serie' }, ...options]} onChange={e => { clearResult(); setProductColumn(e.target.value) }} /></Field>
          </div>
          <details><summary className="cursor-pointer text-sm font-medium">Vista previa del archivo (primeras 5 filas)</summary>
            <div className="mt-2 max-h-60 overflow-auto"><table className="w-full text-left text-sm"><thead><tr>{preview.columnas.map(c => <th className="p-2" key={c}>{c}</th>)}</tr></thead>
              <tbody>{preview.muestra.map((row, i) => <tr key={i}>{preview.columnas.map(c => <td className="p-2" key={c}>{row[c]}</td>)}</tr>)}</tbody></table></div>
          </details>
          {!valid && <p className="text-sm text-fg-muted">Selecciona columnas distintas para la fecha, cantidad y producto.</p>}
          <Button disabled={!valid || busy} loading={busy} onClick={() => void analyze()}>Analizar CSV</Button>
        </>}
        {busy && <p role="status">Procesando el archivo…</p>}
        {error && <p role="alert" className="text-sm text-danger">{error}</p>}
        <p className="text-xs text-fg-muted">Este análisis no modifica tu inventario ni guarda registros en el historial de la empresa.</p>
      </div>
    </Card>
    {result && <Card title={`Resultado del CSV: ${result.serie}`}>
      <div className="space-y-4">
        {result.series.length > 1 && <Field label="Producto o serie del archivo"><Select placeholder={false} value={series} disabled={busy} options={result.series.map(s => ({ value: s, label: s }))} onChange={e => { setSeries(e.target.value); setResult(null); void analyze(false, e.target.value) }} /></Field>}
        <div className="grid gap-4 text-sm sm:grid-cols-3">
          <p>Demanda total: <strong>{format(result.total)}</strong></p><p>Promedio por día observado: <strong>{format(result.promedio_diario)}</strong></p>
          <p>Días con datos: <strong>{result.dias_observados}</strong></p><p>Mínimo diario: <strong>{format(result.minimo_diario)}</strong></p><p>Máximo diario: <strong>{format(result.maximo_diario)}</strong></p>
          <p>Periodo: {result.fecha_inicio} a {result.fecha_fin}</p>
        </div>
        {result.dias_sin_datos > 0 && <p role="status">Faltan {result.dias_sin_datos} días en el periodo; no se rellenaron con ceros.</p>}
        <DemandChart history={result.historico} predictions={result.predicciones.slice(0, horizon)} />
        <div className="flex flex-wrap items-end gap-3">
          <Field label="Días a pronosticar"><Select placeholder={false} value={horizon} onChange={e => setHorizon(Number(e.target.value) as DemandHorizon)} options={[1, 7, 30, 90].map(h => ({ value: String(h), label: `${h} días` }))} /></Field>
          <Button disabled={busy} loading={busy} onClick={() => void analyze(true)}>Pronosticar esta serie</Button>
        </div>
        <p className="text-xs text-fg-muted">El pronóstico requiere al menos 91 días consecutivos y el modelo disponible. Se calcula después de la última fecha del CSV, sin reentrenar el modelo.</p>
        {result.detalle && <p role="status">{result.detalle}</p>}
        {result.advertencias.map(w => <p key={w} className="text-xs text-fg-muted">{w}</p>)}
      </div>
    </Card>}
  </div>
}
