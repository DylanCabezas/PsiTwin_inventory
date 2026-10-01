# app/controllers/forecast_controller.py

from fastapi import (
    APIRouter,
    HTTPException,
    Query
)

import pandas as pd

from app.ml.demand_history import (
    DemandHistory
)

from app.ml.model_loader import (
    ModelLoader
)

from app.ml.feature_builder import (
    FeatureBuilder
)

from app.ml.predictor import (
    DemandPredictor
)

from app.ml.ml_context_builder import (
    MLContextBuilder
)


router = APIRouter(
    prefix="/forecast",
    tags=["Forecast"]
)


# ============================================================
# INSTANCIAS
# ============================================================

model_loader = ModelLoader()

feature_builder = FeatureBuilder(
    loader=model_loader
)


# ============================================================
# JSON SAFE
# ============================================================

def _json_safe_value(
    value
):

    try:

        if pd.isna(value):
            return None

    except (
        TypeError,
        ValueError
    ):

        pass

    if hasattr(
        value,
        "item"
    ):

        try:
            return value.item()

        except Exception:
            pass

    return value


def _features_to_json(
    features: dict
) -> dict:

    return {

        key:
            _json_safe_value(
                value
            )

        for key, value
        in features.items()
    }


# ============================================================
# CONTAR FEATURES
# ============================================================

def _contar_features(
    features: dict
) -> dict:

    features_json = (
        _features_to_json(
            features
        )
    )

    disponibles = sum(

        1

        for value
        in features_json.values()

        if value is not None
    )

    sin_datos = sum(

        1

        for value
        in features_json.values()

        if value is None
    )

    return {

        "disponibles":
            disponibles,

        "sin_datos":
            sin_datos
    }


# ============================================================
# HISTORY DATAFRAME
# ============================================================

def _crear_history_dataframe(
    historial: list
) -> pd.DataFrame:

    if not historial:

        raise ValueError(
            "No existe historial de demanda "
            "para el inventario indicado."
        )

    history_df = pd.DataFrame(
        historial
    )

    if history_df.empty:

        raise ValueError(
            "El historial de demanda está vacío."
        )

    required_columns = {
        "fecha",
        "demanda"
    }

    missing_columns = (

        required_columns

        - set(
            history_df.columns
        )
    )

    if missing_columns:

        raise ValueError(
            "DemandHistory no devolvió "
            "las columnas necesarias: "
            + ", ".join(
                sorted(
                    missing_columns
                )
            )
        )

    history_df[
        "fecha"
    ] = pd.to_datetime(
        history_df[
            "fecha"
        ]
    )

    return history_df


# ============================================================
# FECHA BASE
# ============================================================

def _obtener_fecha_base(
    history_df: pd.DataFrame
) -> pd.Timestamp:

    fecha_base = (
        pd.to_datetime(
            history_df[
                "fecha"
            ]
        )
        .max()
    )

    if pd.isna(
        fecha_base
    ):

        raise ValueError(
            "No se pudo determinar "
            "la fecha base."
        )

    return fecha_base


# ============================================================
# DEBUG HISTORY
# ============================================================

@router.get(
    "/debug-history/{id_inventario}",
    summary="Probar historial diario de demanda"
)
async def debug_history(

    id_inventario: str,

    dias: int = Query(
        default=30,
        ge=1,
        le=500
    )

):

    try:

        demand_history = (
            DemandHistory()
        )

        historial = await (
            demand_history
            .obtener_ultimos_dias(

                id_inventario=
                    id_inventario,

                dias=
                    dias
            )
        )

        resumen = await (
            demand_history
            .obtener_resumen(

                id_inventario=
                    id_inventario,

                dias=
                    dias
            )
        )

        return {

            "mensaje":
                "Historial de demanda generado correctamente",

            "resumen":
                resumen,

            "historial":
                historial
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error generando historial "
                f"de demanda: {str(exc)}"
            )
        )


# ============================================================
# DEBUG CONTEXT
# ============================================================

@router.get(
    "/debug-context/{id_inventario}",
    summary="Probar contexto operacional para ML"
)
async def debug_context(

    id_inventario: str

):

    try:

        demand_history = (
            DemandHistory()
        )

        historial = await (
            demand_history
            .obtener_ultimos_dias(

                id_inventario=
                    id_inventario,

                dias=
                    30
            )
        )

        history_df = (
            _crear_history_dataframe(
                historial
            )
        )

        fecha_base = (
            _obtener_fecha_base(
                history_df
            )
        )

        context_builder = (
            MLContextBuilder()
        )

        resultado = await (
            context_builder.build(

                id_inventario=
                    id_inventario,

                fecha_base=
                    fecha_base.to_pydatetime()
            )
        )

        return {

            "mensaje":
                "Contexto ML generado correctamente",

            "id_inventario":
                id_inventario,

            "fecha_base_forecast":
                fecha_base.strftime(
                    "%Y-%m-%d"
                ),

            **resultado
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=404,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error construyendo contexto "
                f"ML: {str(exc)}"
            )
        )


# ============================================================
# DEBUG FEATURES
# ============================================================

@router.get(
    "/debug-features/{id_inventario}",
    summary="Probar construcción de features ML"
)
async def debug_features(

    id_inventario: str,

    dias: int = Query(
        default=30,
        ge=1,
        le=500
    ),

    horizon: int = Query(
        default=1,
        ge=1,
        le=7
    )

):

    try:

        # ========================================================
        # HISTORIAL
        # ========================================================

        demand_history = (
            DemandHistory()
        )

        historial = await (
            demand_history
            .obtener_ultimos_dias(

                id_inventario=
                    id_inventario,

                dias=
                    dias
            )
        )

        history_df = (
            _crear_history_dataframe(
                historial
            )
        )

        fecha_base = (
            _obtener_fecha_base(
                history_df
            )
        )

        fecha_objetivo = (

            fecha_base

            + pd.Timedelta(
                days=horizon
            )
        )


        # ========================================================
        # CONTEXTO ESPECIFICO DEL HORIZON
        # ========================================================

        context_builder = (
            MLContextBuilder()
        )

        context = await (
            context_builder
            .build_feature_context(

                id_inventario=
                    id_inventario,

                fecha_base=
                    fecha_base.to_pydatetime(),

                horizon=
                    horizon
            )
        )


        # ========================================================
        # FEATURES
        # ========================================================

        features = (
            feature_builder
            .build_demand_features(

                history=
                    history_df,

                horizon=
                    horizon,

                context=
                    context
            )
        )

        missing_features = (
            feature_builder
            .missing_features(
                features
            )
        )

        features_modelo = {

            feature:
                features.get(
                    feature
                )

            for feature
            in feature_builder.features
        }

        conteo = (
            _contar_features(
                features_modelo
            )
        )

        return {

            "mensaje":
                "Features generadas correctamente",

            "id_inventario":
                id_inventario,

            "configuracion": {

                "dias_historial":
                    dias,

                "horizon":
                    horizon,

                "fecha_base":
                    fecha_base.strftime(
                        "%Y-%m-%d"
                    ),

                "fecha_objetivo":
                    fecha_objetivo.strftime(
                        "%Y-%m-%d"
                    ),

                "future_effective_lag":
                    7 - horizon
            },

            "contexto_ml": {

                "cantidad":
                    len(
                        context
                    ),

                "features":
                    _features_to_json(
                        context
                    )
            },

            "resumen": {

                "features_modelo":
                    len(
                        feature_builder.features
                    ),

                "features_disponibles":
                    conteo[
                        "disponibles"
                    ],

                "features_sin_datos":
                    conteo[
                        "sin_datos"
                    ],

                "features_faltantes":
                    len(
                        missing_features
                    )
            },

            "missing_features":
                missing_features,

            "features":
                _features_to_json(
                    features_modelo
                )
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error construyendo features "
                f"ML: {str(exc)}"
            )
        )


# ============================================================
# DEBUG PREDICT
# ============================================================

@router.get(
    "/debug-predict/{id_inventario}",
    summary="Probar predicción LightGBM D+N"
)
async def debug_predict(

    id_inventario: str,

    dias: int = Query(
        default=30,
        ge=1,
        le=500
    ),

    horizon: int = Query(
        default=1,
        ge=1,
        le=7
    )

):

    try:

        demand_history = (
            DemandHistory()
        )

        historial = await (
            demand_history
            .obtener_ultimos_dias(

                id_inventario=
                    id_inventario,

                dias=
                    dias
            )
        )

        history_df = (
            _crear_history_dataframe(
                historial
            )
        )

        fecha_base = (
            _obtener_fecha_base(
                history_df
            )
        )

        fecha_objetivo = (

            fecha_base

            + pd.Timedelta(
                days=horizon
            )
        )


        # ========================================================
        # CONTEXTO D+N
        # ========================================================

        context_builder = (
            MLContextBuilder()
        )

        context = await (
            context_builder
            .build_feature_context(

                id_inventario=
                    id_inventario,

                fecha_base=
                    fecha_base.to_pydatetime(),

                horizon=
                    horizon
            )
        )


        # ========================================================
        # FEATURES
        # ========================================================

        features = (
            feature_builder
            .build_demand_features(

                history=
                    history_df,

                horizon=
                    horizon,

                context=
                    context
            )
        )

        missing_features = (
            feature_builder
            .missing_features(
                features
            )
        )

        if missing_features:

            raise ValueError(
                "Faltan features requeridas "
                "por LightGBM: "
                + ", ".join(
                    missing_features
                )
            )

        features_modelo = {

            feature:
                features.get(
                    feature
                )

            for feature
            in feature_builder.features
        }

        conteo = (
            _contar_features(
                features_modelo
            )
        )


        # ========================================================
        # PREDICCION
        # ========================================================

        predictor = (
            DemandPredictor(
                loader=model_loader
            )
        )

        demanda_predicha = (
            predictor.predict_horizon(

                features=
                    features,

                horizon=
                    horizon
            )
        )

        return {

            "mensaje":
                "Predicción generada correctamente",

            "id_inventario":
                id_inventario,

            "modelo":
                "LightGBM Global",

            "horizon":
                horizon,

            "future_effective_lag":
                7 - horizon,

            "fecha_base":
                fecha_base.strftime(
                    "%Y-%m-%d"
                ),

            "fecha_objetivo":
                fecha_objetivo.strftime(
                    "%Y-%m-%d"
                ),

            "dias_historial":
                dias,

            "contexto_ml": {

                "cantidad":
                    len(
                        context
                    ),

                "features":
                    _features_to_json(
                        context
                    )
            },

            "features": {

                "total":
                    len(
                        feature_builder.features
                    ),

                "disponibles":
                    conteo[
                        "disponibles"
                    ],

                "sin_datos":
                    conteo[
                        "sin_datos"
                    ],

                "faltantes":
                    len(
                        missing_features
                    )
            },

            "demanda_predicha":
                round(
                    float(
                        demanda_predicha
                    ),
                    4
                )
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error realizando predicción "
                f"ML: {str(exc)}"
            )
        )


# ============================================================
# PREDICT 7 DAYS
# ============================================================

@router.get(
    "/predict-7-days/{id_inventario}",
    summary="Generar forecast de demanda de 7 días"
)
async def predict_7_days(

    id_inventario: str,

    dias: int = Query(
        default=30,
        ge=7,
        le=500
    )

):

    try:

        # ========================================================
        # HISTORIAL
        # ========================================================

        demand_history = (
            DemandHistory()
        )

        historial = await (
            demand_history
            .obtener_ultimos_dias(

                id_inventario=
                    id_inventario,

                dias=
                    dias
            )
        )

        history_df = (
            _crear_history_dataframe(
                historial
            )
        )

        fecha_base = (
            _obtener_fecha_base(
                history_df
            )
        )


        # ========================================================
        # CONTEXTOS D+1 ... D+7
        #
        # Cada horizonte recibe:
        #
        # 13 features base
        # +
        # future_store_lag_7
        # +
        # future_dept_lag_7
        #
        # TOTAL = 15
        # ========================================================

        context_builder = (
            MLContextBuilder()
        )

        contexts_by_horizon = await (
            context_builder
            .build_feature_contexts_7_days(

                id_inventario=
                    id_inventario,

                fecha_base=
                    fecha_base.to_pydatetime()
            )
        )


        # ========================================================
        # FEATURES D+1 ... D+7
        # ========================================================

        features_by_horizon = {}

        features_por_horizonte = {}

        contexto_por_horizonte = {}

        for horizon in range(
            1,
            8
        ):

            context = (
                contexts_by_horizon[
                    horizon
                ]
            )

            features = (
                feature_builder
                .build_demand_features(

                    history=
                        history_df,

                    horizon=
                        horizon,

                    context=
                        context
                )
            )

            missing_features = (
                feature_builder
                .missing_features(
                    features
                )
            )

            if missing_features:

                raise ValueError(
                    f"D+{horizon}: faltan "
                    "features requeridas por "
                    "LightGBM: "
                    + ", ".join(
                        missing_features
                    )
                )

            features_by_horizon[
                horizon
            ] = features

            features_modelo = {

                feature:
                    features.get(
                        feature
                    )

                for feature
                in feature_builder.features
            }

            conteo = (
                _contar_features(
                    features_modelo
                )
            )

            features_por_horizonte[
                f"D+{horizon}"
            ] = {

                "disponibles":
                    conteo[
                        "disponibles"
                    ],

                "sin_datos":
                    conteo[
                        "sin_datos"
                    ]
            }

            contexto_por_horizonte[
                f"D+{horizon}"
            ] = {

                "effective_lag":
                    7 - horizon,

                "future_store_lag_7":
                    context.get(
                        "future_store_lag_7"
                    ),

                "future_dept_lag_7":
                    context.get(
                        "future_dept_lag_7"
                    )
            }


        # ========================================================
        # PREDICTOR
        # ========================================================

        predictor = (
            DemandPredictor(
                loader=model_loader
            )
        )

        forecast = (
            predictor.predict_7_days(

                features_by_horizon=
                    features_by_horizon,

                start_date=
                    fecha_base.date()
            )
        )


        # ========================================================
        # RESUMEN
        # ========================================================

        demanda_total_7d = float(
            forecast[
                "demanda_7d"
            ]
        )

        demanda_promedio_diaria = (

            demanda_total_7d

            / 7.0
        )

        fecha_desde = (

            fecha_base

            + pd.Timedelta(
                days=1
            )
        )

        fecha_hasta = (

            fecha_base

            + pd.Timedelta(
                days=7
            )
        )


        # ========================================================
        # RESPONSE
        # ========================================================

        return {

            "mensaje":
                "Forecast de 7 días generado correctamente",

            "id_inventario":
                id_inventario,

            "modelo":
                "LightGBM Direct Horizon",

            "modo_modelo":
                "global",

            "dias_historial":
                dias,

            "fecha_base":
                fecha_base.strftime(
                    "%Y-%m-%d"
                ),

            "periodo_forecast": {

                "desde":
                    fecha_desde.strftime(
                        "%Y-%m-%d"
                    ),

                "hasta":
                    fecha_hasta.strftime(
                        "%Y-%m-%d"
                    )
            },

            "contexto_ml": {

                "cantidad_features_por_horizonte":
                    15,

                "future_features":
                    contexto_por_horizonte
            },

            "features_por_horizonte":
                features_por_horizonte,

            "demanda_total_7d":
                round(
                    demanda_total_7d,
                    4
                ),

            "demanda_promedio_diaria":
                round(
                    demanda_promedio_diaria,
                    4
                ),

            "predicciones_diarias":
                forecast[
                    "predicciones_diarias"
                ]
        }

    except ValueError as exc:

        raise HTTPException(
            status_code=400,
            detail=str(exc)
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error generando forecast "
                f"de 7 días: {str(exc)}"
            )
        )


# ============================================================
# DEBUG FEATURE INFO
# ============================================================

@router.get(
    "/debug-feature-info",
    summary="Ver configuración de features ML"
)
async def debug_feature_info():

    try:

        return (
            feature_builder.info()
        )

    except Exception as exc:

        raise HTTPException(
            status_code=500,
            detail=(
                "Error obteniendo información "
                f"del FeatureBuilder: {str(exc)}"
            )
        )