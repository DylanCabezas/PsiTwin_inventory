from datetime import (
    datetime,
    timezone
)

from uuid import uuid4

from typing import (
    Optional,
    Dict,
    Any,
    List
)

from app.database.mongodb import (
    get_database
)


class InventarioRepository:

    COLLECTION_NAME = "inventarios"


    # ============================================================
    # COLLECTION
    # ============================================================

    def collection(self):

        database = get_database()

        return database[
            self.COLLECTION_NAME
        ]


    # ============================================================
    # CREAR
    # ============================================================

    async def crear(
        self,
        data: Dict[str, Any]
    ) -> Dict[str, Any]:

        now = datetime.now(
            timezone.utc
        )

        inventario = {

            "id_inventario":
                str(
                    uuid4()
                ),

            "id_producto":
                data["id_producto"],

            "id_rack":
                data["id_rack"],

            "stock_actual":
                data["stock_actual"],

            "stock_minimo":
                data["stock_minimo"],

            "stock_maximo":
                data["stock_maximo"],

            "fecha_creacion":
                now,

            "fecha_actualizacion":
                now
        }

        await self.collection().insert_one(
            inventario
        )

        return await self.obtener_por_id(
            inventario[
                "id_inventario"
            ]
        )


    # ============================================================
    # OBTENER TODOS
    # ============================================================

    async def obtener_todos(
        self
    ) -> List[Dict[str, Any]]:

        cursor = self.collection().find(
            {},
            {
                "_id": 0
            }
        )

        return await cursor.to_list(
            length=None
        )


    # ============================================================
    # OBTENER POR ID
    # ============================================================

    async def obtener_por_id(
        self,
        id_inventario: str
    ) -> Optional[Dict[str, Any]]:

        return await self.collection().find_one(
            {
                "id_inventario":
                    id_inventario
            },
            {
                "_id": 0
            }
        )


    # ============================================================
    # OBTENER POR PRODUCTO
    # ============================================================

    async def obtener_por_producto(
        self,
        id_producto: str
    ) -> List[Dict[str, Any]]:

        cursor = self.collection().find(
            {
                "id_producto":
                    id_producto
            },
            {
                "_id": 0
            }
        )

        return await cursor.to_list(
            length=None
        )


    # ============================================================
    # OBTENER POR RACK
    # ============================================================

    async def obtener_por_rack(
        self,
        id_rack: str
    ) -> List[Dict[str, Any]]:

        cursor = self.collection().find(
            {
                "id_rack":
                    id_rack
            },
            {
                "_id": 0
            }
        )

        return await cursor.to_list(
            length=None
        )


    # ============================================================
    # OBTENER POR VARIOS RACKS
    # ============================================================

    async def obtener_por_racks(
        self,
        ids_rack: List[str]
    ) -> List[Dict[str, Any]]:

        cursor = self.collection().find(
            {
                "id_rack": {
                    "$in": list(ids_rack)
                }
            },
            {
                "_id": 0
            }
        )

        return await cursor.to_list(
            length=None
        )


    # ============================================================
    # ACTUALIZAR
    # ============================================================

    async def actualizar(
        self,
        id_inventario: str,
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

        result = await self.collection().update_one(
            {
                "id_inventario":
                    id_inventario
            },
            {
                "$set":
                    data
            }
        )

        if result.matched_count == 0:

            return None

        return await self.obtener_por_id(
            id_inventario
        )


    # ============================================================
    # ACTUALIZAR STOCK
    #
    # Este método nos servirá luego para Movimiento.
    # ============================================================

    async def actualizar_stock(
        self,
        id_inventario: str,
        nuevo_stock: int
    ) -> Optional[Dict[str, Any]]:

        await self.collection().update_one(
            {
                "id_inventario":
                    id_inventario
            },
            {
                "$set": {
                    "stock_actual":
                        nuevo_stock,

                    "fecha_actualizacion":
                        datetime.now(
                            timezone.utc
                        )
                }
            }
        )

        return await self.obtener_por_id(
            id_inventario
        )

    async def actualizar_stock_condicional(
        self,
        id_inventario: str,
        stock_anterior: int,
        nuevo_stock: int
    ) -> bool:
        resultado = await self.collection().update_one(
            {
                "id_inventario": id_inventario,
                "stock_actual": stock_anterior
            },
            {
                "$set": {
                    "stock_actual": nuevo_stock,
                    "fecha_actualizacion": datetime.now(
                        timezone.utc
                    )
                }
            }
        )
        return resultado.matched_count == 1


    # ============================================================
    # ELIMINAR
    # ============================================================

    async def eliminar(
        self,
        id_inventario: str
    ) -> bool:

        result = await self.collection().delete_one(
            {
                "id_inventario":
                    id_inventario
            }
        )

        return (
            result.deleted_count > 0
        )


    # ============================================================
    # HISTORIAL DE CAMBIOS (colección inventario_historial)
    # ============================================================

    async def registrar_historial(
        self,
        id_inventario: str,
        id_operario: Optional[str],
        accion: str,
        antes: Optional[Dict[str, Any]],
        despues: Optional[Dict[str, Any]]
    ) -> None:

        await (
            get_database()["inventario_historial"]
            .insert_one(
                {
                    "id_inventario": id_inventario,
                    "id_operario": id_operario,
                    "accion": accion,
                    "antes": antes,
                    "despues": despues,
                    "fecha": datetime.now(
                        timezone.utc
                    )
                }
            )
        )


    async def obtener_historial(
        self,
        id_inventario: str
    ) -> List[Dict[str, Any]]:

        cursor = (
            get_database()["inventario_historial"]
            .find(
                {
                    "id_inventario": id_inventario
                },
                {
                    "_id": 0
                }
            )
            .sort(
                "fecha",
                -1
            )
        )

        return await cursor.to_list(
            length=None
        )
