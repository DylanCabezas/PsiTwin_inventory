import math

from datetime import (
    datetime,
    timedelta,
    timezone
)

from statistics import pstdev

from fastapi import HTTPException

from app.repositories.inventory_risk_repository import (
    InventoryRiskRepository
)

from app.dto.inventory_risk_dto import (
    InventoryRiskResponse,
    ConsumoInfo,
    CoberturaInfo,
    ForecastInfo,
    SeguridadInfo,
    RiesgoInfo,
    ReposicionInfo
)

from app.dto.alerta_dto import (
    AlertaCreate,
    TipoAlerta,
    NivelRiesgo
)

from app.dto.recomendacion_dto import (
    RecomendacionCreate,
    TipoRecomendacion
)

from app.services.alerta_service import (
    AlertaService
)

from app.services.recomendacion_service import (
    RecomendacionService
)


class InventoryRiskService:

    def __init__(self):

        self.repository = (
            InventoryRiskRepository()
        )

        self.alerta_service = (
            AlertaService()
        )

        self.recomendacion_service = (
            RecomendacionService()
        )

        # Nivel de servicio aproximado del 95%
        self.z_service_level = 1.645

    # ========================================================
    # CONVERSION SEGURA
    # ========================================================

    @staticmethod
    def _safe_float(
        value,
        default: float = 0.0
    ) -> float:

        try:
            return float(value)

        except (
            TypeError,
            ValueError
        ):
            return default

    # ========================================================
    # PROMEDIO
    # ========================================================

    @staticmethod
    def _promedio(
        total: float,
        dias: int
    ) -> float:

        if dias <= 0:
            return 0.0

        return total / dias

    # ========================================================
    # TENDENCIA
    # ========================================================

    @staticmethod
    def _calcular_tendencia(
        promedio_7d: float,
        promedio_28d: float
    ) -> float:

        if promedio_28d <= 0:

            if promedio_7d > 0:
                return 100.0

            return 0.0

        return (
            (
                promedio_7d
                - promedio_28d
            )
            / promedio_28d
        ) * 100

    # ========================================================
    # CONSUMO DIARIO DE LOS ULTIMOS 28 DIAS
    # ========================================================

    @staticmethod
    def _consumo_diario_28d(
        movimientos: list,
        ahora: datetime
    ) -> list[float]:

        consumos = [
            0.0
            for _ in range(28)
        ]

        fecha_inicio = (
            ahora.date()
            - timedelta(
                days=27
            )
        )

        for movimiento in movimientos:

            fecha = movimiento.get(
                "fecha_hora"
            )

            if not isinstance(
                fecha,
                datetime
            ):
                continue

            fecha_movimiento = (
                fecha.date()
            )

            indice = (
                fecha_movimiento
                - fecha_inicio
            ).days

            if (
                0
                <= indice
                < 28
            ):

                cantidad = float(
                    movimiento.get(
                        "cantidad",
                        0
                    )
                )

                consumos[
                    indice
                ] += cantidad

        return consumos

    # ========================================================
    # NIVEL DE RIESGO
    # ========================================================

    @staticmethod
    def _calcular_nivel_riesgo(
        stock_actual: float,
        dias_cobertura: float | None,
        lead_time_dias: int,
        punto_reposicion: float
    ) -> NivelRiesgo:

        if stock_actual <= 0:

            return (
                NivelRiesgo.CRITICO
            )

        if dias_cobertura is None:

            return (
                NivelRiesgo.BAJO
            )

        if (
            lead_time_dias > 0
            and
            dias_cobertura
            <= lead_time_dias
        ):

            return (
                NivelRiesgo.CRITICO
            )

        if (
            punto_reposicion > 0
            and
            stock_actual
            <= punto_reposicion
        ):

            return (
                NivelRiesgo.ALTO
            )

        if (
            lead_time_dias > 0
            and
            dias_cobertura
            <= lead_time_dias * 1.5
        ):

            return (
                NivelRiesgo.MEDIO
            )

        return NivelRiesgo.BAJO

    # ========================================================
    # SCORE DE RIESGO
    # ========================================================

    @staticmethod
    def _calcular_score(
        stock_actual: float,
        dias_cobertura: float | None,
        lead_time_dias: int,
        punto_reposicion: float
    ) -> float:

        if stock_actual <= 0:
            return 100.0

        score = 0.0

        if (
            dias_cobertura is not None
            and
            lead_time_dias > 0
        ):

            ratio_cobertura = (
                dias_cobertura
                / lead_time_dias
            )

            if ratio_cobertura <= 1:
                score += 60

            elif ratio_cobertura <= 1.5:
                score += 40

            elif ratio_cobertura <= 2:
                score += 20

        if punto_reposicion > 0:

            ratio_stock = (
                stock_actual
                / punto_reposicion
            )

            if ratio_stock <= 0.5:
                score += 40

            elif ratio_stock <= 1:
                score += 30

            elif ratio_stock <= 1.25:
                score += 15

        return round(
            min(
                score,
                100
            ),
            2
        )

    # ========================================================
    # CALCULO DE REPOSICION
    # ========================================================

    @staticmethod
    def _calcular_reposicion(
        stock_actual: float,
        promedio_diario: float,
        stock_seguridad: float,
        lead_time_dias: int
    ) -> ReposicionInfo | None:

        if promedio_diario <= 0:
            return None

        horizonte_dias = max(
            lead_time_dias + 7,
            7
        )

        demanda_horizonte = (
            promedio_diario
            * horizonte_dias
        )

        cantidad_base = max(
            0,
            demanda_horizonte
            + stock_seguridad
            - stock_actual
        )

        cantidad_recomendada = (
            math.ceil(
                cantidad_base
            )
        )

        cantidad_minima = (
            math.ceil(
                cantidad_recomendada
                * 0.85
            )
        )

        cantidad_segura = (
            math.ceil(
                cantidad_recomendada
                * 1.15
            )
        )

        return ReposicionInfo(
            cantidad_minima=
                cantidad_minima,

            cantidad_recomendada=
                cantidad_recomendada,

            cantidad_segura=
                cantidad_segura
        )

    # ========================================================
    # EVALUAR INVENTARIO
    # ========================================================

    async def evaluar(
        self,
        id_inventario: str,
        generar_alertas: bool = True
    ) -> InventoryRiskResponse:

        # ----------------------------------------------------
        # INVENTARIO
        # ----------------------------------------------------

        inventario = (
            await self.repository
            .obtener_inventario(
                id_inventario
            )
        )

        if inventario is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Inventario no encontrado"
                )
            )

        id_producto = inventario.get(
            "id_producto"
        )

        id_rack = inventario.get(
            "id_rack"
        )

        if not id_producto:

            raise HTTPException(
                status_code=400,
                detail=(
                    "El inventario no tiene "
                    "id_producto"
                )
            )

        # ----------------------------------------------------
        # PRODUCTO
        # ----------------------------------------------------

        producto = (
            await self.repository
            .obtener_producto(
                id_producto
            )
        )

        if producto is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Producto asociado "
                    "no encontrado"
                )
            )

        id_empresa = producto.get(
            "id_empresa"
        )

        if not id_empresa:

            raise HTTPException(
                status_code=400,
                detail=(
                    "El producto no tiene "
                    "id_empresa"
                )
            )

        # ----------------------------------------------------
        # RACK
        # ----------------------------------------------------

        if not id_rack:

            id_rack = producto.get(
                "id_rack"
            )

        if not id_rack:

            raise HTTPException(
                status_code=400,
                detail=(
                    "No se pudo determinar "
                    "el rack"
                )
            )

        rack = (
            await self.repository
            .obtener_rack(
                id_rack
            )
        )

        if rack is None:

            raise HTTPException(
                status_code=404,
                detail="Rack no encontrado"
            )

        # ----------------------------------------------------
        # ZONA
        # ----------------------------------------------------

        id_zona = rack.get(
            "id_zona"
        )

        if not id_zona:

            raise HTTPException(
                status_code=400,
                detail=(
                    "El rack no tiene "
                    "id_zona"
                )
            )

        zona = (
            await self.repository
            .obtener_zona(
                id_zona
            )
        )

        if zona is None:

            raise HTTPException(
                status_code=404,
                detail="Zona no encontrada"
            )

        # ----------------------------------------------------
        # ALMACEN
        # ----------------------------------------------------

        id_almacen = zona.get(
            "id_almacen"
        )

        if not id_almacen:

            raise HTTPException(
                status_code=400,
                detail=(
                    "La zona no tiene "
                    "id_almacen"
                )
            )

        almacen = (
            await self.repository
            .obtener_almacen(
                id_almacen
            )
        )

        if almacen is None:

            raise HTTPException(
                status_code=404,
                detail=(
                    "Almacén no encontrado"
                )
            )

        # ----------------------------------------------------
        # DATOS BASE
        # ----------------------------------------------------

        stock_actual = (
            self._safe_float(
                inventario.get(
                    "stock_actual",
                    0
                )
            )
        )

        lead_time_dias = int(
            producto.get(
                "lead_time_dias",
                0
            )
            or 0
        )

        ahora = datetime.now(
            timezone.utc
        )

        fecha_28d = (
            ahora
            - timedelta(
                days=28
            )
        )

        # ----------------------------------------------------
        # MOVIMIENTOS DE SALIDA
        # ----------------------------------------------------

        movimientos = (
            await self.repository
            .obtener_salidas_desde(
                id_inventario=
                    id_inventario,

                fecha_desde=
                    fecha_28d
            )
        )

        fecha_7d = (
            ahora
            - timedelta(
                days=7
            )
        )

        fecha_14d = (
            ahora
            - timedelta(
                days=14
            )
        )

        total_7d = 0.0
        total_14d = 0.0
        total_28d = 0.0

        for movimiento in movimientos:

            fecha = movimiento.get(
                "fecha_hora"
            )

            if not isinstance(
                fecha,
                datetime
            ):
                continue

            cantidad = (
                self._safe_float(
                    movimiento.get(
                        "cantidad",
                        0
                    )
                )
            )

            total_28d += cantidad

            if fecha >= fecha_14d:
                total_14d += cantidad

            if fecha >= fecha_7d:
                total_7d += cantidad

        # ----------------------------------------------------
        # PROMEDIOS
        # ----------------------------------------------------

        promedio_7d = (
            self._promedio(
                total_7d,
                7
            )
        )

        promedio_14d = (
            self._promedio(
                total_14d,
                14
            )
        )

        promedio_28d = (
            self._promedio(
                total_28d,
                28
            )
        )

        consumo_diario = (
            promedio_7d
        )

        if consumo_diario <= 0:

            consumo_diario = (
                promedio_14d
            )

        if consumo_diario <= 0:

            consumo_diario = (
                promedio_28d
            )

        # ----------------------------------------------------
        # TENDENCIA
        # ----------------------------------------------------

        tendencia = (
            self._calcular_tendencia(
                promedio_7d=
                    promedio_7d,

                promedio_28d=
                    promedio_28d
            )
        )

        # ----------------------------------------------------
        # COBERTURA
        # ----------------------------------------------------

        dias_cobertura = None

        if consumo_diario > 0:

            dias_cobertura = (
                stock_actual
                / consumo_diario
            )

            dias_cobertura = round(
                dias_cobertura,
                2
            )

        # ----------------------------------------------------
        # VARIABILIDAD
        # ----------------------------------------------------

        consumos_diarios = (
            self._consumo_diario_28d(
                movimientos,
                ahora
            )
        )

        desviacion = 0.0

        if len(consumos_diarios) > 1:

            desviacion = pstdev(
                consumos_diarios
            )

        # ----------------------------------------------------
        # STOCK DE SEGURIDAD
        #
        # SS = Z * sigma * sqrt(L)
        # ----------------------------------------------------

        if (
            lead_time_dias > 0
            and
            desviacion > 0
        ):

            stock_seguridad = (
                self.z_service_level
                * desviacion
                * math.sqrt(
                    lead_time_dias
                )
            )

        else:

            stock_seguridad = 0.0

        stock_seguridad = round(
            stock_seguridad,
            2
        )

        # ----------------------------------------------------
        # PUNTO DE REPOSICION
        # ----------------------------------------------------

        demanda_lead_time = (
            consumo_diario
            * lead_time_dias
        )

        punto_reposicion = (
            demanda_lead_time
            + stock_seguridad
        )

        punto_reposicion = round(
            punto_reposicion,
            2
        )

        # ----------------------------------------------------
        # RIESGO
        # ----------------------------------------------------

        nivel_riesgo = (
            self._calcular_nivel_riesgo(
                stock_actual=
                    stock_actual,

                dias_cobertura=
                    dias_cobertura,

                lead_time_dias=
                    lead_time_dias,

                punto_reposicion=
                    punto_reposicion
            )
        )

        score = (
            self._calcular_score(
                stock_actual=
                    stock_actual,

                dias_cobertura=
                    dias_cobertura,

                lead_time_dias=
                    lead_time_dias,

                punto_reposicion=
                    punto_reposicion
            )
        )

        # ----------------------------------------------------
        # REPOSICION
        # ----------------------------------------------------

        reposicion = (
            self._calcular_reposicion(
                stock_actual=
                    stock_actual,

                promedio_diario=
                    consumo_diario,

                stock_seguridad=
                    stock_seguridad,

                lead_time_dias=
                    lead_time_dias
            )
        )

        # ----------------------------------------------------
        # EXPLICACION
        # ----------------------------------------------------

        if consumo_diario <= 0:

            explicacion = (
                "No existe consumo reciente "
                "suficiente para calcular una "
                "cobertura representativa."
            )

        elif (
            nivel_riesgo
            == NivelRiesgo.CRITICO
        ):

            explicacion = (
                f"El inventario tiene una cobertura "
                f"aproximada de {dias_cobertura} días, "
                f"mientras que el tiempo de reposición "
                f"es de {lead_time_dias} días. "
                f"Existe riesgo crítico de quiebre "
                f"de stock."
            )

        elif (
            nivel_riesgo
            == NivelRiesgo.ALTO
        ):

            explicacion = (
                f"El stock actual ({stock_actual}) "
                f"se encuentra por debajo o cerca "
                f"del punto de reposición "
                f"({punto_reposicion})."
            )

        elif (
            nivel_riesgo
            == NivelRiesgo.MEDIO
        ):

            explicacion = (
                f"La cobertura actual es de "
                f"{dias_cobertura} días y se está "
                f"acercando al tiempo necesario "
                f"para reponer el producto."
            )

        else:

            if dias_cobertura is None:

                explicacion = (
                    "El producto no presenta "
                    "consumo reciente suficiente "
                    "para estimar riesgo de quiebre."
                )

            else:

                explicacion = (
                    f"El inventario presenta una "
                    f"cobertura aproximada de "
                    f"{dias_cobertura} días y "
                    f"actualmente no presenta un "
                    f"riesgo significativo."
                )

        # ----------------------------------------------------
        # RESPONSE
        # ----------------------------------------------------

        resultado = InventoryRiskResponse(

            id_empresa=
                id_empresa,

            id_almacen=
                id_almacen,

            id_inventario=
                id_inventario,

            id_producto=
                id_producto,

            stock_actual=
                round(
                    stock_actual,
                    2
                ),

            consumo=ConsumoInfo(

                promedio_7d=round(
                    promedio_7d,
                    2
                ),

                promedio_14d=round(
                    promedio_14d,
                    2
                ),

                promedio_28d=round(
                    promedio_28d,
                    2
                ),

                tendencia_porcentaje=round(
                    tendencia,
                    2
                )
            ),

            cobertura=CoberturaInfo(
                dias=dias_cobertura
            ),

            lead_time_dias=
                lead_time_dias,

            # LightGBM todavía no conectado
            forecast=ForecastInfo(),

            seguridad=SeguridadInfo(

                stock_seguridad=
                    stock_seguridad,

                punto_reposicion=
                    punto_reposicion
            ),

            riesgo=RiesgoInfo(

                nivel=
                    nivel_riesgo,

                score=
                    score
            ),

            reposicion=
                reposicion,

            explicacion=
                explicacion
        )

        # ----------------------------------------------------
        # ALERTA + RECOMENDACION
        # ----------------------------------------------------

        if generar_alertas:

            await self._procesar_alerta(
                resultado
            )

        return resultado

    # ========================================================
    # GENERAR ALERTA Y RECOMENDACION
    # ========================================================

    async def _procesar_alerta(
        self,
        resultado: InventoryRiskResponse
    ):

        nivel = (
            resultado.riesgo.nivel
        )

        if nivel not in (
            NivelRiesgo.ALTO,
            NivelRiesgo.CRITICO
        ):

            return

        if (
            nivel
            == NivelRiesgo.CRITICO
        ):

            titulo = (
                "Riesgo crítico de "
                "quiebre de stock"
            )

        else:

            titulo = (
                "Inventario cerca del "
                "punto de reposición"
            )

        alerta = (
            await self.alerta_service.crear(
                AlertaCreate(

                    id_empresa=
                        resultado.id_empresa,

                    id_almacen=
                        resultado.id_almacen,

                    id_inventario=
                        resultado.id_inventario,

                    id_producto=
                        resultado.id_producto,

                    tipo_alerta=
                        TipoAlerta
                        .RIESGO_STOCKOUT,

                    nivel_riesgo=
                        nivel,

                    titulo=
                        titulo,

                    mensaje=
                        resultado.explicacion,

                    stock_actual=
                        resultado.stock_actual,

                    dias_cobertura=
                        resultado
                        .cobertura
                        .dias,

                    stock_seguridad=
                        resultado
                        .seguridad
                        .stock_seguridad,

                    punto_reposicion=
                        resultado
                        .seguridad
                        .punto_reposicion,

                    forecast_7d=
                        resultado
                        .forecast
                        .demanda_7d
                )
            )
        )

        if resultado.reposicion is None:
            return

        await self.recomendacion_service.crear(

            RecomendacionCreate(

                id_empresa=
                    resultado.id_empresa,

                id_almacen=
                    resultado.id_almacen,

                id_inventario=
                    resultado.id_inventario,

                id_producto=
                    resultado.id_producto,

                id_alerta=
                    alerta[
                        "id_alerta"
                    ],

                tipo_recomendacion=
                    TipoRecomendacion
                    .REABASTECER,

                nivel_riesgo=
                    nivel,

                cantidad_minima=
                    resultado
                    .reposicion
                    .cantidad_minima,

                cantidad_recomendada=
                    resultado
                    .reposicion
                    .cantidad_recomendada,

                cantidad_segura=
                    resultado
                    .reposicion
                    .cantidad_segura,

                explicacion=
                    resultado.explicacion,

                origen=
                    "MOTOR_SEGURIDAD"
            )
        )

    # ========================================================
    # EVALUAR TODOS
    # ========================================================

    async def evaluar_todos(
        self,
        generar_alertas: bool = False
    ) -> list[
        InventoryRiskResponse
    ]:

        inventarios = (
            await self.repository
            .listar_inventarios()
        )

        resultados = []

        for inventario in inventarios:

            id_inventario = (
                inventario.get(
                    "id_inventario"
                )
            )

            if not id_inventario:
                continue

            try:

                resultado = (
                    await self.evaluar(
                        id_inventario=
                            id_inventario,

                        generar_alertas=
                            generar_alertas
                    )
                )

                resultados.append(
                    resultado
                )

            except HTTPException:
                continue

            except Exception:
                continue

        return resultados