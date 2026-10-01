from fastapi import HTTPException, status

from app.dto.movimiento_dto import (
    MovimientoCreate,
    TipoMovimiento,
    MotivoMovimiento
)

from app.repositories.movimiento_repository import (
    MovimientoRepository
)

from app.repositories.inventario_repository import (
    InventarioRepository
)

from app.repositories.operario_repository import (
    OperarioRepository
)


class MovimientoService:

    def __init__(self):

        self.repository = MovimientoRepository()

        self.inventario_repository = (
            InventarioRepository()
        )

        self.operario_repository = (
            OperarioRepository()
        )

    # ========================================================
    # VALIDAR COMBINACION TIPO + MOTIVO
    # ========================================================

    def validar_tipo_motivo(
        self,
        tipo: TipoMovimiento,
        motivo: MotivoMovimiento
    ):

        motivos_entrada = {
            MotivoMovimiento.RECEPCION,
            MotivoMovimiento.REPOSICION,
            MotivoMovimiento.DEVOLUCION,
            MotivoMovimiento.CONTEO_FISICO,
            MotivoMovimiento.OTRO
        }

        motivos_salida = {
            MotivoMovimiento.VENTA,
            MotivoMovimiento.MERMA,
            MotivoMovimiento.VENCIMIENTO,
            MotivoMovimiento.CONTEO_FISICO,
            MotivoMovimiento.OTRO
        }

        motivos_ajuste = {
            MotivoMovimiento.CONTEO_FISICO,
            MotivoMovimiento.OTRO
        }

        if (
            tipo == TipoMovimiento.ENTRADA
            and motivo not in motivos_entrada
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El motivo {motivo.value} "
                    "no es válido para una ENTRADA"
                )
            )

        if (
            tipo == TipoMovimiento.SALIDA
            and motivo not in motivos_salida
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El motivo {motivo.value} "
                    "no es válido para una SALIDA"
                )
            )

        if (
            tipo == TipoMovimiento.AJUSTE
            and motivo not in motivos_ajuste
        ):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"El motivo {motivo.value} "
                    "no es válido para un AJUSTE"
                )
            )

    # ========================================================
    # CREAR MOVIMIENTO
    # ========================================================

    async def crear_movimiento(
        self,
        data: MovimientoCreate
    ):

        if data.id_detalle_recepcion:
            existente = await (
                self.repository
                .obtener_por_detalle_recepcion(
                    data.id_detalle_recepcion
                )
            )
            if existente:
                return existente

        # ----------------------------------------------------
        # 1. Validar inventario
        # ----------------------------------------------------

        inventario = (
            await self.inventario_repository.obtener_por_id(
                data.id_inventario
            )
        )

        if not inventario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inventario no encontrado"
            )

        # ----------------------------------------------------
        # 2. Validar operario
        # ----------------------------------------------------

        operario = (
            await self.operario_repository.obtener_por_id(
                data.id_operario
            )
        )

        if not operario:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Operario no encontrado"
            )

        # ----------------------------------------------------
        # 3. Validar operario activo
        # ----------------------------------------------------

        estado_operario = str(
            operario.get(
                "estado",
                ""
            )
        ).upper()

        if estado_operario != "ACTIVO":
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    "El operario debe estar ACTIVO "
                    "para registrar movimientos"
                )
            )

        # ----------------------------------------------------
        # 4. Validar tipo + motivo
        # ----------------------------------------------------

        self.validar_tipo_motivo(
            data.tipo_movimiento,
            data.motivo_movimiento
        )

        # ----------------------------------------------------
        # 5. Obtener stock actual
        # ----------------------------------------------------

        stock_anterior = inventario[
            "stock_actual"
        ]

        stock_nuevo = stock_anterior

        # ----------------------------------------------------
        # 6. ENTRADA
        # ----------------------------------------------------

        if (
            data.tipo_movimiento
            == TipoMovimiento.ENTRADA
        ):

            stock_nuevo = (
                stock_anterior
                + data.cantidad
            )

        # ----------------------------------------------------
        # 7. SALIDA
        # ----------------------------------------------------

        elif (
            data.tipo_movimiento
            == TipoMovimiento.SALIDA
        ):

            if data.cantidad > stock_anterior:

                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail=(
                        "Stock insuficiente. "
                        f"Stock disponible: "
                        f"{stock_anterior}. "
                        f"Cantidad solicitada: "
                        f"{data.cantidad}"
                    )
                )

            stock_nuevo = (
                stock_anterior
                - data.cantidad
            )

        # ----------------------------------------------------
        # 8. AJUSTE
        # ----------------------------------------------------
        #
        # Para AJUSTE, cantidad representa el NUEVO STOCK
        # físico contado.
        #
        # Ejemplo:
        # stock sistema = 100
        # cantidad = 96
        # nuevo stock = 96
        #
        # ----------------------------------------------------

        elif (
            data.tipo_movimiento
            == TipoMovimiento.AJUSTE
        ):

            stock_nuevo = data.cantidad

        # ----------------------------------------------------
        # 9. Validar stock
        # ----------------------------------------------------

        if stock_nuevo < 0:

            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "El movimiento produciría "
                    "stock negativo"
                )
            )

        # ----------------------------------------------------
        # 10. Actualizar inventario
        # ----------------------------------------------------

        actualizado = await (
            self.inventario_repository
            .actualizar_stock_condicional(
                data.id_inventario,
                stock_anterior,
                stock_nuevo
            )
        )

        if not actualizado:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=(
                    "El inventario cambió durante el movimiento; "
                    "intente nuevamente"
                )
            )

        # ----------------------------------------------------
        # 11. Crear historial
        # ----------------------------------------------------

        movimiento_dict = {
            "id_inventario":
                data.id_inventario,

            "id_producto":
                inventario["id_producto"],

            "id_rack":
                inventario["id_rack"],

            "id_operario":
                data.id_operario,

            "id_detalle_recepcion":
                data.id_detalle_recepcion,

            "tipo_movimiento":
                data.tipo_movimiento.value,

            "motivo_movimiento":
                data.motivo_movimiento.value,

            "cantidad":
                data.cantidad,

            "stock_anterior":
                stock_anterior,

            "stock_nuevo":
                stock_nuevo,

            "observacion":
                data.observacion
        }

        try:
            movimiento = (
                await self.repository.crear(
                    movimiento_dict
                )
            )
        except Exception:
            await (
                self.inventario_repository
                .actualizar_stock_condicional(
                    data.id_inventario,
                    stock_nuevo,
                    stock_anterior
                )
            )
            raise

        return movimiento

    # ========================================================
    # OBTENER TODOS
    # ========================================================

    async def obtener_movimientos(self):

        return await self.repository.obtener_todos()

    # ========================================================
    # OBTENER POR ID
    # ========================================================

    async def obtener_movimiento(
        self,
        id_movimiento: str
    ):

        movimiento = (
            await self.repository.obtener_por_id(
                id_movimiento
            )
        )

        if not movimiento:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Movimiento no encontrado"
            )

        return movimiento

    # ========================================================
    # POR INVENTARIO
    # ========================================================

    async def obtener_por_inventario(
        self,
        id_inventario: str
    ):

        return (
            await self.repository.obtener_por_inventario(
                id_inventario
            )
        )

    # ========================================================
    # POR PRODUCTO
    # ========================================================

    async def obtener_por_producto(
        self,
        id_producto: str
    ):

        return (
            await self.repository.obtener_por_producto(
                id_producto
            )
        )

    # ========================================================
    # POR RACK
    # ========================================================

    async def obtener_por_rack(
        self,
        id_rack: str
    ):

        return (
            await self.repository.obtener_por_rack(
                id_rack
            )
        )

    # ========================================================
    # POR OPERARIO
    # ========================================================

    async def obtener_por_operario(
        self,
        id_operario: str
    ):

        return (
            await self.repository.obtener_por_operario(
                id_operario
            )
        )

    # ========================================================
    # POR TIPO
    # ========================================================

    async def obtener_por_tipo(
        self,
        tipo_movimiento: TipoMovimiento
    ):

        return (
            await self.repository.obtener_por_tipo(
                tipo_movimiento.value
            )
        )

    # ========================================================
    # POR MOTIVO
    # ========================================================

    async def obtener_por_motivo(
        self,
        motivo_movimiento: MotivoMovimiento
    ):

        return (
            await self.repository.obtener_por_motivo(
                motivo_movimiento.value
            )
        )