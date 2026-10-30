import { useQuery } from '@tanstack/react-query'
import { analisisApi, type DemandHorizon } from '@/api/analisis'
import { Button, Card } from '@/components/ui'
import { DemandChart } from './DemandChart'

interface Props {
  tenant: string
  warehouse: string
  product: string
  title: string
  horizon: DemandHorizon
  source: string
}

export function ForecastSeriesCard({ tenant, warehouse, product, title, horizon, source }: Props) {
  const query = useQuery({
    queryKey: ['analisis', 'forecast', tenant, warehouse, product, source],
    queryFn: () => analisisApi.forecast(warehouse, product, source),
    enabled: !!tenant && !!warehouse && !!product,
    refetchInterval: q => q.state.data?.estado === 'CALCULANDO' ? 3000 : false,
  })
  const data = query.data
  return <Card title={title} description={`Pronóstico a ${horizon} días · Serie por producto y almacén`}>
    {query.isError ? <p role="alert">No se pudo consultar esta serie. <Button onClick={() => void query.refetch()}>Reintentar</Button></p>
      : query.isPending ? <p role="status">Consultando serie…</p>
        : data && <>
          <p className="mb-3 text-sm">Corte del historial: {data.fecha_corte}</p>
          <DemandChart history={data.historico} predictions={data.estado === 'DISPONIBLE' ? data.predicciones.slice(0, horizon) : []} />
          {data.estado === 'CALCULANDO' && <p role="status">Calculando pronóstico…</p>}
          {data.detalle && <p role="status" className="mt-3 text-sm">{data.detalle}</p>}
        </>}
  </Card>
}
