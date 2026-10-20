from fastapi import (
    HTTPException,
    status
)

from app.dto.inventario_dto import (
    InventarioCreate,
    InventarioUpdate
)

from app.repositories.inventario_repository import (
    InventarioRepository
)

from app.repositories.producto_repository import (
    ProductoRepository
)

from app.repositories.rack_repository import (
    RackRepository
)

from app.repositories.operario_repository import (
    OperarioRepository
)

from app.services.rack_service import (
    RackService
)


class InventarioService:

    def __init__(self):

        self.repository = (
            InventarioRepository()
        )


    # ============================================================
    # CREAR INVENTARIO
    # ============================================================

    async def crear_inventario(
        self,
        data: InventarioCreate,
        id_operario: str | None = None
    ):

        # --------------------------------------------------------
        # VALIDAR PRODUCTO
        # --------------------------------------------------------

        producto = await (
            ProductoRepository.obtener_por_id(
                data.id_producto
            )
        )

        if not producto:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Producto no encontrado"
            )


        # --------------------------------------------------------
        # VALIDAR RACK
        # --------------------------------------------------------

        rack = await (
            RackRepository.obtener_por_id(
                data.id_rack
            )
        )

        if not rack:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Rack no encontrado"
            )


        # --------------------------------------------------------
        # VALIDAR STOCK MIN / MAX
        # --------------------------------------------------------

        if (
            data.stock_minimo
            >
            data.stock_maximo
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "El stock mínimo no puede ser "
                    "mayor que el stock máximo"
                )
            )


        # --------------------------------------------------------
        # EVITAR DUPLICADOS
        # producto + rack
        # --------------------------------------------------------

        inventarios_producto = await (
            self.repository.obtener_por_producto(
                data.id_producto
            )
        )

        for inventario in inventarios_producto:

            if (
                inventario.get(
                    "id_rack"
                )
                ==
                data.id_rack
            ):

                raise HTTPException(
                    status_code=(
                        status.HTTP_409_CONFLICT
                    ),
                    detail=(
                        "Ya existe inventario para "
                        "este producto en este rack"
                    )
                )


        # --------------------------------------------------------
        # STOCK INICIAL <= STOCK MAXIMO (409)
        # --------------------------------------------------------

        if data.stock_actual > data.stock_maximo:

            raise HTTPException(
                status_code=(
                    status.HTTP_409_CONFLICT
                ),
                detail=(
                    "El stock inicial no puede superar "
                    "el stock máximo"
                )
            )


        # --------------------------------------------------------
        # EL PRODUCTO DEBE CABER EN EL RACK (409)
        #
        # rack DISPONIBLE, kg libres y temperatura.
        # --------------------------------------------------------

        await RackService.validar_asignacion(
            rack,
            producto,
            data.stock_actual
        )


        # --------------------------------------------------------
        # CREAR
        # --------------------------------------------------------

        inventario_data = (
            data.model_dump()
        )

        inventario = await (
            self.repository.crear(
                inventario_data
            )
        )

        await self.repository.registrar_historial(
            inventario["id_inventario"],
            id_operario,
            "CREAR",
            None,
            {
                campo: inventario[campo]
                for campo in (
                    "id_producto",
                    "id_rack",
                    "stock_actual",
                    "stock_minimo",
                    "stock_maximo"
                )
            }
        )

        return inventario


    # ============================================================
    # OBTENER TODOS
    # ============================================================

    async def obtener_inventarios(
        self
    ):

        return await (
            self.repository.obtener_todos()
        )


    # ============================================================
    # OBTENER POR ID
    # ============================================================

    async def obtener_inventario(
        self,
        id_inventario: str
    ):

        inventario = await (
            self.repository.obtener_por_id(
                id_inventario
            )
        )

        if not inventario:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Inventario no encontrado"
            )

        return inventario


    # ============================================================
    # OBTENER POR PRODUCTO
    # ============================================================

    async def obtener_por_producto(
        self,
        id_producto: str
    ):

        producto = await (
            ProductoRepository.obtener_por_id(
                id_producto
            )
        )

        if not producto:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Producto no encontrado"
            )

        return await (
            self.repository.obtener_por_producto(
                id_producto
            )
        )


    # ============================================================
    # OBTENER POR RACK
    # ============================================================

    async def obtener_por_rack(
        self,
        id_rack: str
    ):

        rack = await (
            RackRepository.obtener_por_id(
                id_rack
            )
        )

        if not rack:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Rack no encontrado"
            )

        return await (
            self.repository.obtener_por_rack(
                id_rack
            )
        )


    # ============================================================
    # STOCK BAJO
    # ============================================================

    async def obtener_stock_bajo(
        self
    ):

        inventarios = await (
            self.repository.obtener_todos()
        )

        return [
            inventario
            for inventario in inventarios
            if (
                inventario.get(
                    "stock_actual",
                    0
                )
                <=
                inventario.get(
                    "stock_minimo",
                    0
                )
            )
        ]


    # ============================================================
    # SIN STOCK
    # ============================================================

    async def obtener_sin_stock(
        self
    ):

        inventarios = await (
            self.repository.obtener_todos()
        )

        return [
            inventario
            for inventario in inventarios
            if (
                inventario.get(
                    "stock_actual",
                    0
                )
                ==
                0
            )
        ]


    # ============================================================
    # SOBRE STOCK
    # ============================================================

    async def obtener_sobre_stock(
        self
    ):

        inventarios = await (
            self.repository.obtener_todos()
        )

        return [
            inventario
            for inventario in inventarios
            if (
                inventario.get(
                    "stock_actual",
                    0
                )
                >
                inventario.get(
                    "stock_maximo",
                    0
                )
            )
        ]


    # ============================================================
    # ACTUALIZAR LIMITES (OPERARIO)
    #
    # Solo stock_minimo / stock_maximo. El stock cambia
    # únicamente por movimientos y recepciones.
    # ============================================================

    async def actualizar_inventario(
        self,
        id_inventario: str,
        data: InventarioUpdate,
        id_operario: str | None = None
    ):

        inventario_actual = await (
            self.repository.obtener_por_id(
                id_inventario
            )
        )

        if not inventario_actual:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Inventario no encontrado"
            )


        update_data = {
            campo: valor
            for campo, valor in data.model_dump(
                exclude_unset=True
            ).items()
            if valor is not None
        }


        if not update_data:

            return inventario_actual


        antes = {
            campo: inventario_actual.get(campo, 0)
            for campo in (
                "stock_minimo",
                "stock_maximo"
            )
        }

        despues = {
            **antes,
            **update_data
        }


        if (
            despues["stock_minimo"]
            >
            despues["stock_maximo"]
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "El stock mínimo no puede ser "
                    "mayor que el stock máximo"
                )
            )


        inventario_actualizado = await (
            self.repository.actualizar(
                id_inventario,
                update_data
            )
        )

        if despues != antes:

            await self.repository.registrar_historial(
                id_inventario,
                id_operario,
                "EDITAR_LIMITES",
                antes,
                despues
            )

        return inventario_actualizado


    # ============================================================
    # HISTORIAL DE CAMBIOS
    #
    # [{fecha, id_operario, operario_nombre,
    #   accion, antes, despues}]
    # ============================================================

    async def obtener_historial(
        self,
        id_inventario: str
    ):

        historial = await (
            self.repository.obtener_historial(
                id_inventario
            )
        )

        nombres = await (
            OperarioRepository.nombres_por_ids(
                [
                    item.get("id_operario")
                    for item in historial
                ]
            )
        )

        for item in historial:

            item["operario_nombre"] = nombres.get(
                item.get("id_operario")
            )

        return historial


    # ============================================================
    # ELIMINAR INVENTARIO
    # ============================================================

    async def eliminar_inventario(
        self,
        id_inventario: str
    ):

        inventario = await (
            self.repository.obtener_por_id(
                id_inventario
            )
        )

        if not inventario:

            raise HTTPException(
                status_code=(
                    status.HTTP_404_NOT_FOUND
                ),
                detail="Inventario no encontrado"
            )


        if (
            inventario.get(
                "stock_actual",
                0
            )
            >
            0
        ):

            raise HTTPException(
                status_code=(
                    status.HTTP_400_BAD_REQUEST
                ),
                detail=(
                    "No se puede eliminar un inventario "
                    "que todavía tiene stock"
                )
            )


        eliminado = await (
            self.repository.eliminar(
                id_inventario
            )
        )

        if not eliminado:

            raise HTTPException(
                status_code=(
                    status.HTTP_500_INTERNAL_SERVER_ERROR
                ),
                detail=(
                    "No se pudo eliminar el inventario"
                )
            )


        return {
            "mensaje":
                "Inventario eliminado correctamente"
        }