# Informe de validación — PsiTwin sintético

Dataset generado, importado y reconciliado en MongoDB local, base `psitwin_synthetic30_test`, empresa `psitwin-synthetic-30-v1`. Datos reales de otras empresas sin modificar.

## Conteos comprobados

| Entidad | Registros |
|---|---:|
| README | 1 |
| Empresa | 1 |
| Almacenes | 1 |
| Zonas | 3 |
| Racks | 6 |
| Niveles | 10 |
| Productos | 30 |
| Ubicaciones_Productos | 30 |
| Demanda_Historica | 11880 |
| Movimientos | 13148 |
| Inventario_Actual | 30 |
| Pedidos | 11880 |
| Validaciones | 35 |
| Pronosticos_Referencia | 840 |

30 productos, cuatro helados, 396 días por producto. Período inclusivo 28/09/2025–28/10/2026. Un almacén ABC1, tres zonas, seis racks y diez niveles. Cero sensores, dispositivos, lecturas o alertas IoT. Saldos finales: **1.942,38 kg** y **852 unidades**, separados. Las 417 unidades de helado están exclusivamente en C1.

## Resultados reales de AutoGluon

Entrenamiento nuevo con SeasonalNaive y AutoETS, 11.040 observaciones hasta 30/09/2026. WeightedEnsemble seleccionado; validación reservada de 840 observaciones del 01 al 28/10/2026. La referencia del Excel no se usó como predicción.

| Unidad | MAE | RMSE | WAPE % | sMAPE % |
|---|---:|---:|---:|---:|
| kg | 3.6569 | 5.3229 | 17.5845 | 18.8344 |
| unidad | 3.5698 | 5.0677 | 22.8337 | 28.3839 |

Runtime original de PsiTwin, papaya: {"MAE": 1.8934838305523531, "RMSE": 2.733079900739411, "WAPE": 20.42121071391491, "sMAPE": 23.241927460736996}. Validación de los primeros 28 días del horizonte fijo de 90 días; sin reentrenar ese ensemble. El servicio completo produjo 90 fechas correctas desde 29/10/2026.

Recomendador operativo de papaya: **81 kg**, stock cero y máximo 81 kg. No se generaron compras ni alertas. Política de prueba de tres días para 30 productos: `reposicion.json`. No se confunden ambas políticas.

## Pruebas ejecutadas

- Backend final: **180 aprobadas**.
- Frontend focalizado final: **39 aprobadas**; TypeScript sin errores.
- Suite general de frontend ejecutada antes de los últimos ajustes: **106 aprobadas**.
- Playwright final: **2 aprobadas**, cero fallos, cero omitidas. Aplicación React y servicios reales, autenticación de prueba explícita sobre la base aislada.
- Segunda importación: conteos idénticos, sin duplicados. 13.148 movimientos reconciliados y saldos intermedios no negativos.
- 90 informes históricos comprobados: 30 productos × diario, semanal y mensual.
- Saiki: 13 consultas ejecutadas, cero errores; respuestas guardadas en `saiki_consultas.json`. Pruebas adicionales de aislamiento entre empresas.
- Plano: diez niveles en gris, tres zonas, tipos y nombres comprobados; productos agotados visibles como asignados sin existencias. Las pruebas existentes cubren cambios de nivel y actualización de la proyección.

## Evidencias

- [Plano ABC1](plano_ABC1.png)
- [Demanda diaria](demanda_diaria.png)
- [Demanda semanal](demanda_semanal.png)
- [Demanda mensual](demanda_mensual.png)
- [Pronóstico de papaya en la aplicación](pronostico_papaya_aplicacion.png)
- [Validación reservada de papaya](validacion_SYN-001.png)
- `validacion_SYN-001.png` a `validacion_SYN-030.png`: entrenamiento, demanda real reservada y pronóstico para cada producto.
- `evaluacion_autogluon.json`, `modelo_existente_papaya.json`, `recomendador_operativo_papaya.json`, `auditoria_integracion.json`, `playwright_results.json` y logs finales.

## Alcance y pendientes

No quedan errores en las verificaciones finales indicadas. El ensemble original y el recomendador operativo se comprobaron con papaya; no se afirma haber evaluado sus 30 series. Los 30 productos sí tienen entrenamiento, evaluación y recomendaciones mediante los modelos y la política de prueba documentados.
Los pedidos del Excel son demanda de clientes, guardada en `pedidos_sinteticos`; no son solicitudes operativas de reposición a proveedores. Los precios se conservan en el Excel: el catálogo actual no tiene campos propios de precio de compra/venta, y no se crearon ofertas de proveedores ficticias. Estas dos integraciones de interfaz no forman parte de lo validado.
El exportador artifact-tool agotó su memoria con el conjunto completo; el archivo final usa openpyxl, se reabrió y pasó comparación exacta contra la fuente. Se revisaron vistas de las 14 hojas. Microsoft Excel de escritorio no se ejecutó.
Los fallos intermedios de identificación duplicada, filtros de Saiki, fecha de corte y selectores del navegador fueron corregidos. Los logs definitivos se identifican arriba; los logs exploratorios no representan el resultado final.

## Archivos de esta tarea

La carpeta ya contenía cambios ajenos al inicio. Esta lista identifica los archivos intervenidos en esta tarea, no atribuye a esta tarea todo el diff previo del repositorio.

- `backend/app/knowledge/catalogo_alimentos.json`
- `backend/app/repositories/analisis_repository.py`
- `backend/app/repositories/demanda_historica_repository.py`
- `backend/app/services/analisis_service.py`
- `backend/app/services/forecast_service.py`
- `backend/app/services/inventory_risk_service.py`
- `backend/app/services/saiki_catalog_queries.py`
- `backend/app/services/saiki_demand.py`
- `backend/app/services/saiki_inventario_detallado.py`
- `backend/app/services/saiki_service.py`
- `backend/app/services/saiki_warehouse_map.py`
- `backend/app/services/warehouse_map_service.py`
- `backend/scripts/empaquetar_dataset_pruebas.py`
- `backend/scripts/evaluar_dataset_pruebas.py`
- `backend/scripts/generar_dataset_pruebas.py`
- `backend/scripts/importar_dataset_pruebas.py`
- `backend/scripts/verificar_modelo_existente_pruebas.py`
- `backend/scripts/verificar_recomendador_pruebas.py`
- `backend/tests/synthetic30_browser_app.py`
- `backend/tests/test_dataset_sintetico30.py`
- `backend/tests/test_synthetic30_integration.py`
- `docs/dataset_pruebas_30.md`
- `frontend/e2e/synthetic30.spec.ts`
- `frontend/playwright.synthetic30.config.ts`
- `frontend/src/api/analisis.ts`
- `frontend/src/api/inventarioConsultas.ts`
- `frontend/src/features/almacenes/WarehouseMap.tsx`
- `frontend/src/features/analisis/HistoricalDemandPanel.tsx`
- `frontend/src/features/analisis/SyntheticDataset.test.tsx`
- `tools/synthetic_workbook/preview.mjs`

Procedimiento completo y distribución de los 30 productos: [documentación](PROCEDIMIENTO.md).