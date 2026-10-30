# app/main.py

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import (
    get_settings
)

from app.database.mongodb import (
    connect_to_mongo,
    close_mongo_connection,
    get_database
)


# ============================================================
# CONTROLLERS
# ============================================================

from app.controllers.empresa_controller import (
    router as empresa_router
)

from app.controllers.almacen_controller import (
    router as almacen_router
)

from app.controllers.zona_controller import (
    router as zona_router
)

from app.controllers.rack_controller import (
    router as rack_router
)

from app.controllers.producto_controller import (
    router as producto_router
)

from app.controllers.inventario_controller import (
    router as inventario_router
)

from app.controllers.operario_controller import (
    router as operario_router
)

from app.controllers.movimiento_controller import (
    router as movimiento_router
)

from app.controllers.proveedor_controller import (
    router as proveedor_router
)

from app.controllers.orden_reposicion_controller import (
    router as orden_reposicion_router
)

from app.controllers.detalle_reposicion_controller import (
    router as detalle_reposicion_router
)

from app.controllers.recepcion_mercaderia_controller import (
    router as recepcion_mercaderia_router
)

from app.controllers.detalle_recepcion_controller import (
    router as detalle_recepcion_router
)

from app.controllers.alerta_controller import (
    router as alerta_router
)

from app.controllers.recomendacion_controller import (
    router as recomendacion_router
)

from app.controllers.inventory_risk_controller import (
    router as inventory_risk_router
)

from app.controllers.saiki_controller import (
    router as saiki_router
)

# NUEVO:
# Controller temporal para probar el historial
# de demanda que posteriormente utilizará ML.
from app.controllers.forecast_controller import (
    router as forecast_router
)


# ============================================================
# SETTINGS
# ============================================================

settings = get_settings()


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(
    app: FastAPI
):

    # --------------------------------------------------------
    # INICIO DE LA APLICACION
    # --------------------------------------------------------

    await connect_to_mongo()

    yield

    # --------------------------------------------------------
    # CIERRE DE LA APLICACION
    # --------------------------------------------------------

    await close_mongo_connection()


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(

    title=
        settings.app_name,

    version=
        "1.2.0",

    description=(
        "API de gestión inteligente de inventario, "
        "almacenes, movimientos, reposición, "
        "recepción de mercadería, alertas, "
        "recomendaciones, evaluación de riesgo "
        "y predicción de demanda para PsiTwin."
    ),

    lifespan=
        lifespan
)


# ============================================================
# ROOT
#
# GET /
# ============================================================

@app.get(
    "/",
    tags=["Sistema"]
)
async def root():

    return {

        "mensaje":
            "PsiTwin Inventory API funcionando",

        "version":
            "1.2.0",

        "modulos": [

            "Empresa",
            "Almacen",
            "Zona",
            "Rack",
            "Producto",
            "Inventario",
            "Operario",
            "Movimiento",

            "Proveedor",
            "OrdenReposicion",
            "DetalleReposicion",
            "RecepcionMercaderia",
            "DetalleRecepcion",

            "Alertas",
            "Recomendaciones",

            "InventoryRisk",

            "Forecast",

            "Saiki"
        ]
    }


# ============================================================
# HEALTH
#
# GET /health
#
# Comprueba:
#
# FastAPI
# +
# MongoDB
# ============================================================

@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health check"
)
async def health():

    try:

        database = (
            get_database()
        )

        await database.command(
            "ping"
        )

        return {

            "status":
                "healthy",

            "api":
                "ok",

            "database":
                "ok",

            "database_name":
                settings.mongodb_database,

            "version":
                "1.2.0"
        }

    except Exception as exc:

        return {

            "status":
                "unhealthy",

            "api":
                "ok",

            "database":
                "error",

            "detail":
                str(exc),

            "version":
                "1.2.0"
        }


# ============================================================
# ARQUITECTURA GENERAL
# ============================================================
#
# EMPRESA
#   ↓
# ALMACEN
#   ↓
# ZONA
#   ↓
# RACK
#
#
# PRODUCTO
#   ↓
# INVENTARIO
#   ↓
# MOVIMIENTO
#
#
# PROVEEDOR
#   ↓
# ORDEN REPOSICION
#   ↓
# DETALLE REPOSICION
#   ↓
# RECEPCION MERCADERIA
#   ↓
# DETALLE RECEPCION
#   ↓
# MOVIMIENTO AUTOMATICO
#   ↓
# INVENTARIO
#
#
# ============================================================
# CAPA DE INTELIGENCIA
# ============================================================
#
# MOVIMIENTOS
#      ↓
# DEMAND HISTORY
#      ↓
# FEATURE BUILDER
#      ↓
# LIGHTGBM
# D+1 ... D+7
#      ↓
# FORECAST
#      ↓
# INVENTORY RISK
#      ↓
# ALERTA
#      ↓
# RECOMENDACION
#      ↓
# LLM
#
# ============================================================


# ============================================================
# EMPRESA
# ============================================================

app.include_router(
    empresa_router,
    prefix=settings.api_prefix
)


# ============================================================
# ALMACEN
# ============================================================

app.include_router(
    almacen_router,
    prefix=settings.api_prefix
)


# ============================================================
# ZONA
# ============================================================

app.include_router(
    zona_router,
    prefix=settings.api_prefix
)


# ============================================================
# RACK
# ============================================================

app.include_router(
    rack_router,
    prefix=settings.api_prefix
)


# ============================================================
# PRODUCTO
# ============================================================

app.include_router(
    producto_router,
    prefix=settings.api_prefix
)


# ============================================================
# INVENTARIO
# ============================================================

app.include_router(
    inventario_router,
    prefix=settings.api_prefix
)


# ============================================================
# OPERARIO
# ============================================================

app.include_router(
    operario_router,
    prefix=settings.api_prefix
)


# ============================================================
# MOVIMIENTO
# ============================================================

app.include_router(
    movimiento_router,
    prefix=settings.api_prefix
)


# ============================================================
# PROVEEDOR
# ============================================================

app.include_router(
    proveedor_router,
    prefix=settings.api_prefix
)


# ============================================================
# ORDEN REPOSICION
# ============================================================

app.include_router(
    orden_reposicion_router,
    prefix=settings.api_prefix
)


# ============================================================
# DETALLE REPOSICION
# ============================================================

app.include_router(
    detalle_reposicion_router,
    prefix=settings.api_prefix
)


# ============================================================
# RECEPCION MERCADERIA
# ============================================================

app.include_router(
    recepcion_mercaderia_router,
    prefix=settings.api_prefix
)


# ============================================================
# DETALLE RECEPCION
# ============================================================

app.include_router(
    detalle_recepcion_router,
    prefix=settings.api_prefix
)


# ============================================================
# ALERTAS
# ============================================================

app.include_router(
    alerta_router,
    prefix=settings.api_prefix
)


# ============================================================
# RECOMENDACIONES
# ============================================================

app.include_router(
    recomendacion_router,
    prefix=settings.api_prefix
)


# ============================================================
# INVENTORY RISK
# ============================================================

app.include_router(
    inventory_risk_router,
    prefix=settings.api_prefix
)


# ============================================================
# FORECAST
#
# Actualmente:
#
# Movimiento
#     ↓
# DemandHistory
#     ↓
# Serie diaria
#
# Posteriormente:
#
# Serie diaria
#     ↓
# FeatureBuilder
#     ↓
# LightGBM
#     ↓
# D+1 ... D+7
# ============================================================

app.include_router(
    forecast_router,
    prefix=settings.api_prefix
)


# ============================================================
# SAIKI
# ============================================================

app.include_router(
    saiki_router,
    prefix=settings.api_prefix
)