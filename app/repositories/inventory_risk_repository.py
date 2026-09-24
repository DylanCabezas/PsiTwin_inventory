from datetime import datetime
from typing import List, Optional

from app.database.mongodb import (
    get_database
)


class InventoryRiskRepository:

    def __init__(self):

        self.db = get_database()

        self.inventarios = self.db[
            "inventarios"
        ]

        self.productos = self.db[
            "productos"
        ]

        self.movimientos = self.db[
            "movimientos"
        ]

        self.racks = self.db[
            "racks"
        ]

        self.zonas = self.db[
            "zonas"
        ]

        self.almacenes = self.db[
            "almacenes"
        ]

    async def obtener_inventario(
        self,
        id_inventario: str
    ) -> Optional[dict]:

        return await self.inventarios.find_one(
            {
                "id_inventario":
                    id_inventario
            },
            {
                "_id": 0
            }
        )

    async def listar_inventarios(
        self
    ) -> List[dict]:

        cursor = self.inventarios.find(
            {},
            {
                "_id": 0
            }
        )

        return await cursor.to_list(
            length=None
        )

    async def obtener_producto(
        self,
        id_producto: str
    ) -> Optional[dict]:

        return await self.productos.find_one(
            {
                "id_producto":
                    id_producto
            },
            {
                "_id": 0
            }
        )

    async def obtener_rack(
        self,
        id_rack: str
    ) -> Optional[dict]:

        return await self.racks.find_one(
            {
                "id_rack":
                    id_rack
            },
            {
                "_id": 0
            }
        )

    async def obtener_zona(
        self,
        id_zona: str
    ) -> Optional[dict]:

        return await self.zonas.find_one(
            {
                "id_zona":
                    id_zona
            },
            {
                "_id": 0
            }
        )

    async def obtener_almacen(
        self,
        id_almacen: str
    ) -> Optional[dict]:

        return await self.almacenes.find_one(
            {
                "id_almacen":
                    id_almacen
            },
            {
                "_id": 0
            }
        )

    async def obtener_salidas_desde(
        self,
        id_inventario: str,
        fecha_desde: datetime
    ) -> List[dict]:

        cursor = self.movimientos.find(
            {
                "id_inventario":
                    id_inventario,

                "tipo_movimiento":
                    "SALIDA",

                "fecha_hora": {
                    "$gte":
                        fecha_desde
                }
            },
            {
                "_id": 0
            }
        ).sort(
            "fecha_hora",
            1
        )

        return await cursor.to_list(
            length=None
        )