from typing import List, Optional

from app.database.mongodb import get_database


class RecomendacionRepository:

    def __init__(self):
        self.db = get_database()

        self.collection = self.db[
            "recomendaciones"
        ]

    async def crear(
        self,
        recomendacion: dict
    ) -> dict:

        documento = recomendacion.copy()

        await self.collection.insert_one(
            documento
        )

        documento.pop(
            "_id",
            None
        )

        return documento

    async def obtener_por_id(
        self,
        id_recomendacion: str
    ) -> Optional[dict]:

        return await self.collection.find_one(
            {
                "id_recomendacion":
                    id_recomendacion
            },
            {
                "_id": 0
            }
        )

    async def listar(
        self
    ) -> List[dict]:

        cursor = self.collection.find(
            {},
            {
                "_id": 0
            }
        ).sort(
            "fecha_creacion",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def listar_por_empresa(
        self,
        id_empresa: str
    ) -> List[dict]:

        cursor = self.collection.find(
            {
                "id_empresa": id_empresa
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_creacion",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def listar_por_almacen(
        self,
        id_almacen: str
    ) -> List[dict]:

        cursor = self.collection.find(
            {
                "id_almacen":
                    id_almacen
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_creacion",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def listar_por_producto(
        self,
        id_producto: str
    ) -> List[dict]:

        cursor = self.collection.find(
            {
                "id_producto":
                    id_producto
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_creacion",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def listar_por_inventario(
        self,
        id_inventario: str
    ) -> List[dict]:

        cursor = self.collection.find(
            {
                "id_inventario":
                    id_inventario
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_creacion",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def listar_por_alerta(
        self,
        id_alerta: str
    ) -> List[dict]:

        cursor = self.collection.find(
            {
                "id_alerta":
                    id_alerta
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_creacion",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def listar_por_estado(
        self,
        estado: str
    ) -> List[dict]:

        cursor = self.collection.find(
            {
                "estado":
                    estado
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_creacion",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def buscar_pendiente(
        self,
        id_inventario: str,
        tipo_recomendacion: str
    ) -> Optional[dict]:

        return await self.collection.find_one(
            {
                "id_inventario":
                    id_inventario,

                "tipo_recomendacion":
                    tipo_recomendacion,

                "estado": {
                    "$in": [
                        "PENDIENTE",
                        "ACEPTADA"
                    ]
                }
            },
            {
                "_id": 0
            }
        )

    async def actualizar(
        self,
        id_recomendacion: str,
        datos: dict
    ) -> Optional[dict]:

        resultado = (
            await self.collection.update_one(
                {
                    "id_recomendacion":
                        id_recomendacion
                },
                {
                    "$set": datos
                }
            )
        )

        if resultado.matched_count == 0:
            return None

        return await self.obtener_por_id(
            id_recomendacion
        )

    async def eliminar(
        self,
        id_recomendacion: str
    ) -> bool:

        resultado = (
            await self.collection.delete_one(
                {
                    "id_recomendacion":
                        id_recomendacion
                }
            )
        )

        return resultado.deleted_count > 0