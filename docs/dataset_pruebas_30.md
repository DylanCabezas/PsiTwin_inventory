# Dataset sintético PsiTwin 2025–2026

Todos los precios, pedidos, ubicaciones, pesos y cantidades son simulados. Semilla: **20260928**. El archivo final está en `outputs/psitwin_pruebas/PsiTwin_Dataset_Pruebas_2025_2026.xlsx`.

## Generación y carga reproducible

Desde la raíz del repositorio, PowerShell:

```powershell
.runtime.local/python/python.exe backend/scripts/generar_dataset_pruebas.py
.runtime.local/python/python.exe backend/scripts/exportar_dataset_excel.py
.runtime.local/python/python.exe backend/scripts/importar_dataset_pruebas.py
.runtime.local/python/python.exe backend/scripts/importar_dataset_pruebas.py --apply
.autogluon.local/Scripts/python.exe backend/scripts/evaluar_dataset_pruebas.py --lead-time-days 3
.runtime.local/python/python.exe backend/scripts/verificar_modelo_existente_pruebas.py
.runtime.local/python/python.exe backend/scripts/verificar_recomendador_pruebas.py
.runtime.local/python/python.exe backend/scripts/verificar_dataset_importado.py
.autogluon.local/Scripts/python.exe backend/scripts/graficar_validacion_pruebas.py
```

La primera ejecución del importador es una **vista previa sin escrituras**. `--apply` solo admite MongoDB local, base `psitwin_synthetic30_test`, empresa `psitwin-synthetic-30-v1`. No utiliza la base configurada de la empresa real ni admite seleccionar otra empresa. El importador lee el Excel real, comprueba el contrato, crea la jerarquía con los servicios existentes, valida los DTO y reproduce las entradas y salidas mediante `MovimientoService`. La empresa y el operario sintéticos son registros de arranque de esta base aislada. No se envían correos ni órdenes a proveedores.

Identidad del origen: `PSITWIN-SINTETICO-2025-2026-v1`. Los identificadores del Excel son estables; los servicios asignan sus identificadores internos y guardan la correspondencia en `id_origen_sintetico`. La repetición busca esas claves y los identificadores de los movimientos: no reinicia el inventario ni duplica las entidades. El bloqueo de importación evita dos cargas simultáneas. Una modificación incompatible del archivo falla en la reconciliación; no se sobrescriben silenciosamente los movimientos existentes.

Los precios se conservan en el Excel como supuestos comerciales. El modelo de catálogo existente no tiene precios de compra/venta propios: las ofertas de proveedores son otra entidad. No se inventan ofertas ni proveedores para simular esa funcionalidad. Los pedidos del Excel representan demanda de clientes, y se conservan en `pedidos_sinteticos`; **no son órdenes operativas de reposición a proveedores** y no alimentan la vista de solicitudes de abastecimiento.

## Inventario y ubicaciones

Período inclusivo: 28/09/2025–28/10/2026, **396 días**, **11.880 observaciones diarias**, **13.148 movimientos**, **11.880 pedidos**. Demanda solicitada, atendida y perdida se guardan por separado. El saldo inicial es cero y la apertura se registra como entrada. Cada ubicación cumple entradas menos salidas igual a saldo final; ningún saldo intermedio es negativo. Hay dos productos agotados, productos bajo mínimo y un exceso deliberado de piña para probar los estados.

| Zona | Rack y tipo | Niveles y productos asignados |
|---|---|---|
| A | A1 Convencional | 1: Papaya, Mango Kent, Granadilla, Melón. 2: Piña Golden, Plátano de seda, Palta Hass, Sandía |
| A | A2 Convencional | 1: Naranja, Mandarina, Limón |
| B | B1 Refrigerado | 1: Manzana roja, Manzana verde. 2: Fresa, Uva roja, Yogur natural |
| B | B2 Refrigerado | 1: Tomate, Zanahoria, Pepino, Choclo. 2: Lechuga, Brócoli, Espinaca |
| C | C1 Congelado | 1: Helado de fresa, Helado de lúcuma. 2: Helado de vainilla, Helado de chocolate |
| C | C2 Convencional | 1: Cebolla roja, Papa blanca, Camote amarillo |

La zona C agrupa conservación seca y congelada; los rangos configurados son características nominales, nunca mediciones. Por compatibilidad con el modelo existente, la zona permite configurar rangos en sus racks; C1 tiene configuración congelada y C2 configuración ambiente. Los tropicales a ambiente representan rotación rápida y ventilación; hojas y yogur están refrigerados. No se simulan temperaturas medidas.

Hay **cero dispositivos, lecturas, tokens MQTT y alertas IoT** en la base de este dataset. Las alertas descriptivas de stock agotado, mínimo y exceso se calculan del inventario, no de sensores. Los diez niveles muestran `sin_datos` en gris. Los productos asignados sin existencias se etiquetan así en el plano.

## Evaluación real de AutoGluon

Entrenamiento nuevo: 28/09/2025–30/09/2026, **11.040 observaciones**. Validación reservada: 01/10/2026–28/10/2026, **840 observaciones**, horizonte 28 días. Se entrenaron SeasonalNaive y AutoETS mediante AutoGluon; ganó WeightedEnsemble. Las columnas de `Pronosticos_Referencia` no se leen para entrenar, evaluar ni recomendar compras.

| Unidad | MAE | RMSE | WAPE % | sMAPE % |
|---|---:|---:|---:|---:|
| kg | 3,6569 | 5,3229 | 17,5845 | 18,8344 |
| unidad | 3,5698 | 5,0677 | 22,8337 | 28,3839 |

No se agrega una métrica física que mezcle kg con unidades. `evaluacion_autogluon.json` incluye las métricas individuales de los 30 productos. Los 30 PNG `validacion_SYN-*.png` muestran entrenamiento, real reservada, pronóstico y horizonte con fechas proporcionales al tiempo real.

También se ejecutó el **runtime preentrenado existente** de PsiTwin, WeightedEnsemble con su configuración original, sin reentrenarlo. Para papaya se evaluaron los primeros 28 días de su horizonte fijo de 90 días, con corte 30/09/2026: MAE **1,8935 kg**, RMSE **2,7331 kg**, WAPE **20,4212 %**, sMAPE **23,2419 %**. `modelo_existente_papaya.json` conserva resultados, cuantiles, fingerprint y métricas. Esta comprobación del ensemble original cubre papaya; la evaluación nueva de SeasonalNaive/AutoETS cubre los 30 productos.

El servicio real `AnalisisService` también produjo 90 días para papaya con el histórico completo hasta 28/10/2026, comenzando el 29/10/2026. `pronostico_servicio_papaya.json` conserva la respuesta. No se reemplazó ni se publicó otro modelo de producción.

## Reposición

Se ajustó un modelo SeasonalNaive nuevo sobre las observaciones disponibles hasta 28/10/2026 para estimar demanda posterior al saldo final. El plazo de prueba es explícito y configurable con `--lead-time-days` (1–28, predeterminado 3). La sugerencia es `max(0, min(maximo-stock, demanda_plazo+minimo-stock))`; unidades enteras se redondean hacia arriba, kg a dos decimales. No se ejecutan compras.

Ejemplos verificados: papaya, saldo 0 kg y sugerencia 47,64 kg; mango, saldo 0 kg y sugerencia 91,63 kg; piña, saldo 393,16 kg frente a máximo 207 kg, sugerencia 0. `reposicion.json` contiene los 30 resultados de la política de prueba de tres días.

También se ejecutó `InventoryRiskService.evaluar` con papaya, el pronóstico real del runtime existente y sin generar alertas ni compras: recomendó **81 kg**, limitado al stock máximo configurado. Se corrigió el corte devuelto por el adaptador cuando el dataset termina antes de ayer, se añadió el histórico diario requerido por el motor y se limitó la reposición al espacio hasta el máximo. Este motor conserva su política anterior de plazo más siete días y sus campos enteros; por eso no da la misma cantidad que la política de prueba de tres días. La capacidad restante se redondea hacia abajo para no superar el máximo.

## Navegador y Saiki

La prueba Playwright utiliza la aplicación React real y los controladores/servicios reales sobre MongoDB local. Solo la identidad de inicio de sesión se sustituye por una identidad explícita de prueba. No se prueba registro, contraseñas ni login de producción. El servidor de prueba no ejecuta tareas de correo ni arranque MQTT.

```powershell
cd frontend
npx.cmd playwright test --config playwright.synthetic30.config.ts
```

Capturas: `plano_ABC1.png`, `demanda_diaria.png`, `demanda_semanal.png`, `demanda_mensual.png` y la vista del pronóstico si la ejecución correspondiente pasa. Los gráficos históricos se recorren para los 30 productos, incluyendo agrupación semanal y mensual. La serie respeta la separación temporal real entre fechas. La tendencia descriptiva compara ambas mitades del período; no se etiqueta como predicción.

`saiki_consultas.json` conserva las 13 consultas y respuestas reales. Se corrigieron el reconocimiento de familias, los filtros de enero, la demanda mensual de helados, la resolución del nombre papaya y la respuesta explícita de ausencia de dispositivos. El stock de helados es **417 unidades en cuatro productos**. En enero de 2026, el mayor registro en kg es Uva roja (**1.057,44 kg**) y en unidades Helado de chocolate (**1.413 unidades**); no se comparan ambas magnitudes. Una consulta mensual sin año solo lo deduce cuando existe un único año del mes en los datos autorizados.

## Evidencias y límites

Los archivos `*_tests.log`, `playwright_results.json` y `auditoria_integracion.json` registran las ejecuciones; el informe final en outputs consolida los resultados definitivos. `auditoria_integracion.json` comprueba la repetición sin cambios de conteos, el plano y las 90 consultas históricas (30 productos × 3 frecuencias).

El Excel se exportó con openpyxl después de que artifact-tool agotara su heap al intentar el conjunto completo. Se reabrió el XLSX, se comprobó la igualdad con la fuente reproducible y se generaron vistas de revisión de las 14 hojas. No se ejecutó Microsoft Excel de escritorio.

La política de prueba se evaluó para 30 productos; el recomendador operativo y el ensemble original se probaron con papaya. No se ejecutaron aprobaciones ni compras. Los pedidos de clientes del dataset permanecen separados de solicitudes de abastecimiento. Los rangos y pesos son supuestos de prueba, no una certificación de conservación o capacidad física.
