from fastapi import HTTPException, status

from app.dto.proveedor_dto import (
    ProveedorCreate,
    ProveedorUpdate
)

from app.repositories.proveedor_repository import (
    ProveedorRepository
)

from app.repositories.empresa_repository import (
    EmpresaRepository
)


class ProveedorService:

    def __init__(self):
        self.repository = ProveedorRepository()

    async def crear(self, data: ProveedorCreate):

        empresa = await EmpresaRepository.obtener_por_id(
            data.id_empresa
        )

        if not empresa:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Empresa no encontrada"
            )

        existente = await self.repository.obtener_por_ruc(
            data.ruc
        )

        if existente:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Ya existe un proveedor con ese RUC"
            )

        documento = data.model_dump()

        documento["estado"] = data.estado.value

        return await self.repository.crear(documento)

    async def obtener_todos(self):
        return await self.repository.obtener_todos()

    async def obtener_por_id(self, id_proveedor: str):

        proveedor = await self.repository.obtener_por_id(
            id_proveedor
        )

        if not proveedor:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Proveedor no encontrado"
            )

        return proveedor

    async def obtener_por_empresa(self, id_empresa: str):

        return await self.repository.obtener_por_empresa(
            id_empresa
        )

    async def obtener_por_estado(self, estado: str):

        return await self.repository.obtener_por_estado(
            estado
        )

    async def actualizar(
        self,
        id_proveedor: str,
        data: ProveedorUpdate
    ):

        await self.obtener_por_id(id_proveedor)

        cambios = data.model_dump(
            exclude_unset=True
        )

        if "estado" in cambios:
            cambios["estado"] = cambios["estado"].value

        return await self.repository.actualizar(
            id_proveedor,
            cambios
        )

    async def eliminar(self, id_proveedor: str):

        await self.obtener_por_id(id_proveedor)

        eliminado = await self.repository.eliminar(
            id_proveedor
        )

        if not eliminado:
            raise HTTPException(
                status_code=500,
                detail="No se pudo eliminar el proveedor"
            )

        return {
            "mensaje": "Proveedor eliminado correctamente"
        }