from datetime import (
    datetime,
    timezone
)

from uuid import uuid4

from fastapi import HTTPException

from app.dto.rack_dto import (
    RackCreate,
    RackUpdate
)

from app.repositories.rack_repository import (
    RackRepository
)

from app.repositories.zona_repository import (
    ZonaRepository
)


class RackService:

    def __init__(self):
        self.repository = RackRepository()
        self.zona_repository = ZonaRepository()


    async def crear_rack(
        self,
        data: RackCreate
    ):
        zona = (
            await self.zona_repository.obtener_por_id(
                data.id_zona
            )
        )

        if not zona:
            raise HTTPException(
                status_code=404,
                detail="Zona no encontrada"
            )

        codigo = data.codigo.strip().upper()

        existente = (
            await self.repository
            .obtener_por_codigo_nivel_y_zona(
                codigo,
                data.nivel,
                data.id_zona
            )
        )

        if existente:
            raise HTTPException(
                status_code=400,
                detail=(
                    "Ya existe ese código y nivel "
                    "de rack dentro de la zona"
                )
            )

        ahora = datetime.now(
            timezone.utc
        )

        rack = {
            "id_rack":
                str(uuid4()),

            "id_zona":
                data.id_zona,

            "codigo":
                codigo,

            "nivel":
                data.nivel,

            "capacidad":
                data.capacidad,

            "estado":
                data.estado.value,

            "fecha_creacion":
                ahora,

            "fecha_actualizacion":
                ahora
        }

        return await self.repository.crear(
            rack
        )


    async def obtener_racks(self):
        return await self.repository.obtener_todos()


    async def obtener_rack(
        self,
        id_rack: str
    ):
        rack = (
            await self.repository.obtener_por_id(
                id_rack
            )
        )

        if not rack:
            raise HTTPException(
                status_code=404,
                detail="Rack no encontrado"
            )

        return rack


    async def obtener_racks_zona(
        self,
        id_zona: str
    ):
        zona = (
            await self.zona_repository.obtener_por_id(
                id_zona
            )
        )

        if not zona:
            raise HTTPException(
                status_code=404,
                detail="Zona no encontrada"
            )

        return await self.repository.obtener_por_zona(
            id_zona
        )


    async def actualizar_rack(
        self,
        id_rack: str,
        data: RackUpdate
    ):
        rack_actual = (
            await self.repository.obtener_por_id(
                id_rack
            )
        )

        if not rack_actual:
            raise HTTPException(
                status_code=404,
                detail="Rack no encontrado"
            )

        datos = data.model_dump(
            exclude_unset=True
        )

        codigo_final = datos.get(
            "codigo",
            rack_actual["codigo"]
        )

        codigo_final = (
            codigo_final.strip().upper()
        )

        nivel_final = datos.get(
            "nivel",
            rack_actual["nivel"]
        )

        existente = (
            await self.repository
            .obtener_por_codigo_nivel_y_zona(
                codigo_final,
                nivel_final,
                rack_actual["id_zona"]
            )
        )

        if (
            existente
            and
            existente["id_rack"] != id_rack
        ):
            raise HTTPException(
                status_code=400,
                detail=(
                    "Ya existe ese código y nivel "
                    "de rack dentro de la zona"
                )
            )

        if "codigo" in datos:
            datos["codigo"] = codigo_final

        if "estado" in datos:
            datos["estado"] = (
                datos["estado"].value
                if hasattr(
                    datos["estado"],
                    "value"
                )
                else datos["estado"]
            )

        datos["fecha_actualizacion"] = (
            datetime.now(
                timezone.utc
            )
        )

        return await self.repository.actualizar(
            id_rack,
            datos
        )


    async def eliminar_rack(
        self,
        id_rack: str
    ):
        rack = (
            await self.repository.obtener_por_id(
                id_rack
            )
        )

        if not rack:
            raise HTTPException(
                status_code=404,
                detail="Rack no encontrado"
            )

        eliminado = (
            await self.repository.eliminar(
                id_rack
            )
        )

        return {
            "mensaje":
                "Rack eliminado correctamente",

            "eliminado":
                eliminado
        }