"""Export holdout evidence using actual AutoGluon predictions."""
import json
from pathlib import Path
import pandas as pd
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
OUT=Path(__file__).resolve().parents[2]/'outputs/psitwin_pruebas'
data=json.loads((OUT/'dataset.json').read_text(encoding='utf-8'))
history=pd.DataFrame(data['Demanda_Historica']);history['fecha']=pd.to_datetime(history.fecha)
pred=pd.read_csv(OUT/'predicciones_autogluon.csv',parse_dates=['timestamp'])
for p in data['Productos']:
    rows=history[history.id_producto==p['id_producto']];forecast=pred[pred.item_id==p['id_producto']]
    fig,ax=plt.subplots(figsize=(12,4.6),layout='constrained')
    train=rows[(rows.fecha>='2026-07-01')&(rows.fecha<='2026-09-30')]
    ax.plot(train.fecha,train.cantidad,label='Demanda de entrenamiento',color='#667085',lw=1)
    ax.plot(forecast.timestamp,forecast.real,label='Real reservada · validación',color='#14825a',lw=1.5)
    ax.plot(forecast.timestamp,forecast['mean'],label='AutoGluon · pronóstico',color='#2563eb',lw=1.8)
    ax.axvspan(pd.Timestamp('2026-10-01'),pd.Timestamp('2026-10-28'),alpha=.07,color='blue',label='Horizonte 28 días')
    ax.axvline(pd.Timestamp('2026-09-30'),ls='--',color='#9ca3af')
    ax.set(title=p['nombre']+' · DATOS SINTÉTICOS DE PRUEBA',ylabel=p['unidad'],xlabel='Fecha real · corte 30/09/2026');ax.xaxis.set_major_formatter(mdates.DateFormatter('%d/%m/%Y'));ax.legend(fontsize=8,ncol=2);ax.grid(alpha=.15)
    fig.savefig(OUT/f"validacion_{p['id_producto']}.png",dpi=130);plt.close(fig)
print('30 gráficos de validación real exportados')
