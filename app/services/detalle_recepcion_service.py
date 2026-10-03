# app/services/detalle_recepcion_service.py

from datetime import datetime, timezone

from fastapi import HTTPException

from app.dto.detalle_recepcion_dto import (
    DetalleRecepcionCreate
)

from app.dto.movimiento_dto import (
    MovimientoCreate,
    TipoMovimiento,
    MotivoMovimiento
)

from app.repositories.detalle_recepcion_repository import (
    DetalleRecepcionRepository
)

from app.repositories.recepcion_mercaderia_repository import (
    RecepcionMercaderiaRepository
)

from app.repositories.detalle_reposicion_repository import (
    DetalleReposicionRepository
)

from app.repositories.orden_reposicion_repository import (
    OrdenReposicionRepository
)

from app.repositories.inventario_repository import (
    InventarioRepository
)

from app.repositories.rack_repository import (
    RackRepository
)

from app.repositories.zona_repository import (
    ZonaRepository
)

from app.services.movimiento_service import (
    MovimientoService
)

from app.services.notification_service import (
    NotificationService
)


class DetalleRecepcionService:

    def __init__(self):

        self.repository = (
            DetalleRecepcionRepository()
        )

        self.recepcion_repository = (
            RecepcionMercaderiaRepository()
        )

        self.detalle_reposicion_repository = (
            DetalleReposicionRepository()
        )

        self.orden_repository = (
            OrdenReposicionRepository()
        )

        self.inventario_repository = (
            InventarioRepository()
        )

        self.rack_repository = RackRepository()

        self.zona_repository = ZonaRepository()

        self.movimiento_service = (
            MovimientoService()
        )

        self.notification_service = NotificationService()

    # ========================================================
    # CREAR DETALLE DE RECEPCION
    # ========================================================

    async def crear(
        self,
        id_recepcion: str,
        data: DetalleRecepcionCreate
    ):

        # ====================================================
        # 1. VALIDAR RECEPCION
        # ====================================================

        recepcion = (
            await self.recepcion_repository
            .obtener_por_id(
                id_recepcion
            )
        )

        if not recepcion:

            raise HTTPException(
                status_code=404,
                detail="Recepción no encontrada"
            )

        # ====================================================
        # 2. VALIDAR DETALLE DE REPOSICION
        # ====================================================

        detalle_orden = (
            await self.detalle_reposicion_repository
            .obtener_por_id(
                data.id_detalle_reposicion
            )
        )

        if not detalle_orden:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Detalle de reposición "
                    "no encontrado"
                )
            )

        # ====================================================
        # 3. VALIDAR QUE PERTENEZCA A LA MISMA ORDEN
        # ====================================================

        if (
            detalle_orden[
                "id_orden_reposicion"
            ]
            != recepcion[
                "id_orden_reposicion"
            ]
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "El detalle de reposición "
                    "no pertenece a la orden "
                    "de esta recepción"
                )
            )

        # ====================================================
        # 4. VALIDAR INVENTARIO
        # ====================================================

        inventario = (
            await self.inventario_repository
            .obtener_por_id(
                data.id_inventario
            )
        )

        if not inventario:

            raise HTTPException(
                status_code=404,
                detail="Inventario no encontrado"
            )

        rack = await self.rack_repository.obtener_por_id(
            inventario["id_rack"]
        )

        if not rack:
            raise HTTPException(
                status_code=404,
                detail="Rack del inventario no encontrado"
            )

        zona = await self.zona_repository.obtener_por_id(
            rack.get("id_zona")
        )

        if not zona:
            raise HTTPException(
                status_code=404,
                detail="Zona del rack no encontrada"
            )

        orden = await self.orden_repository.obtener_por_id(
            recepcion["id_orden_reposicion"]
        )

        id_almacen_zona = zona.get("id_almacen")
        if not orden or id_almacen_zona != orden.get(
            "id_almacen"
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "El rack del inventario no pertenece "
                    "al almacén de la orden"
                )
            )

        # ====================================================
        # 5. VALIDAR PRODUCTO
        #
        # El inventario seleccionado debe corresponder
        # exactamente al producto pedido.
        # ====================================================

        if (
            inventario["id_producto"]
            != detalle_orden["id_producto"]
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "El inventario seleccionado "
                    "no corresponde al producto "
                    "de la orden"
                )
            )

        # ====================================================
        # 6. OBTENER RECEPCIONES ANTERIORES
        #
        # Esto permite recepciones parciales.
        # ====================================================

        anteriores = (
            await self.repository
            .obtener_por_detalle_reposicion(
                data.id_detalle_reposicion
            )
        )

        cantidad_aceptada_anterior = sum(
            detalle.get(
                "cantidad_aceptada",
                0
            )
            for detalle in anteriores
        )

        # ====================================================
        # 7. CALCULAR CANTIDAD ACEPTADA
        # ====================================================

        if data.estado_recepcion.value == "EN_EVALUACION":
            cantidad_aceptada = 0
        else:
            cantidad_aceptada = (
                data.cantidad_recibida
                - data.cantidad_rechazada
            )

        # ====================================================
        # 8. EVITAR SOBRERECEPCION
        # ====================================================

        cantidad_total_aceptada = (
            cantidad_aceptada_anterior
            + cantidad_aceptada
        )

        if (
            cantidad_total_aceptada
            > detalle_orden[
                "cantidad_solicitada"
            ]
        ):

            cantidad_pendiente = (
                detalle_orden[
                    "cantidad_solicitada"
                ]
                - cantidad_aceptada_anterior
            )

            raise HTTPException(
                status_code=409,
                detail=(
                    "La cantidad aceptada supera "
                    "la cantidad pendiente de la orden. "
                    f"Pendiente: {cantidad_pendiente}"
                )
            )

        # ====================================================
        # 9. CREAR DETALLE DE RECEPCION
        # ====================================================

        documento = data.model_dump()

        documento[
            "id_recepcion"
        ] = id_recepcion

        documento[
            "cantidad_aceptada"
        ] = cantidad_aceptada

        documento[
            "id_movimiento"
        ] = None

        documento[
            "id_rack"
        ] = inventario["id_rack"]

        documento[
            "ubicado"
        ] = (
            data.estado_recepcion.value
            != "EN_EVALUACION"
        )

        detalle_recepcion = (
            await self.repository.crear(
                documento
            )
        )

        # ====================================================
        # 10. GENERAR MOVIMIENTO AUTOMATICO
        #
        # Solo las unidades aceptadas ingresan al stock.
        #
        # Ejemplo:
        #
        # recibidas = 100
        # rechazadas = 5
        #
        # movimiento = 95
        # ====================================================

        if cantidad_aceptada > 0:

            movimiento_data = MovimientoCreate(

                id_inventario=
                    data.id_inventario,

                id_operario=
                    recepcion[
                        "id_operario"
                    ],

                id_detalle_recepcion=
                    detalle_recepcion[
                        "id_detalle_recepcion"
                    ],

                tipo_movimiento=
                    TipoMovimiento.ENTRADA,

                motivo_movimiento=
                    MotivoMovimiento.RECEPCION,

                cantidad=
                    cantidad_aceptada,

                observacion=(
                    "Entrada automática por "
                    "recepción de mercadería "
                    f"{id_recepcion}"
                )
            )

            movimiento = (
                await self.movimiento_service
                .crear_movimiento(
                    movimiento_data
                )
            )

            # ================================================
            # GUARDAR FK DEL MOVIMIENTO GENERADO
            # ================================================

            detalle_recepcion = (
                await self.repository
                .actualizar_movimiento(
                    detalle_recepcion[
                        "id_detalle_recepcion"
                    ],
                    movimiento[
                        "id_movimiento"
                    ]
                )
            )

        # ====================================================
        # 11. ACTUALIZAR ESTADO DE ORDEN
        # ====================================================

        await self._recalcular_estado_orden(
            recepcion[
                "id_orden_reposicion"
            ]
        )

        return detalle_recepcion

    async def resolver_evaluacion(
        self,
        id_detalle_recepcion: str,
        data
    ):
        detalle = await self.repository.obtener_por_id(
            id_detalle_recepcion
        )

        if not detalle:
            raise HTTPException(
                status_code=404,
                detail="Detalle de recepción no encontrado"
            )

        if detalle.get("id_movimiento"):
            return detalle

        movimiento_existente = await (
            self.movimiento_service.repository
            .obtener_por_detalle_recepcion(
                id_detalle_recepcion
            )
        )

        if movimiento_existente:
            return await self.repository.actualizar_movimiento(
                id_detalle_recepcion,
                movimiento_existente["id_movimiento"]
            )

        if detalle.get("estado_recepcion") != "EN_EVALUACION":
            raise HTTPException(
                status_code=409,
                detail="El detalle ya fue resuelto"
            )

        recepcion = await self.recepcion_repository.obtener_por_id(
            detalle["id_recepcion"]
        )

        if not recepcion:
            raise HTTPException(
                status_code=404,
                detail="Recepción no encontrada"
            )

        id_inventario = (
            data.id_inventario
            or detalle.get("id_inventario")
        )
        inventario = await self.inventario_repository.obtener_por_id(
            id_inventario
        )

        if not inventario:
            raise HTTPException(
                status_code=404,
                detail="Inventario no encontrado"
            )

        rack = await self.rack_repository.obtener_por_id(
            inventario["id_rack"]
        )
        zona = await self.zona_repository.obtener_por_id(
            rack.get("id_zona") if rack else None
        )
        orden = await self.orden_repository.obtener_por_id(
            recepcion["id_orden_reposicion"]
        )

        if not rack or not zona or not orden or zona.get(
            "id_almacen"
        ) != orden.get("id_almacen"):
            raise HTTPException(
                status_code=400,
                detail="El rack no pertenece al almacén de la orden"
            )

        recibida = detalle["cantidad_recibida"]
        rechazada = (
            data.cantidad_rechazada
            if data.cantidad_rechazada is not None
            else detalle.get("cantidad_rechazada", 0)
        )
        aceptada = (
            data.cantidad_aceptada
            if data.cantidad_aceptada is not None
            else recibida - rechazada
        )

        if aceptada < 0 or rechazada < 0 or aceptada + rechazada != recibida:
            raise HTTPException(
                status_code=400,
                detail="Las cantidades aceptada y rechazada no coinciden con la recibida"
            )

        riesgo_antes = await self._obtener_riesgo(
            id_inventario
        )

        if aceptada <= 0:
            actualizado = await self.repository.actualizar(
                id_detalle_recepcion,
                {
                    "id_inventario": id_inventario,
                    "id_rack": inventario["id_rack"],
                    "cantidad_aceptada": 0,
                    "cantidad_rechazada": rechazada,
                    "estado_recepcion": data.estado_recepcion.value,
                    "comentario_resolucion": data.comentario_resolucion,
                    "id_operario_resolucion": data.id_operario,
                    "fecha_resolucion": datetime.now(timezone.utc),
                    "ubicado": False
                }
            )
            await self._recalcular_estado_orden(
                recepcion["id_orden_reposicion"]
            )
            riesgo_despues = await self._obtener_riesgo(
                id_inventario
            )
            return await self._notificar_cierre(
                recepcion,
                actualizado,
                riesgo_antes,
                riesgo_despues
            )

        movimiento = await self.movimiento_service.crear_movimiento(
            MovimientoCreate(
                id_inventario=id_inventario,
                id_operario=data.id_operario,
                id_detalle_recepcion=id_detalle_recepcion,
                tipo_movimiento=TipoMovimiento.ENTRADA,
                motivo_movimiento=MotivoMovimiento.RECEPCION,
                cantidad=aceptada,
                observacion=data.comentario_resolucion
            )
        )

        actualizado = await self.repository.actualizar(
            id_detalle_recepcion,
            {
                "id_inventario": id_inventario,
                "id_rack": inventario["id_rack"],
                "cantidad_aceptada": aceptada,
                "cantidad_rechazada": rechazada,
                "estado_recepcion": data.estado_recepcion.value,
                "comentario_resolucion": data.comentario_resolucion,
                "id_operario_resolucion": data.id_operario,
                "fecha_resolucion": datetime.now(timezone.utc),
                "ubicado": True,
                "id_movimiento": movimiento["id_movimiento"]
            }
        )

        await self._recalcular_estado_orden(
            recepcion["id_orden_reposicion"]
        )

        riesgo_despues = await self._obtener_riesgo(
            id_inventario
        )
        return await self._notificar_cierre(
            recepcion,
            actualizado,
            riesgo_antes,
            riesgo_despues
        )

    async def _obtener_riesgo(self, id_inventario):
        try:
            from app.services.inventory_risk_service import (
                InventoryRiskService
            )
            return await InventoryRiskService().evaluar(
                id_inventario,
                generar_alertas=False
            )
        except Exception:
            return None

    async def _notificar_cierre(
        self,
        recepcion,
        detalle,
        riesgo_antes,
        riesgo_despues
    ):
        antes = (
            riesgo_antes.riesgo.nivel.value
            if riesgo_antes else "NO_DISPONIBLE"
        )
        despues = (
            riesgo_despues.riesgo.nivel.value
            if riesgo_despues else "NO_DISPONIBLE"
        )
        notificacion = await (
            self.notification_service
            .enviar_resumen_reposicion(
                detalle["id_detalle_recepcion"],
                antes,
                despues
            )
        )

        return await self.repository.actualizar(
            detalle["id_detalle_recepcion"],
            {
                "riesgo_antes": antes,
                "riesgo_despues": despues,
                "notificacion_final": notificacion
            }
        )

    # ========================================================
    # RECALCULAR ESTADO DE ORDEN
    # ========================================================

    async def _recalcular_estado_orden(
        self,
        id_orden: str
    ):

        detalles_orden = (
            await self.detalle_reposicion_repository
            .obtener_por_orden(
                id_orden
            )
        )

        if not detalles_orden:
            return

        # ====================================================
        # TOTAL SOLICITADO
        # ====================================================

        total_solicitado = sum(
            detalle[
                "cantidad_solicitada"
            ]
            for detalle in detalles_orden
        )

        # ====================================================
        # TOTAL ACEPTADO
        # ====================================================

        total_aceptado = 0

        for detalle_orden in detalles_orden:

            recepciones = (
                await self.repository
                .obtener_por_detalle_reposicion(
                    detalle_orden[
                        "id_detalle_reposicion"
                    ]
                )
            )

            total_aceptado += sum(
                recepcion.get(
                    "cantidad_aceptada",
                    0
                )
                for recepcion in recepciones
            )

        # ====================================================
        # DETERMINAR ESTADO
        # ====================================================

        if (
            total_aceptado
            >= total_solicitado
        ):

            nuevo_estado = "RECIBIDA"

        elif total_aceptado > 0:

            nuevo_estado = "PARCIAL"

        else:

            return

        # ====================================================
        # ACTUALIZAR ORDEN
        # ====================================================

        await self.orden_repository.cambiar_estado(
            id_orden,
            nuevo_estado
        )

    # ========================================================
    # OBTENER POR ID
    # ========================================================

    async def obtener_por_id(
        self,
        id_detalle: str
    ):

        detalle = (
            await self.repository
            .obtener_por_id(
                id_detalle
            )
        )

        if not detalle:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Detalle de recepción "
                    "no encontrado"
                )
            )

        return detalle

    # ========================================================
    # OBTENER POR RECEPCION
    # ========================================================

    async def obtener_por_recepcion(
        self,
        id_recepcion: str
    ):

        recepcion = (
            await self.recepcion_repository
            .obtener_por_id(
                id_recepcion
            )
        )

        if not recepcion:

            raise HTTPException(
                status_code=404,
                detail="Recepción no encontrada"
            )

        return (
            await self.repository
            .obtener_por_recepcion(
                id_recepcion
            )
        )