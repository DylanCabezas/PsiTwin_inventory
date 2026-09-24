from datetime import datetime, timezone
from uuid import uuid4

from fastapi import HTTPException

from app.dto.recomendacion_dto import (
    RecomendacionCreate,
    RecomendacionEstadoUpdate,
    EstadoRecomendacion
)

from app.repositories.recomendacion_repository import (
    RecomendacionRepository
)


class RecomendacionService:

    def __init__(self):
        self.repository = (
            RecomendacionRepository()
        )

    async def crear(
        self,
        data: RecomendacionCreate
    ) -> dict:

        ahora = datetime.now(
            timezone.utc
        )

        recomendacion_existente = (
            await self.repository.buscar_pendiente(
                id_inventario=
                    data.id_inventario,

                tipo_recomendacion=
                    data.tipo_recomendacion.value
            )
        )

        if recomendacion_existente:

            datos_actualizados = {
                "nivel_riesgo":
                    data.nivel_riesgo.value,

                "id_alerta":
                    data.id_alerta,

                "cantidad_minima":
                    data.cantidad_minima,

                "cantidad_recomendada":
                    data.cantidad_recomendada,

                "cantidad_segura":
                    data.cantidad_segura,

                "explicacion":
                    data.explicacion,

                "origen":
                    data.origen,

                "fecha_actualizacion":
                    ahora
            }

            return (
                await self.repository.actualizar(
                    recomendacion_existente[
                        "id_recomendacion"
                    ],
                    datos_actualizados
                )
            )

        recomendacion = {
            "id_recomendacion":
                str(uuid4()),

            "id_empresa":
                data.id_empresa,

            "id_almacen":
                data.id_almacen,

            "id_inventario":
                data.id_inventario,

            "id_producto":
                data.id_producto,

            "id_alerta":
                data.id_alerta,

            "tipo_recomendacion":
                data.tipo_recomendacion.value,

            "nivel_riesgo":
                data.nivel_riesgo.value,

            "cantidad_minima":
                data.cantidad_minima,

            "cantidad_recomendada":
                data.cantidad_recomendada,

            "cantidad_segura":
                data.cantidad_segura,

            "explicacion":
                data.explicacion,

            "origen":
                data.origen,

            "estado":
                EstadoRecomendacion
                .PENDIENTE.value,

            "fecha_creacion":
                ahora,

            "fecha_actualizacion":
                ahora,

            "fecha_aplicacion":
                None
        }

        return (
            await self.repository.crear(
                recomendacion
            )
        )

    async def obtener(
        self,
        id_recomendacion: str
    ) -> dict:

        recomendacion = (
            await self.repository.obtener_por_id(
                id_recomendacion
            )
        )

        if recomendacion is None:
            raise HTTPException(
                status_code=404,
                detail=(
                    "Recomendación "
                    "no encontrada"
                )
            )

        return recomendacion

    async def listar(self):
        return (
            await self.repository.listar()
        )

    async def listar_por_empresa(
        self,
        id_empresa: str
    ):
        return (
            await self.repository
            .listar_por_empresa(
                id_empresa
            )
        )

    async def listar_por_almacen(
        self,
        id_almacen: str
    ):
        return (
            await self.repository
            .listar_por_almacen(
                id_almacen
            )
        )

    async def listar_por_producto(
        self,
        id_producto: str
    ):
        return (
            await self.repository
            .listar_por_producto(
                id_producto
            )
        )

    async def listar_por_inventario(
        self,
        id_inventario: str
    ):
        return (
            await self.repository
            .listar_por_inventario(
                id_inventario
            )
        )

    async def cambiar_estado(
        self,
        id_recomendacion: str,
        data: RecomendacionEstadoUpdate
    ) -> dict:

        await self.obtener(
            id_recomendacion
        )

        ahora = datetime.now(
            timezone.utc
        )

        datos = {
            "estado":
                data.estado.value,

            "fecha_actualizacion":
                ahora
        }

        if (
            data.estado
            == EstadoRecomendacion.APLICADA
        ):
            datos[
                "fecha_aplicacion"
            ] = ahora

        return (
            await self.repository.actualizar(
                id_recomendacion,
                datos
            )
        )