import re

from datetime import (
    datetime,
    timezone
)

from app.database.mongodb import (
    get_database
)


class ProductoRepository:

    COLLECTION_NAME = "productos"


    @staticmethod
    def collection():

        return get_database()[
            ProductoRepository.COLLECTION_NAME
        ]


    @staticmethod
    async def crear(
        producto: dict
    ):

        await (
            ProductoRepository
            .collection()
            .insert_one(
                producto
            )
        )

        return await (
            ProductoRepository.obtener_por_id(
                producto["id_producto"]
            )
        )


    @staticmethod
    async def obtener_todos():

        return await (
            ProductoRepository
            .collection()
            .find(
                {},
                {
                    "_id": 0
                }
            )
            .to_list(
                length=None
            )
        )


    @staticmethod
    async def obtener_por_id(
        id_producto: str
    ):

        return await (
            ProductoRepository
            .collection()
            .find_one(
                {
                    "id_producto":
                        id_producto
                },
                {
                    "_id": 0
                }
            )
        )


    # ============================================================
    # PRODUCTOS POR RACK
    # ============================================================

    @staticmethod
    async def obtener_por_rack(
        id_rack: str
    ):

        return await (
            ProductoRepository
            .collection()
            .find(
                {
                    "id_rack":
                        id_rack
                },
                {
                    "_id": 0
                }
            )
            .to_list(
                length=None
            )
        )


    # ============================================================
    # PRODUCTOS POR ALMACEN
    #
    # ALMACEN
    # ↓
    # ZONAS
    # ↓
    # RACKS
    # ↓
    # PRODUCTOS
    # ============================================================

    @staticmethod
    async def obtener_por_almacen(
        id_almacen: str
    ):

        database = get_database()


        # ========================================================
        # 1. ZONAS DEL ALMACEN
        # ========================================================

        zonas = await (
            database["zonas"]
            .find(
                {
                    "id_almacen":
                        id_almacen
                },
                {
                    "_id": 0
                }
            )
            .to_list(
                length=None
            )
        )


        ids_zonas = []

        for zona in zonas:

            id_zona = (
                zona.get("id")
                or
                zona.get("id_zona")
            )

            if id_zona:

                ids_zonas.append(
                    id_zona
                )


        if not ids_zonas:

            return []


        # ========================================================
        # 2. RACKS DE LAS ZONAS
        # ========================================================

        racks = await (
            database["racks"]
            .find(
                {
                    "id_zona": {
                        "$in":
                            ids_zonas
                    }
                },
                {
                    "_id": 0
                }
            )
            .to_list(
                length=None
            )
        )


        ids_racks = []

        for rack in racks:

            id_rack = (
                rack.get("id")
                or
                rack.get("id_rack")
            )

            if id_rack:

                ids_racks.append(
                    id_rack
                )


        if not ids_racks:

            return []


        # ========================================================
        # 3. PRODUCTOS QUE ESTAN EN ESOS RACKS
        # ========================================================

        productos = await (
            ProductoRepository
            .collection()
            .find(
                {
                    "id_rack": {
                        "$in":
                            ids_racks
                    }
                },
                {
                    "_id": 0
                }
            )
            .to_list(
                length=None
            )
        )


        return productos


    @staticmethod
    async def obtener_por_categoria(
        categoria: str
    ):

        categoria_segura = (
            re.escape(
                categoria.strip()
            )
        )

        return await (
            ProductoRepository
            .collection()
            .find(
                {
                    "categoria": {
                        "$regex":
                            f"^{categoria_segura}$",

                        "$options":
                            "i"
                    }
                },
                {
                    "_id": 0
                }
            )
            .to_list(
                length=None
            )
        )


    @staticmethod
    async def obtener_refrigerados():

        return await (
            ProductoRepository
            .collection()
            .find(
                {
                    "requiere_refrigeracion":
                        True
                },
                {
                    "_id": 0
                }
            )
            .to_list(
                length=None
            )
        )


    @staticmethod
    async def actualizar(
        id_producto: str,
        data: dict
    ):

        data[
            "fecha_actualizacion"
        ] = datetime.now(
            timezone.utc
        )


        result = await (
            ProductoRepository
            .collection()
            .update_one(
                {
                    "id_producto":
                        id_producto
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
            ProductoRepository
            .obtener_por_id(
                id_producto
            )
        )


    @staticmethod
    async def eliminar(
        id_producto: str
    ):

        result = await (
            ProductoRepository
            .collection()
            .delete_one(
                {
                    "id_producto":
                        id_producto
                }
            )
        )

        return (
            result.deleted_count > 0
        )