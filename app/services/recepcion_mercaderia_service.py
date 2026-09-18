from fastapi import HTTPException

from app.database.mongodb import get_database

from app.dto.recepcion_mercaderia_dto import (
    RecepcionMercaderiaCreate
)

from app.repositories.recepcion_mercaderia_repository import (
    RecepcionMercaderiaRepository
)

from app.repositories.orden_reposicion_repository import (
    OrdenReposicionRepository
)

from app.repositories.detalle_reposicion_repository import (
    DetalleReposicionRepository
)


class RecepcionMercaderiaService:

    def __init__(self):
        self.repository = RecepcionMercaderiaRepository()
        self.orden_repository = OrdenReposicionRepository()
        self.detalle_repository = DetalleReposicionRepository()

    async def crear(
        self,
        data: RecepcionMercaderiaCreate
    ):

        orden = await self.orden_repository.obtener_por_id(
            data.id_orden_reposicion
        )

        if not orden:
            raise HTTPException(
                status_code=404,
                detail="Orden no encontrada"
            )

        if orden["estado"] not in [
            "ENVIADA",
            "PARCIAL"
        ]:
            raise HTTPException(
                status_code=409,
                detail=(
                    "La orden debe estar ENVIADA "
                    "o PARCIAL para recibir mercancía"
                )
            )

        detalles = (
            await self.detalle_repository.obtener_por_orden(
                data.id_orden_reposicion
            )
        )

        if not detalles:
            raise HTTPException(
                status_code=409,
                detail=(
                    "La orden no contiene productos"
                )
            )

        db = get_database()

        operario = await db["operarios"].find_one(
            {"id_operario": data.id_operario}
        )

        if not operario:
            raise HTTPException(
                status_code=404,
                detail="Operario no encontrado"
            )

        if operario.get("estado") != "ACTIVO":
            raise HTTPException(
                status_code=409,
                detail="El operario está inactivo"
            )

        if (
            operario.get("id_almacen")
            != orden["id_almacen"]
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "El operario no pertenece "
                    "al almacén de la orden"
                )
            )

        return await self.repository.crear(
            data.model_dump()
        )

    async def obtener_todos(self):
        return await self.repository.obtener_todos()

    async def obtener_por_id(self, id_recepcion):

        recepcion = await self.repository.obtener_por_id(
            id_recepcion
        )

        if not recepcion:
            raise HTTPException(
                status_code=404,
                detail="Recepción no encontrada"
            )

        return recepcion

    async def obtener_por_orden(self, id_orden):
        return await self.repository.obtener_por_orden(
            id_orden
        )

    async def obtener_por_operario(self, id_operario):
        return await self.repository.obtener_por_operario(
            id_operario
        )