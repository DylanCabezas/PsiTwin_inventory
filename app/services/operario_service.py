from fastapi import HTTPException, status

from app.dto.operario_dto import (
    OperarioCreate,
    OperarioUpdate
)

from app.repositories.operario_repository import (
    OperarioRepository
)

from app.repositories.empresa_repository import (
    EmpresaRepository
)

from app.repositories.almacen_repository import (
    AlmacenRepository
)


class OperarioService:

    # ============================================================
    # CREAR
    # ============================================================

    async def crear_operario(
        self,
        data: OperarioCreate
    ):

        empresa = await (
            EmpresaRepository
            .obtener_por_id(
                data.id_empresa
            )
        )

        if not empresa:

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,
                detail=
                    "Empresa no encontrada"
            )

        if data.id_almacen:
            almacen = await AlmacenRepository.obtener_por_id(
                data.id_almacen
            )
            if not almacen or almacen.get("id_empresa") != data.id_empresa:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "El almacén del operario no pertenece "
                        "a la empresa"
                    )
                )


        operario_data = (
            data.model_dump()
        )

        operario_data[
            "nombre"
        ] = (
            operario_data[
                "nombre"
            ].strip()
        )

        operario_data[
            "apellido"
        ] = (
            operario_data[
                "apellido"
            ].strip()
        )

        operario_data[
            "cargo"
        ] = (
            operario_data[
                "cargo"
            ].strip()
        )

        operario_data[
            "turno"
        ] = (
            operario_data[
                "turno"
            ].strip().upper()
        )

        operario_data[
            "estado"
        ] = (
            operario_data[
                "estado"
            ].strip().upper()
        )


        return await (
            OperarioRepository
            .crear(
                operario_data
            )
        )


    # ============================================================
    # OBTENER TODOS
    # ============================================================

    async def obtener_operarios(
        self
    ):

        return await (
            OperarioRepository
            .obtener_todos()
        )


    # ============================================================
    # OBTENER POR ID
    # ============================================================

    async def obtener_operario(
        self,
        id_operario: str
    ):

        operario = await (
            OperarioRepository
            .obtener_por_id(
                id_operario
            )
        )

        if not operario:

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,
                detail=
                    "Operario no encontrado"
            )

        return operario


    # ============================================================
    # OBTENER POR EMPRESA
    # ============================================================

    async def obtener_por_empresa(
        self,
        id_empresa: str
    ):

        empresa = await (
            EmpresaRepository
            .obtener_por_id(
                id_empresa
            )
        )

        if not empresa:

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,
                detail=
                    "Empresa no encontrada"
            )

        return await (
            OperarioRepository
            .obtener_por_empresa(
                id_empresa
            )
        )


    # ============================================================
    # OBTENER POR ESTADO
    # ============================================================

    async def obtener_por_estado(
        self,
        estado: str
    ):

        estado = (
            estado
            .strip()
            .upper()
        )

        return await (
            OperarioRepository
            .obtener_por_estado(
                estado
            )
        )


    # ============================================================
    # OBTENER POR TURNO
    # ============================================================

    async def obtener_por_turno(
        self,
        turno: str
    ):

        turno = (
            turno
            .strip()
            .upper()
        )

        return await (
            OperarioRepository
            .obtener_por_turno(
                turno
            )
        )


    # ============================================================
    # ACTUALIZAR
    # ============================================================

    async def actualizar_operario(
        self,
        id_operario: str,
        data: OperarioUpdate
    ):

        operario = await (
            OperarioRepository
            .obtener_por_id(
                id_operario
            )
        )

        if not operario:

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,
                detail=
                    "Operario no encontrado"
            )


        update_data = (
            data.model_dump(
                exclude_unset=True
            )
        )

        if not update_data:
            return operario


        if (
            "nombre"
            in update_data
            and
            update_data["nombre"]
            is not None
        ):
            update_data[
                "nombre"
            ] = (
                update_data[
                    "nombre"
                ].strip()
            )


        if (
            "apellido"
            in update_data
            and
            update_data["apellido"]
            is not None
        ):
            update_data[
                "apellido"
            ] = (
                update_data[
                    "apellido"
                ].strip()
            )


        if (
            "cargo"
            in update_data
            and
            update_data["cargo"]
            is not None
        ):
            update_data[
                "cargo"
            ] = (
                update_data[
                    "cargo"
                ].strip()
            )


        if (
            "turno"
            in update_data
            and
            update_data["turno"]
            is not None
        ):
            update_data[
                "turno"
            ] = (
                update_data[
                    "turno"
                ]
                .strip()
                .upper()
            )


        if (
            "estado"
            in update_data
            and
            update_data["estado"]
            is not None
        ):
            update_data[
                "estado"
            ] = (
                update_data[
                    "estado"
                ]
                .strip()
                .upper()
            )


        actualizado = await (
            OperarioRepository
            .actualizar(
                id_operario,
                update_data
            )
        )

        if not actualizado:

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,
                detail=
                    "Operario no encontrado"
            )

        return actualizado


    # ============================================================
    # ELIMINAR
    # ============================================================

    async def eliminar_operario(
        self,
        id_operario: str
    ):

        operario = await (
            OperarioRepository
            .obtener_por_id(
                id_operario
            )
        )

        if not operario:

            raise HTTPException(
                status_code=
                    status.HTTP_404_NOT_FOUND,
                detail=
                    "Operario no encontrado"
            )


        eliminado = await (
            OperarioRepository
            .eliminar(
                id_operario
            )
        )

        if not eliminado:

            raise HTTPException(
                status_code=
                    status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=
                    "No se pudo eliminar el operario"
            )

        return {
            "mensaje":
                "Operario eliminado correctamente"
        }