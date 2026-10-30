# Analizar CSV desde la web

Abrir **Análisis de demanda → Analizar CSV**, cargar el archivo y seleccionar
las columnas correspondientes. La aplicación muestra cinco filas de ejemplo
antes de analizarlo.

## Datos necesarios

| Dato | Obligatorio | Contenido |
| --- | --- | --- |
| Fecha | Sí | Día de la venta, consumo o demanda observada |
| Cantidad demandada | Sí | Cantidad numérica no negativa; no usar stock ni precio |
| Producto o serie | No | Nombre, código o identificador para separar las series |

Los encabezados pueden tener cualquier nombre: el usuario los asigna en la
vista previa. No se declara un tipo de datos: CSV contiene texto, y el sistema
convierte los valores compatibles. Las columnas adicionales se ignoran.

Se aceptan fechas ISO, fechas con hora, `DD/MM/AAAA`, `DD-MM-AAAA`, `AAAA/MM/DD`,
`AAAAMMDD` y fechas numéricas de Excel, también con hora fraccionaria.
Las fechas con barras se interpretan como día/mes/año, no mes/día/año.

Las cantidades admiten enteros, decimales con punto o coma, espacios de miles,
notación científica y formatos mixtos como `1.200,50` o `1,200.50`. Un separador
único se interpreta como decimal: `1,234` significa `1.234`. Para mil doscientos
treinta y cuatro usar `1234` o `1 234`. Valores vacíos, palabras, negativos,
NaN, infinito y fechas inválidas se rechazan con el número de fila; no se
descartan registros silenciosamente.

```csv
fecha,producto,cantidad
2026-10-01,Arroz,12
2026-10-02,Arroz,15
2026-10-01,Chocolate,8
```

CSV UTF-8, con o sin BOM, delimitado por coma, punto y coma, tabulador o `|`.
Límite: 2 MB y 20 000 registros. Usar comillas si un valor contiene el separador.
Las filas del mismo producto y día se suman. Cada serie debe usar una sola
unidad; no combinar cantidades de distintos productos sin asignar la columna
de producto. Para almacenes separados, preparar una serie o archivo por almacén.

## Resultados

El análisis muestra demanda total, promedio por día observado, mínimo y máximo
diarios, periodo, días ausentes y gráfico. Cada producto se analiza por separado.
Los días ausentes no se rellenan con ceros.

El botón de pronóstico utiliza el runtime AutoGluon existente, sin reentrenarlo:
requiere 91 días consecutivos, con corte anterior a hoy, y el modelo validado.
Puede mostrarse a 1, 7, 30 o 90 días después del último día del archivo. Sin
modelo o sin historial suficiente solo se presenta el análisis observado.

La carga no escribe en MongoDB ni modifica stock, pedidos o el historial de la
empresa. Se procesa en memoria, con el usuario autenticado; no se envía al LLM.
El archivo se manda en JSON a `POST /api/v1/analisis/csv/columnas` para inspección
y a `POST /api/v1/analisis/csv/analizar` para el análisis y pronóstico opcional.
