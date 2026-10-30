"""Create the delivery report and ZIP from verified artifacts, never model substitutes."""
import json,re,zipfile,hashlib
from pathlib import Path
ROOT=Path(__file__).resolve().parents[2]
OUT=ROOT/'outputs/psitwin_pruebas'
def load(name):return json.loads((OUT/name).read_text(encoding='utf-8'))
data=load('dataset.json');audit=load('auditoria_integracion.json');evaluation=load('evaluacion_autogluon.json');model=load('modelo_existente_papaya.json');risk=load('recomendador_operativo_papaya.json');playwright=load('playwright_results.json')
assert audit['idempotente'] and audit['errores_saiki']==0 and playwright['stats']['unexpected']==0 and playwright['stats']['expected']==2
tests={}
for f in ['backend_verificacion_final.log','frontend_final_tests.log','frontend_tests.log']:
    raw=(OUT/f).read_bytes()
    text=raw.decode('utf-16' if raw.startswith(b'\xff\xfe') else 'utf-8-sig',errors='replace')
    matches=re.findall(r'(\d+) passed',text)
    assert matches,f
    tests[f]=int(matches[-1])
changed=[
'backend/app/knowledge/catalogo_alimentos.json','backend/app/repositories/analisis_repository.py','backend/app/repositories/demanda_historica_repository.py',
'backend/app/services/analisis_service.py','backend/app/services/forecast_service.py','backend/app/services/inventory_risk_service.py',
'backend/app/services/warehouse_map_service.py','backend/app/services/saiki_service.py','backend/app/services/saiki_demand.py','backend/app/services/saiki_catalog_queries.py','backend/app/services/saiki_warehouse_map.py','backend/app/services/saiki_inventario_detallado.py',
'frontend/src/api/analisis.ts','frontend/src/api/inventarioConsultas.ts','frontend/src/features/analisis/HistoricalDemandPanel.tsx','frontend/src/features/almacenes/WarehouseMap.tsx',
'backend/tests/test_dataset_sintetico30.py','backend/tests/test_synthetic30_integration.py','backend/tests/synthetic30_browser_app.py',
'frontend/src/features/analisis/SyntheticDataset.test.tsx','frontend/e2e/synthetic30.spec.ts','frontend/playwright.synthetic30.config.ts','docs/dataset_pruebas_30.md','tools/synthetic_workbook/preview.mjs']
changed += [str(p.relative_to(ROOT)).replace('\\','/') for p in (ROOT/'backend/scripts').glob('*dataset*pruebas*.py')]
changed += ['backend/scripts/verificar_modelo_existente_pruebas.py','backend/scripts/verificar_recomendador_pruebas.py']
lines=['# Informe de validación — PsiTwin sintético','',
'Dataset generado, importado y reconciliado en MongoDB local, base `psitwin_synthetic30_test`, empresa `psitwin-synthetic-30-v1`. Datos reales de otras empresas sin modificar.','',
'## Conteos comprobados','', '| Entidad | Registros |','|---|---:|']
for k,v in data.items():lines.append(f'| {k} | {len(v)} |')
lines+=['','30 productos, cuatro helados, 396 días por producto. Período inclusivo 28/09/2025–28/10/2026. Un almacén ABC1, tres zonas, seis racks y diez niveles. Cero sensores, dispositivos, lecturas o alertas IoT. Saldos finales: **1.942,38 kg** y **852 unidades**, separados. Las 417 unidades de helado están exclusivamente en C1.','',
'## Resultados reales de AutoGluon','',
'Entrenamiento nuevo con SeasonalNaive y AutoETS, 11.040 observaciones hasta 30/09/2026. WeightedEnsemble seleccionado; validación reservada de 840 observaciones del 01 al 28/10/2026. La referencia del Excel no se usó como predicción.','',
'| Unidad | MAE | RMSE | WAPE % | sMAPE % |','|---|---:|---:|---:|---:|']
for unit,m in evaluation['metricas_por_unidad'].items():lines.append(f"| {unit} | {m['MAE']:.4f} | {m['RMSE']:.4f} | {m['WAPE']:.4f} | {m['sMAPE']:.4f} |")
lines+=['',f"Runtime original de PsiTwin, papaya: {json.dumps(model['metricas_validacion_28_dias'],ensure_ascii=False)}. Validación de los primeros 28 días del horizonte fijo de 90 días; sin reentrenar ese ensemble. El servicio completo produjo 90 fechas correctas desde 29/10/2026.",'',
f"Recomendador operativo de papaya: **{risk['reposicion']['cantidad_recomendada']} kg**, stock cero y máximo 81 kg. No se generaron compras ni alertas. Política de prueba de tres días para 30 productos: `reposicion.json`. No se confunden ambas políticas.",'',
'## Pruebas ejecutadas','',f"- Backend final: **{tests['backend_verificacion_final.log']} aprobadas**.",f"- Frontend focalizado final: **{tests['frontend_final_tests.log']} aprobadas**; TypeScript sin errores.",f"- Suite general de frontend ejecutada antes de los últimos ajustes: **{tests['frontend_tests.log']} aprobadas**.",'- Playwright final: **2 aprobadas**, cero fallos, cero omitidas. Aplicación React y servicios reales, autenticación de prueba explícita sobre la base aislada.',
'- Segunda importación: conteos idénticos, sin duplicados. 13.148 movimientos reconciliados y saldos intermedios no negativos.',
'- 90 informes históricos comprobados: 30 productos × diario, semanal y mensual.',
'- Saiki: 13 consultas ejecutadas, cero errores; respuestas guardadas en `saiki_consultas.json`. Pruebas adicionales de aislamiento entre empresas.',
'- Plano: diez niveles en gris, tres zonas, tipos y nombres comprobados; productos agotados visibles como asignados sin existencias. Las pruebas existentes cubren cambios de nivel y actualización de la proyección.',
'', '## Evidencias','',
'- [Plano ABC1](plano_ABC1.png)', '- [Demanda diaria](demanda_diaria.png)', '- [Demanda semanal](demanda_semanal.png)', '- [Demanda mensual](demanda_mensual.png)', '- [Pronóstico de papaya en la aplicación](pronostico_papaya_aplicacion.png)', '- [Validación reservada de papaya](validacion_SYN-001.png)',
'- `validacion_SYN-001.png` a `validacion_SYN-030.png`: entrenamiento, demanda real reservada y pronóstico para cada producto.',
'- `evaluacion_autogluon.json`, `modelo_existente_papaya.json`, `recomendador_operativo_papaya.json`, `auditoria_integracion.json`, `playwright_results.json` y logs finales.',
'','## Alcance y pendientes','',
'No quedan errores en las verificaciones finales indicadas. El ensemble original y el recomendador operativo se comprobaron con papaya; no se afirma haber evaluado sus 30 series. Los 30 productos sí tienen entrenamiento, evaluación y recomendaciones mediante los modelos y la política de prueba documentados.',
'Los pedidos del Excel son demanda de clientes, guardada en `pedidos_sinteticos`; no son solicitudes operativas de reposición a proveedores. Los precios se conservan en el Excel: el catálogo actual no tiene campos propios de precio de compra/venta, y no se crearon ofertas de proveedores ficticias. Estas dos integraciones de interfaz no forman parte de lo validado.',
'El exportador artifact-tool agotó su memoria con el conjunto completo; el archivo final usa openpyxl, se reabrió y pasó comparación exacta contra la fuente. Se revisaron vistas de las 14 hojas. Microsoft Excel de escritorio no se ejecutó.',
'Los fallos intermedios de identificación duplicada, filtros de Saiki, fecha de corte y selectores del navegador fueron corregidos. Los logs definitivos se identifican arriba; los logs exploratorios no representan el resultado final.',
'','## Archivos de esta tarea','',
'La carpeta ya contenía cambios ajenos al inicio. Esta lista identifica los archivos intervenidos en esta tarea, no atribuye a esta tarea todo el diff previo del repositorio.','']
lines += ['- `'+p+'`' for p in sorted(set(changed))]
lines += ['','Procedimiento completo y distribución de los 30 productos: [documentación](PROCEDIMIENTO.md).']
(OUT/'PROCEDIMIENTO.md').write_text((ROOT/'docs/dataset_pruebas_30.md').read_text(encoding='utf-8'),encoding='utf-8')
(OUT/'INFORME_VALIDACION.md').write_text('\n'.join(lines),encoding='utf-8')
manifest={'archivo':'PsiTwin_Dataset_Pruebas_2025_2026.xlsx','sha256':hashlib.sha256((OUT/'PsiTwin_Dataset_Pruebas_2025_2026.xlsx').read_bytes()).hexdigest(),'pruebas':tests,'playwright':playwright['stats'],'saiki_errores':audit['errores_saiki'],'archivos_tarea':sorted(set(changed))}
(OUT/'entrega_manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
names=['PsiTwin_Dataset_Pruebas_2025_2026.xlsx','INFORME_VALIDACION.md','entrega_manifest.json','dataset.json','evaluacion_autogluon.json','modelo_existente_papaya.json','recomendador_operativo_papaya.json','pronostico_servicio_papaya.json','importacion.json','preview_importacion.json','reposicion.json','saiki_consultas.json','auditoria_integracion.json','playwright_results.json','predicciones_autogluon.csv','pronostico_futuro.csv','entrenamiento.log','backend_verificacion_final.log','frontend_final_tests.log','frontend_typecheck.log','frontend_tests.log','playwright_ejecucion_final.log']
with zipfile.ZipFile(OUT/'PsiTwin_Pruebas_Entrega.zip','w',zipfile.ZIP_DEFLATED) as z:
    for name in names:z.write(OUT/name,name)
    for p in OUT.glob('*.png'):z.write(p,p.name)
    for p in (ROOT/'backend/scripts').glob('*pruebas*.py'):z.write(p,str(p.relative_to(ROOT)))
    z.write(ROOT/'docs/dataset_pruebas_30.md','PROCEDIMIENTO.md')
print('Informe y ZIP creados; verificaciones finales aprobadas.')
