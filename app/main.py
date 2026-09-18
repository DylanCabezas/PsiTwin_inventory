# app/main.py

from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.config.settings import get_settings

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


# ============================================================
# SETTINGS
# ============================================================

settings = get_settings()


# ============================================================
# LIFESPAN
# ============================================================

@asynccontextmanager
async def lifespan(app: FastAPI):

    # Conectar MongoDB al iniciar FastAPI
    await connect_to_mongo()

    yield

    # Cerrar conexión MongoDB al detener FastAPI
    await close_mongo_connection()


# ============================================================
# FASTAPI
# ============================================================

app = FastAPI(
    title=settings.app_name,

    version="1.0.0",

    description=(
        "API de gestión inteligente de inventario, "
        "almacenes, movimientos, reposición y recepción "
        "de mercadería para PsiTwin"
    ),

    lifespan=lifespan
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
            "1.0.0"
    }


# ============================================================
# HEALTH
#
# Comprueba:
#
# API
# +
# MongoDB
#
# GET /health
# ============================================================

@app.get(
    "/health",
    tags=["Sistema"],
    summary="Health check"
)
async def health():

    try:

        database = get_database()

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
                "1.0.0"
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
                "1.0.0"
        }


# ============================================================
# ROUTERS
# ============================================================
#
# Estructura:
#
# Empresa
#   ↓
# Almacen
#   ↓
# Zona
#   ↓
# Rack
#
# Producto
#   ↓
# Inventario
#   ↓
# Movimiento
#
# Operario ────────────────┘
#
# Proveedor
#   ↓
# OrdenReposicion
#   ↓
# DetalleReposicion
#   ↓
# RecepcionMercaderia
#   ↓
# DetalleRecepcion
#   ↓
# Movimiento automático
#   ↓
# Inventario
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
# ORDEN DE REPOSICION
# ============================================================

app.include_router(
    orden_reposicion_router,
    prefix=settings.api_prefix
)


# ============================================================
# DETALLE DE REPOSICION
# ============================================================

app.include_router(
    detalle_reposicion_router,
    prefix=settings.api_prefix
)


# ============================================================
# RECEPCION DE MERCADERIA
# ============================================================

app.include_router(
    recepcion_mercaderia_router,
    prefix=settings.api_prefix
)


# ============================================================
# DETALLE DE RECEPCION
# ============================================================

app.include_router(
    detalle_recepcion_router,
    prefix=settings.api_prefix
)