from __future__ import annotations

from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone
)

from typing import (
    Optional,
    Dict,
    Any,
    List
)

import pandas as pd

from app.repositories.movimiento_repository import (
    MovimientoRepository
)

from app.repositories.inventario_repository import (
    InventarioRepository
)


class DemandHistory:
    """
    Construye el historial diario de demanda utilizado
    posteriormente por FeatureBuilder y LightGBM.

    Fuente:

        Movimiento
            ↓
        tipo = SALIDA
            ↓
        suma de cantidad por día
            ↓
        serie diaria

    Los días sin SALIDA se rellenan con demanda 0.
    """

    # ============================================================
    # INIT
    # ============================================================

    def __init__(
        self,
        movimiento_repository: Optional[
            MovimientoRepository
        ] = None,
        inventario_repository: Optional[
            InventarioRepository
        ] = None
    ) -> None:

        self.movimiento_repository = (
            movimiento_repository
            or MovimientoRepository()
        )

        self.inventario_repository = (
            inventario_repository
            or InventarioRepository()
        )

    # ============================================================
    # NORMALIZAR FECHA
    # ============================================================

    @staticmethod
    def _inicio_dia(
        fecha: date | datetime
    ) -> datetime:

        if isinstance(
            fecha,
            datetime
        ):

            fecha = fecha.date()

        return datetime.combine(
            fecha,
            time.min,
            tzinfo=timezone.utc
        )

    @staticmethod
    def _fin_dia(
        fecha: date | datetime
    ) -> datetime:

        if isinstance(
            fecha,
            datetime
        ):

            fecha = fecha.date()

        return datetime.combine(
            fecha,
            time.max,
            tzinfo=timezone.utc
        )

    # ============================================================
    # HISTORIAL POR INVENTARIO
    # ============================================================

    async def obtener_historial(
        self,
        id_inventario: str,
        dias: int = 400,
        fecha_fin: Optional[
            date | datetime
        ] = None
    ) -> pd.DataFrame:

        if dias <= 0:

            raise ValueError(
                "dias debe ser mayor que 0."
            )

        # --------------------------------------------------------
        # VALIDAR INVENTARIO
        # --------------------------------------------------------

        inventario = (
            await self.inventario_repository
            .obtener_por_id(
                id_inventario
            )
        )

        if inventario is None:

            raise ValueError(
                "No existe el inventario "
                f"{id_inventario}."
            )

        # --------------------------------------------------------
        # FECHA FINAL
        # --------------------------------------------------------

        if fecha_fin is None:

            fecha_final_date = (
                datetime.now(
                    timezone.utc
                )
                .date()
            )

        elif isinstance(
            fecha_fin,
            datetime
        ):

            fecha_final_date = (
                fecha_fin.date()
            )

        else:

            fecha_final_date = (
                fecha_fin
            )

        # --------------------------------------------------------
        # FECHA INICIAL
        # --------------------------------------------------------

        fecha_inicial_date = (
            fecha_final_date
            - timedelta(
                days=dias - 1
            )
        )

        fecha_inicio_query = (
            self._inicio_dia(
                fecha_inicial_date
            )
        )

        fecha_fin_query = (
            self._fin_dia(
                fecha_final_date
            )
        )

        # --------------------------------------------------------
        # CONSULTAR MONGODB
        # --------------------------------------------------------

        consumo = (
            await self.movimiento_repository
            .obtener_consumo_diario_inventario(
                id_inventario=
                    id_inventario,

                fecha_inicio=
                    fecha_inicio_query,

                fecha_fin=
                    fecha_fin_query
            )
        )

        # --------------------------------------------------------
        # CALENDARIO COMPLETO
        # --------------------------------------------------------

        fechas = pd.date_range(
            start=fecha_inicial_date,
            end=fecha_final_date,
            freq="D"
        )

        historial = pd.DataFrame(
            {
                "fecha":
                    fechas
            }
        )

        # Por defecto no hubo consumo.
        historial[
            "demanda"
        ] = 0.0

        # --------------------------------------------------------
        # SI EXISTEN MOVIMIENTOS
        # --------------------------------------------------------

        if consumo:

            consumo_df = pd.DataFrame(
                consumo
            )

            consumo_df[
                "fecha"
            ] = pd.to_datetime(
                consumo_df[
                    "fecha"
                ]
            )

            consumo_df[
                "cantidad"
            ] = pd.to_numeric(
                consumo_df[
                    "cantidad"
                ],
                errors="coerce"
            ).fillna(
                0
            )

            consumo_df = (
                consumo_df[
                    [
                        "fecha",
                        "cantidad"
                    ]
                ]
                .rename(
                    columns={
                        "cantidad":
                            "demanda"
                    }
                )
            )

            # ----------------------------------------------------
            # MERGE
            # ----------------------------------------------------

            historial = (
                historial[
                    [
                        "fecha"
                    ]
                ]
                .merge(
                    consumo_df,
                    how="left",
                    on="fecha"
                )
            )

            historial[
                "demanda"
            ] = (
                historial[
                    "demanda"
                ]
                .fillna(
                    0
                )
                .astype(
                    float
                )
            )

        # --------------------------------------------------------
        # ORDEN
        # --------------------------------------------------------

        historial = (
            historial
            .sort_values(
                "fecha"
            )
            .reset_index(
                drop=True
            )
        )

        return historial

    # ============================================================
    # HISTORIAL COMPLETO DISPONIBLE
    # ============================================================

    async def obtener_historial_completo(
        self,
        id_inventario: str
    ) -> pd.DataFrame:

        inventario = (
            await self.inventario_repository
            .obtener_por_id(
                id_inventario
            )
        )

        if inventario is None:

            raise ValueError(
                "Inventario no encontrado."
            )

        movimientos = (
            await self.movimiento_repository
            .obtener_por_inventario(
                id_inventario
            )
        )

        salidas = [

            movimiento

            for movimiento in movimientos

            if (
                movimiento.get(
                    "tipo_movimiento"
                )
                == "SALIDA"
            )

            and movimiento.get(
                "fecha_hora"
            )
        ]

        if not salidas:

            return pd.DataFrame(
                columns=[
                    "fecha",
                    "demanda"
                ]
            )

        fecha_minima = min(
            movimiento[
                "fecha_hora"
            ]
            for movimiento in salidas
        )

        fecha_maxima = datetime.now(
            timezone.utc
        )

        dias = (
            fecha_maxima.date()
            - fecha_minima.date()
        ).days + 1

        return await self.obtener_historial(
            id_inventario=
                id_inventario,

            dias=
                dias,

            fecha_fin=
                fecha_maxima
        )

    # ============================================================
    # INFORMACION DEL HISTORIAL
    # ============================================================

    async def obtener_resumen(
        self,
        id_inventario: str,
        dias: int = 400
    ) -> Dict[str, Any]:

        historial = (
            await self.obtener_historial(
                id_inventario=
                    id_inventario,

                dias=
                    dias
            )
        )

        if historial.empty:

            return {
                "id_inventario":
                    id_inventario,

                "dias":
                    0,

                "demanda_total":
                    0,

                "demanda_promedio":
                    0,

                "dias_con_demanda":
                    0,

                "dias_sin_demanda":
                    0,

                "historial_suficiente_ml":
                    False
            }

        demanda = historial[
            "demanda"
        ]

        dias_con_demanda = int(
            (
                demanda > 0
            ).sum()
        )

        dias_sin_demanda = int(
            (
                demanda == 0
            ).sum()
        )

        return {

            "id_inventario":
                id_inventario,

            "dias":
                len(
                    historial
                ),

            "fecha_inicio":
                historial[
                    "fecha"
                ]
                .min()
                .date()
                .isoformat(),

            "fecha_fin":
                historial[
                    "fecha"
                ]
                .max()
                .date()
                .isoformat(),

            "demanda_total":
                float(
                    demanda.sum()
                ),

            "demanda_promedio":
                float(
                    demanda.mean()
                ),

            "demanda_maxima":
                float(
                    demanda.max()
                ),

            "dias_con_demanda":
                dias_con_demanda,

            "dias_sin_demanda":
                dias_sin_demanda,

            # lag_366 necesita un historial largo.
            "historial_suficiente_ml":
                len(
                    historial
                ) >= 367
        }

    # ============================================================
    # ULTIMOS N DIAS
    # ============================================================

    async def obtener_ultimos_dias(
        self,
        id_inventario: str,
        dias: int
    ) -> List[Dict[str, Any]]:

        historial = (
            await self.obtener_historial(
                id_inventario=
                    id_inventario,

                dias=
                    dias
            )
        )

        resultado = []

        for _, row in (
            historial.iterrows()
        ):

            resultado.append(
                {
                    "fecha":
                        row[
                            "fecha"
                        ]
                        .date()
                        .isoformat(),

                    "demanda":
                        float(
                            row[
                                "demanda"
                            ]
                        )
                }
            )

        return resultado