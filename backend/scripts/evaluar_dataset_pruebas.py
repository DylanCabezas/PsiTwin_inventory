"""Real AutoGluon temporal holdout; reference values are never read."""
import json
import argparse
import math
from pathlib import Path
import numpy as np
import pandas as pd
from autogluon.timeseries import TimeSeriesDataFrame, TimeSeriesPredictor

OUT=Path(__file__).resolve().parents[2]/'outputs/psitwin_pruebas'

def metrics(y,p):
    y,p=np.asarray(y,dtype=float),np.asarray(p,dtype=float)
    e=np.abs(y-p);den=np.abs(y)+np.abs(p)
    return {'MAE':float(e.mean()),'RMSE':float(np.sqrt(((y-p)**2).mean())),
        'WAPE':float(e.sum()/np.abs(y).sum()*100) if np.abs(y).sum() else None,
        'sMAPE':float(np.mean(np.divide(200*e,den,out=np.zeros_like(e),where=den!=0)))}

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--lead-time-days',type=int,default=3);args=parser.parse_args()
    if not 1<=args.lead_time_days<=28:parser.error('El plazo de prueba debe estar entre 1 y 28 días')
    data=json.loads((OUT/'dataset.json').read_text(encoding='utf-8'))
    frame=pd.DataFrame(data['Demanda_Historica']).rename(columns={'id_producto':'item_id','fecha':'timestamp','cantidad':'target'})
    frame['timestamp']=pd.to_datetime(frame.timestamp)
    train=frame[frame.timestamp<='2026-09-30'][['item_id','timestamp','target']]
    hold=frame[frame.timestamp>'2026-09-30'].set_index(['item_id','timestamp']).sort_index()
    assert train.timestamp.max()<hold.index.get_level_values('timestamp').min()
    ts=TimeSeriesDataFrame.from_data_frame(train,id_column='item_id',timestamp_column='timestamp')
    model=TimeSeriesPredictor(path=str(OUT/'autogluon_model'),prediction_length=28,freq='D',target='target',eval_metric='MAE')
    model.fit(ts,hyperparameters={'SeasonalNaive':{},'AutoETS':{}},time_limit=120,enable_ensemble=True,num_val_windows=1)
    pred=model.predict(ts).sort_index()
    assert pred.index.equals(hold.index)
    pred['real']=hold.target
    pred['mean']=pred['mean'].clip(lower=0)
    pred.reset_index().to_csv(OUT/'predicciones_autogluon.csv',index=False)
    scores={}
    for pid in sorted(frame.item_id.unique()):
        subset=pred.loc[pid];scores[pid]=metrics(subset.real,subset['mean'])
    # Metrics per unit, never sum kg and units.
    units={p['id_producto']:p['unidad'] for p in data['Productos']}
    aggregate={u:metrics(pred.loc[[p for p in scores if units[p]==u],'real'],pred.loc[[p for p in scores if units[p]==u],'mean']) for u in ('kg','unidad')}
    report={'motor':'AutoGluon TimeSeriesPredictor','modelos_solicitados':['SeasonalNaive','AutoETS'],'mejor_modelo':model.model_best,'corte':'2026-09-30','validacion_inicio':'2026-10-01','validacion_fin':'2026-10-28','horizonte':28,'filas_entrenamiento':len(train),'filas_validacion':len(hold),'metricas_por_producto':scores,'metricas_por_unidad':aggregate,'limitacion':'Evaluación real de modelos estadísticos de AutoGluon; no certifica el ensemble preentrenado de producción (Chronos2/Toto2).'}
    (OUT/'evaluacion_autogluon.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report))
    # Refit after evaluation for genuine replenishment horizon after final stock date.
    full=TimeSeriesDataFrame.from_data_frame(frame[['item_id','timestamp','target']],id_column='item_id',timestamp_column='timestamp')
    future_model=TimeSeriesPredictor(path=str(OUT/'autogluon_futuro'),prediction_length=28,freq='D',target='target',eval_metric='MAE')
    future_model.fit(full,hyperparameters={'SeasonalNaive':{}},enable_ensemble=False,num_val_windows=1)
    future=future_model.predict(full).sort_index();future.reset_index().to_csv(OUT/'pronostico_futuro.csv',index=False)
    replenishment=[]
    for product,stock in zip(data['Productos'],data['Inventario_Actual']):
        pid=product['id_producto'];expected=max(0,float(future.loc[pid]['mean'].iloc[:args.lead_time_days].sum()))
        suggested=max(0,min(product['stock_maximo']-stock['stock_final'],expected+product['stock_minimo']-stock['stock_final']))
        suggested=math.ceil(suggested) if product['unidad']=='unidad' else round(suggested,2)
        replenishment.append({'producto':product['nombre'],'id_producto':pid,'unidad':product['unidad'],'stock':stock['stock_final'],'minimo':product['stock_minimo'],'maximo':product['stock_maximo'],'demanda_plazo':expected,'plazo_dias_prueba':args.lead_time_days,'reposicion_sugerida':suggested,'estado':'AGOTADO' if stock['stock_final']==0 else 'BAJO' if stock['stock_final']<product['stock_minimo'] else 'EXCESO' if stock['stock_final']>product['stock_maximo'] else 'NORMAL','inicio_pronostico':'2026-10-29'})
    (OUT/'reposicion.json').write_text(json.dumps(replenishment,ensure_ascii=False,indent=2),encoding='utf-8')

if __name__=='__main__':main()
