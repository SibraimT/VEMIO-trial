# VEMIO, Prueba Técnica

Análisis de demanda, elasticidad de precio y uplift promocional para un cliente CPG.

## Estructura del repo

```
vemio_case/
├── data/               # dataset crudo + datos procesados
├── src/                # funciones reutilizables
├── notebooks/          # desarrollo de los 3 retos
├── outputs/            # gráficas y tablas de resultados
├── docs/               # documento 
├── requirements.txt
└── README.md
```

## Cómo reproducir

1. Clonar el repo.
2. Crear entorno e instalar dependencias:
   ```bash
   pip install -r requirements.txt
   ```
3. Colocar el archivo csv dentro de `data/`
4. Correr los notebooks en orden: `01_eda_cleaning`, `02_reto_a_forecasting`, `03_reto_b_elasticidad`, `04_reto_c_uplift`.

## Retos

- **Reto A — Demand Forecasting**: proyección semanal de demanda para SKUs seleccionados, 8-12 semanas adelante, con validación temporal sin fuga de información.
- **Reto B — Elasticidad de precio**: estimación de sensibilidad de demanda al precio + simulador de ingreso/margen.
- **Reto C — Uplift promocional**: venta incremental de al menos 2 promociones pasadas.

Ver `docs/findings.md` para metodología, supuestos y recomendaciones de negocio.
