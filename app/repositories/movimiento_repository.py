from datetime import datetime, timezone
from uuid import uuid4

from app.database.mongodb import get_database


class MovimientoRepository:

    COLLECTION_NAME = "movimientos"

    def collection(self):
        db = get_database()
        return db[self.COLLECTION_NAME]

    async def crear(self, data: dict):

        documento = data.copy()

        documento["id_movimiento"] = str(uuid4())

        documento["fecha_hora"] = datetime.now(
            timezone.utc
        )

        await self.collection().insert_one(
            documento
        )

        return await self.obtener_por_id(
            documento["id_movimiento"]
        )

    async def obtener_todos(self):

        cursor = self.collection().find(
            {},
            {"_id": 0}
        ).sort(
            "fecha_hora",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def obtener_por_id(
        self,
        id_movimiento: str
    ):

        return await self.collection().find_one(
            {
                "id_movimiento": id_movimiento
            },
            {
                "_id": 0
            }
        )

    async def obtener_por_inventario(
        self,
        id_inventario: str
    ):

        cursor = self.collection().find(
            {
                "id_inventario": id_inventario
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_hora",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def obtener_por_producto(
        self,
        id_producto: str
    ):

        cursor = self.collection().find(
            {
                "id_producto": id_producto
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_hora",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def obtener_por_rack(
        self,
        id_rack: str
    ):

        cursor = self.collection().find(
            {
                "id_rack": id_rack
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_hora",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def obtener_por_operario(
        self,
        id_operario: str
    ):

        cursor = self.collection().find(
            {
                "id_operario": id_operario
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_hora",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def obtener_por_tipo(
        self,
        tipo_movimiento: str
    ):

        cursor = self.collection().find(
            {
                "tipo_movimiento": tipo_movimiento
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_hora",
            -1
        )

        return await cursor.to_list(
            length=None
        )

    async def obtener_por_motivo(
        self,
        motivo_movimiento: str
    ):

        cursor = self.collection().find(
            {
                "motivo_movimiento": motivo_movimiento
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_hora",
            -1
        )

        return await cursor.to_list(
            length=None
        )