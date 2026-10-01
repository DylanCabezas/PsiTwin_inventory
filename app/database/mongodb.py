# app/database/mongodb.py

from importlib import import_module
from typing import Any


try:
    _motor = import_module("motor.motor_asyncio")
    AsyncIOMotorClient = _motor.AsyncIOMotorClient
    AsyncIOMotorDatabase = _motor.AsyncIOMotorDatabase
except ImportError as exc:
    AsyncIOMotorClient = None
    AsyncIOMotorDatabase = Any
    _motor_import_error = exc

from app.config.settings import (
    settings
)


client: Any = None

database: Any = None


async def connect_to_mongo():

    global client
    global database

    if AsyncIOMotorClient is None:
        raise RuntimeError(
            "El paquete 'motor' no está instalado. "
            "Instálalo con: pip install motor"
        ) from _motor_import_error

    try:

        client = AsyncIOMotorClient(
            settings.mongodb_url
        )

        database = client[
            settings.mongodb_database
        ]

        # Verificar conexión real
        await client.admin.command(
            "ping"
        )

        try:
            await database["movimientos"].create_index(
                [("id_detalle_recepcion", 1)],
                unique=True,
                partialFilterExpression={
                    "id_detalle_recepcion": {
                        "$type": "string"
                    }
                },
                name="uq_movimiento_detalle_recepcion"
            )
        except Exception as exc:
            print(
                "Advertencia creando índice de idempotencia:"
            )
            print(exc)

        print(
            "MongoDB conectado correctamente"
        )

        print(
            f"Base de datos: "
            f"{settings.mongodb_database}"
        )

    except Exception as e:

        print(
            "Error conectando a MongoDB:"
        )

        print(e)

        raise


async def close_mongo_connection():

    global client
    global database

    if client is not None:

        client.close()

        client = None

        database = None

        print(
            "Conexión MongoDB cerrada"
        )


def get_database() -> Any:

    if database is None:

        raise RuntimeError(
            "MongoDB no está conectado."
        )

    return database