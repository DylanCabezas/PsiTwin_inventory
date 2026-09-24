from datetime import datetime, timezone

from fastapi import HTTPException, status

from app.database.mongodb import get_database

from app.dto.orden_reposicion_dto import (
    OrdenReposicionCreate,
    OrdenReposicionUpdate,
    EstadoOrdenReposicion
)

from app.repositories.orden_reposicion_repository import (
    OrdenReposicionRepository
)

from app.repositories.proveedor_repository import (
    ProveedorRepository
)


class OrdenReposicionService:

    def __init__(self):
        self.repository = OrdenReposicionRepository()
        self.proveedor_repository = ProveedorRepository()

    async def crear(
        self,
        data: OrdenReposicionCreate
    ):

        db = get_database()

        empresa = await db["empresas"].find_one(
            {
                "$or": [
                    {"id_empresa": data.id_empresa},
                    {"id": data.id_empresa}
                ]
            }
        )

        if not empresa:
            raise HTTPException(
                status_code=404,
                detail="Empresa no encontrada"
            )

        almacen = await db["almacenes"].find_one(
            {
                "$or": [
                    {"id_almacen": data.id_almacen},
                    {"id": data.id_almacen}
                ]
            }
        )

        if not almacen:
            raise HTTPException(
                status_code=404,
                detail="Almacén no encontrado"
            )

        if almacen.get("id_empresa") != data.id_empresa:
            raise HTTPException(
                status_code=400,
                detail="El almacén no pertenece a la empresa"
            )

        proveedor = (
            await self.proveedor_repository.obtener_por_id(
                data.id_proveedor
            )
        )

        if not proveedor:
            raise HTTPException(
                status_code=404,
                detail="Proveedor no encontrado"
            )

        if proveedor["id_empresa"] != data.id_empresa:
            raise HTTPException(
                status_code=400,
                detail="El proveedor no pertenece a la empresa"
            )

        if proveedor["estado"] != "ACTIVO":
            raise HTTPException(
                status_code=400,
                detail="El proveedor está inactivo"
            )

        documento = data.model_dump()

        documento["origen"] = data.origen.value
        documento["estado"] = (
            EstadoOrdenReposicion.PENDIENTE.value
        )

        return await self.repository.crear(documento)

    async def obtener_todos(self):
        return await self.repository.obtener_todos()

    async def obtener_por_id(self, id_orden: str):

        orden = await self.repository.obtener_por_id(
            id_orden
        )

        if not orden:
            raise HTTPException(
                status_code=404,
                detail="Orden de reposición no encontrada"
            )

        return orden

    async def obtener_por_empresa(self, id_empresa):
        return await self.repository.obtener_por_empresa(
            id_empresa
        )

    async def obtener_por_almacen(self, id_almacen):
        return await self.repository.obtener_por_almacen(
            id_almacen
        )

    async def obtener_por_proveedor(self, id_proveedor):
        return await self.repository.obtener_por_proveedor(
            id_proveedor
        )

    async def obtener_por_estado(self, estado):
        return await self.repository.obtener_por_estado(
            estado
        )

    async def actualizar(
        self,
        id_orden: str,
        data: OrdenReposicionUpdate
    ):

        orden = await self.obtener_por_id(id_orden)

        if orden["estado"] in [
            "RECIBIDA",
            "CANCELADA"
        ]:
            raise HTTPException(
                status_code=409,
                detail="La orden ya no puede modificarse"
            )

        cambios = data.model_dump(
            exclude_unset=True
        )

        return await self.repository.actualizar(
            id_orden,
            cambios
        )

    async def aprobar(self, id_orden: str):

        orden = await self.obtener_por_id(id_orden)

        if orden["estado"] != "PENDIENTE":
            raise HTTPException(
                status_code=409,
                detail="Solo una orden pendiente puede aprobarse"
            )

        return await self.repository.cambiar_estado(
            id_orden,
            "APROBADA"
        )

    async def enviar(self, id_orden: str):

        orden = await self.obtener_por_id(id_orden)

        if orden["estado"] != "APROBADA":
            raise HTTPException(
                status_code=409,
                detail="Solo una orden aprobada puede enviarse"
            )

        return await self.repository.cambiar_estado(
            id_orden,
            "ENVIADA"
        )

    async def cancelar(self, id_orden: str):

        orden = await self.obtener_por_id(id_orden)

        if orden["estado"] not in [
            "PENDIENTE",
            "APROBADA"
        ]:
            raise HTTPException(
                status_code=409,
                detail="La orden ya no puede cancelarse"
            )

        return await self.repository.cambiar_estado(
            id_orden,
            "CANCELADA"
        )

    async def eliminar(self, id_orden: str):

        orden = await self.obtener_por_id(id_orden)

        if orden["estado"] != "PENDIENTE":
            raise HTTPException(
                status_code=409,
                detail="Solo una orden pendiente puede eliminarse"
            )

        return await self.repository.eliminar(
            id_orden
        )

        return {
            "mensaje":
                "Orden de reposición eliminada correctamente"
        }