"""Exercise the application's actual pretrained runtime, without retraining it."""
import json
from pathlib import Path
from app.services.autogluon_runtime import runtime
OUT=Path(__file__).resolve().parents[2]/'outputs/psitwin_pruebas'
data=json.loads((OUT/'dataset.json').read_text(encoding='utf-8'))
history=[{'fecha':r['fecha'],'cantidad':r['cantidad']} for r in data['Demanda_Historica'] if r['id_producto']=='SYN-001' and r['fecha']<='2026-09-30']
try:
    result,cached=runtime.predict('psitwin-synthetic-30-v1','ABC1_SYN-001',history)
    import math
    points=result['predictions']['ABC1_SYN-001'][:28]
    truth=[r['cantidad'] for r in data['Demanda_Historica'] if r['id_producto']=='SYN-001' and '2026-10-01'<=r['fecha']<='2026-10-28']
    errors=[abs(y-p['cantidad']) for y,p in zip(truth,points)]
    scores={'MAE':sum(errors)/28,'RMSE':math.sqrt(sum(e*e for e in errors)/28),'WAPE':sum(errors)/sum(truth)*100,'sMAPE':sum(200*e/(abs(y)+abs(p['cantidad'])) if abs(y)+abs(p['cantidad']) else 0 for y,p,e in zip(truth,points,errors))/28}
    assert points[0]['fecha']=='2026-10-01' and points[-1]['fecha']=='2026-10-28'
    (OUT/'modelo_existente_papaya.json').write_text(json.dumps({'runtime':runtime.status(),'cache':cached,'corte':'2026-09-30','metricas_validacion_28_dias':scores,'resultado':result},indent=2),encoding='utf-8')
    print('Predicción del runtime existente guardada')
except Exception as exc:
    (OUT/'modelo_existente_papaya.json').write_text(json.dumps({'error':str(exc),'runtime':runtime.status()},indent=2),encoding='utf-8')
    print(type(exc).__name__,str(exc))
finally:runtime.close()
