from datetime import datetime, timezone
from uuid import uuid4
from typing import Optional, Dict, Any, List

from app.database.mongodb import get_database


class OperarioRepository:

    COLLECTION_NAME = "operarios"

    @staticmethod
    def collection():
        return get_database()[
            OperarioRepository.COLLECTION_NAME
        ]


    @staticmethod
    async def crear(
        data: Dict[str, Any]
    ) -> Dict[str, Any]:

        now = datetime.now(
            timezone.utc
        )

        operario = {
            "id_operario": str(uuid4()),
            "id_empresa": data["id_empresa"],
            "id_almacen": data.get("id_almacen"),

            "nombre": data["nombre"],
            "apellido": data["apellido"],
            "cargo": data["cargo"],
            "turno": data["turno"],
            "estado": data["estado"],

            "fecha_creacion": now,
            "fecha_actualizacion": now
        }

        await (
            OperarioRepository
            .collection()
            .insert_one(operario)
        )

        return await (
            OperarioRepository
            .obtener_por_id(
                operario["id_operario"]
            )
        )


    @staticmethod
    async def obtener_todos(
    ) -> List[Dict[str, Any]]:

        cursor = (
            OperarioRepository
            .collection()
            .find(
                {},
                {"_id": 0}
            )
        )

        return await cursor.to_list(
            length=None
        )


    @staticmethod
    async def obtener_por_id(
        id_operario: str
    ) -> Optional[Dict[str, Any]]:

        return await (
            OperarioRepository
            .collection()
            .find_one(
                {
                    "id_operario":
                        id_operario
                },
                {
                    "_id": 0
                }
            )
        )


    @staticmethod
    async def obtener_por_empresa(
        id_empresa: str
    ) -> List[Dict[str, Any]]:

        cursor = (
            OperarioRepository
            .collection()
            .find(
                {
                    "id_empresa":
                        id_empresa
                },
                {
                    "_id": 0
                }
            )
        )

        return await cursor.to_list(
            length=None
        )


    @staticmethod
    async def obtener_por_estado(
        estado: str
    ) -> List[Dict[str, Any]]:

        cursor = (
            OperarioRepository
            .collection()
            .find(
                {
                    "estado": {
                        "$regex":
                            f"^{estado}$",
                        "$options":
                            "i"
                    }
                },
                {
                    "_id": 0
                }
            )
        )

        return await cursor.to_list(
            length=None
        )


    @staticmethod
    async def obtener_por_turno(
        turno: str
    ) -> List[Dict[str, Any]]:

        cursor = (
            OperarioRepository
            .collection()
            .find(
                {
                    "turno": {
                        "$regex":
                            f"^{turno}$",
                        "$options":
                            "i"
                    }
                },
                {
                    "_id": 0
                }
            )
        )

        return await cursor.to_list(
            length=None
        )


    @staticmethod
    async def actualizar(
        id_operario: str,
        data: Dict[str, Any]
    ) -> Optional[Dict[str, Any]]:

        data = dict(
            data
        )

        data[
            "fecha_actualizacion"
        ] = datetime.now(
            timezone.utc
        )

        result = await (
            OperarioRepository
            .collection()
            .update_one(
                {
                    "id_operario":
                        id_operario
                },
                {
                    "$set":
                        data
                }
            )
        )

        if result.matched_count == 0:
            return None

        return await (
            OperarioRepository
            .obtener_por_id(
                id_operario
            )
        )


    @staticmethod
    async def eliminar(
        id_operario: str
    ) -> bool:

        result = await (
            OperarioRepository
            .collection()
            .delete_one(
                {
                    "id_operario":
                        id_operario
                }
            )
        )

        return (
            result.deleted_count > 0
        )