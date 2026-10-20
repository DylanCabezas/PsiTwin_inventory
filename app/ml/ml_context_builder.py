# app/ml/ml_context_builder.py

from __future__ import annotations

from datetime import (
    date,
    datetime,
    time,
    timedelta,
    timezone
)

from typing import (
    Any,
    Dict,
    List,
    Optional
)

from app.repositories.inventario_repository import (
    InventarioRepository
)

from app.repositories.producto_repository import (
    ProductoRepository
)

from app.repositories.rack_repository import (
    RackRepository
)

from app.repositories.zona_repository import (
    ZonaRepository
)

from app.repositories.almacen_repository import (
    AlmacenRepository
)

from app.repositories.movimiento_repository import (
    MovimientoRepository
)


class MLContextBuilder:

    MAX_LAG = 28


    # ============================================================
    # INIT
    # ============================================================

    def __init__(
        self
    ) -> None:

        self.inventario_repository = (
            InventarioRepository()
        )

        self.producto_repository = (
            ProductoRepository
        )

        self.rack_repository = (
            RackRepository
        )

        self.zona_repository = (
            ZonaRepository
        )

        self.almacen_repository = (
            AlmacenRepository
        )

        self.movimiento_repository = (
            MovimientoRepository()
        )


    # ============================================================
    # OBTENER ID
    # ============================================================

    @staticmethod
    def _obtener_id(
        documento: Optional[
            Dict[str, Any]
        ],
        *campos: str
    ) -> Optional[str]:

        if not documento:
            return None

        for campo in campos:

            valor = documento.get(
                campo
            )

            if valor is None:
                continue

            valor = str(
                valor
            ).strip()

            if valor:
                return valor

        return None


    # ============================================================
    # IDS PRODUCTOS
    # ============================================================

    @classmethod
    def _obtener_ids_productos(
        cls,
        productos: List[
            Dict[str, Any]
        ]
    ) -> List[str]:

        ids_productos = []

        for producto in productos:

            id_producto = (
                cls._obtener_id(
                    producto,
                    "id_producto",
                    "id"
                )
            )

            if id_producto:

                ids_productos.append(
                    id_producto
                )

        return list(
            dict.fromkeys(
                ids_productos
            )
        )


    # ============================================================
    # NORMALIZAR TEXTO
    # ============================================================

    @staticmethod
    def _normalizar_texto(
        valor: Any
    ) -> Optional[str]:

        if valor is None:
            return None

        valor = str(
            valor
        ).strip()

        if not valor:
            return None

        return valor


    # ============================================================
    # NORMALIZAR FECHA
    # ============================================================

    @staticmethod
    def _normalizar_fecha_base(
        fecha_base: Optional[
            date | datetime
        ] = None
    ) -> date:

        if fecha_base is None:

            return (
                datetime.now(
                    timezone.utc
                )
                .date()
            )

        if isinstance(
            fecha_base,
            datetime
        ):

            return fecha_base.date()

        if isinstance(
            fecha_base,
            date
        ):

            return fecha_base

        raise TypeError(
            "fecha_base debe ser "
            "date, datetime o None."
        )


    # ============================================================
    # VALIDAR HORIZON
    # ============================================================

    @staticmethod
    def _validar_horizon(
        horizon: int
    ) -> int:

        try:

            horizon = int(
                horizon
            )

        except (
            TypeError,
            ValueError
        ):

            raise ValueError(
                "horizon debe ser un entero."
            )

        if horizon < 1 or horizon > 7:

            raise ValueError(
                "horizon debe estar "
                "entre 1 y 7."
            )

        return horizon


    # ============================================================
    # RANGO DE FECHAS
    # ============================================================

    @classmethod
    def _obtener_rango_fechas(
        cls,
        fecha_base: date
    ) -> tuple[
        datetime,
        datetime
    ]:

        fecha_inicio_date = (

            fecha_base

            - timedelta(
                days=cls.MAX_LAG
            )
        )

        fecha_inicio = datetime.combine(
            fecha_inicio_date,
            time.min,
            tzinfo=timezone.utc
        )

        fecha_fin = datetime.combine(
            fecha_base,
            time.max,
            tzinfo=timezone.utc
        )

        return (
            fecha_inicio,
            fecha_fin
        )


    # ============================================================
    # CREAR SERIE DIARIA
    #
    # Los días sin SALIDA son demanda 0.
    # ============================================================

    @classmethod
    def _crear_serie_diaria(
        cls,
        consumos: List[
            Dict[str, Any]
        ],
        fecha_base: date
    ) -> Dict[
        date,
        float
    ]:

        fecha_inicio = (

            fecha_base

            - timedelta(
                days=cls.MAX_LAG
            )
        )

        serie = {}

        fecha_actual = fecha_inicio

        while fecha_actual <= fecha_base:

            serie[
                fecha_actual
            ] = 0.0

            fecha_actual += timedelta(
                days=1
            )

        for registro in consumos:

            fecha = registro.get(
                "fecha"
            )

            cantidad = registro.get(
                "cantidad",
                0
            )

            if fecha is None:
                continue

            try:

                if isinstance(
                    fecha,
                    datetime
                ):

                    fecha_registro = (
                        fecha.date()
                    )

                elif isinstance(
                    fecha,
                    date
                ):

                    fecha_registro = fecha

                else:

                    fecha_registro = (
                        datetime.strptime(
                            str(fecha),
                            "%Y-%m-%d"
                        )
                        .date()
                    )

            except (
                TypeError,
                ValueError
            ):

                continue

            if fecha_registro not in serie:
                continue

            try:

                cantidad_float = float(
                    cantidad
                )

            except (
                TypeError,
                ValueError
            ):

                cantidad_float = 0.0

            serie[
                fecha_registro
            ] += cantidad_float

        return serie


    # ============================================================
    # LAG
    # ============================================================

    @staticmethod
    def _lag(
        serie: Dict[
            date,
            float
        ],
        fecha_base: date,
        lag: int
    ) -> float:

        fecha_objetivo = (

            fecha_base

            - timedelta(
                days=lag
            )
        )

        return float(
            serie.get(
                fecha_objetivo,
                0.0
            )
        )


    # ============================================================
    # MEDIA ANTERIOR
    #
    # Equivalente a:
    #
    # shift(1).rolling(...)
    # ============================================================

    @staticmethod
    def _mean_anterior(
        serie: Dict[
            date,
            float
        ],
        fecha_base: date,
        window: int
    ) -> float:

        valores = []

        for lag in range(
            1,
            window + 1
        ):

            fecha_objetivo = (

                fecha_base

                - timedelta(
                    days=lag
                )
            )

            valores.append(
                float(
                    serie.get(
                        fecha_objetivo,
                        0.0
                    )
                )
            )

        if not valores:
            return 0.0

        return float(
            sum(valores)
            / len(valores)
        )


    # ============================================================
    # ITEM FEATURES
    # ============================================================

    @classmethod
    def _crear_item_features(
        cls,
        serie: Dict[
            date,
            float
        ],
        fecha_base: date
    ) -> Dict[str, float]:

        return {

            "item_total_lag_1":
                cls._lag(
                    serie,
                    fecha_base,
                    1
                ),

            "item_total_lag_7":
                cls._lag(
                    serie,
                    fecha_base,
                    7
                ),

            "item_total_lag_28":
                cls._lag(
                    serie,
                    fecha_base,
                    28
                )
        }


    # ============================================================
    # DEPARTMENT FEATURES
    # ============================================================

    @classmethod
    def _crear_dept_features(
        cls,
        serie: Dict[
            date,
            float
        ],
        fecha_base: date
    ) -> Dict[str, float]:

        return {

            "dept_sales_lag_1":
                cls._lag(
                    serie,
                    fecha_base,
                    1
                ),

            "dept_sales_lag_7":
                cls._lag(
                    serie,
                    fecha_base,
                    7
                ),

            "dept_sales_lag_28":
                cls._lag(
                    serie,
                    fecha_base,
                    28
                ),

            "dept_sales_mean_7":
                cls._mean_anterior(
                    serie,
                    fecha_base,
                    7
                ),

            "dept_sales_mean_28":
                cls._mean_anterior(
                    serie,
                    fecha_base,
                    28
                )
        }


    # ============================================================
    # STORE FEATURES
    # ============================================================

    @classmethod
    def _crear_store_features(
        cls,
        serie: Dict[
            date,
            float
        ],
        fecha_base: date
    ) -> Dict[str, float]:

        return {

            "store_sales_lag_1":
                cls._lag(
                    serie,
                    fecha_base,
                    1
                ),

            "store_sales_lag_7":
                cls._lag(
                    serie,
                    fecha_base,
                    7
                ),

            "store_sales_lag_28":
                cls._lag(
                    serie,
                    fecha_base,
                    28
                ),

            "store_sales_mean_7":
                cls._mean_anterior(
                    serie,
                    fecha_base,
                    7
                ),

            "store_sales_mean_28":
                cls._mean_anterior(
                    serie,
                    fecha_base,
                    28
                )
        }


    # ============================================================
    # FUTURE HIERARCHICAL FEATURES
    #
    # ENTRENAMIENTO V3.6:
    #
    # future_store_lag_7 =
    #     store_sales.shift(7 - horizon)
    #
    # future_dept_lag_7 =
    #     dept_sales.shift(7 - horizon)
    #
    # D+1 -> lag 6
    # D+2 -> lag 5
    # ...
    # D+7 -> lag 0
    # ============================================================

    @classmethod
    def _crear_future_features(
        cls,
        serie_almacen: Dict[
            date,
            float
        ],
        serie_departamento: Dict[
            date,
            float
        ],
        fecha_base: date,
        horizon: int
    ) -> Dict[str, float]:

        horizon = (
            cls._validar_horizon(
                horizon
            )
        )

        effective_lag = (
            7 - horizon
        )

        return {

            "future_store_lag_7":
                cls._lag(
                    serie_almacen,
                    fecha_base,
                    effective_lag
                ),

            "future_dept_lag_7":
                cls._lag(
                    serie_departamento,
                    fecha_base,
                    effective_lag
                )
        }


    # ============================================================
    # BUILD
    # ============================================================

    async def build(
        self,
        id_inventario: str,
        fecha_base: Optional[
            date | datetime
        ] = None
    ) -> Dict[str, Any]:

        # ========================================================
        # VALIDAR ID
        # ========================================================

        if id_inventario is None:

            raise ValueError(
                "id_inventario es obligatorio."
            )

        id_inventario = str(
            id_inventario
        ).strip()

        if not id_inventario:

            raise ValueError(
                "id_inventario no puede estar vacío."
            )


        # ========================================================
        # FECHA BASE
        # ========================================================

        fecha_base_normalizada = (
            self._normalizar_fecha_base(
                fecha_base
            )
        )

        (
            fecha_inicio_query,
            fecha_fin_query
        ) = (
            self._obtener_rango_fechas(
                fecha_base_normalizada
            )
        )


        # ========================================================
        # INVENTARIO
        # ========================================================

        inventario = await (
            self.inventario_repository
            .obtener_por_id(
                id_inventario
            )
        )

        if not inventario:

            raise ValueError(
                "No existe el inventario "
                f"con id {id_inventario}."
            )


        # ========================================================
        # PRODUCTO
        # ========================================================

        id_producto = (
            self._obtener_id(
                inventario,
                "id_producto"
            )
        )

        if not id_producto:

            raise ValueError(
                "El inventario no tiene "
                "id_producto asociado."
            )

        producto = await (
            self.producto_repository
            .obtener_por_id(
                id_producto
            )
        )

        if not producto:

            raise ValueError(
                "No se encontró el producto "
                f"{id_producto}."
            )


        # ========================================================
        # RACK
        # ========================================================

        id_rack = (
            self._obtener_id(
                inventario,
                "id_rack"
            )
        )

        if not id_rack:

            id_rack = (
                self._obtener_id(
                    producto,
                    "id_rack"
                )
            )

        if not id_rack:

            raise ValueError(
                "No se pudo determinar "
                "el rack del inventario."
            )

        rack = await (
            self.rack_repository
            .obtener_por_id(
                id_rack
            )
        )

        if not rack:

            raise ValueError(
                "No se encontró el rack "
                f"{id_rack}."
            )


        # ========================================================
        # ZONA
        # ========================================================

        id_zona = (
            self._obtener_id(
                rack,
                "id_zona"
            )
        )

        if not id_zona:

            raise ValueError(
                "El rack no tiene "
                "id_zona asociado."
            )

        zona = await (
            self.zona_repository
            .obtener_por_id(
                id_zona
            )
        )

        if not zona:

            raise ValueError(
                "No se encontró la zona "
                f"{id_zona}."
            )


        # ========================================================
        # ALMACEN
        # ========================================================

        id_almacen = (
            self._obtener_id(
                zona,
                "id_almacen"
            )
        )

        if not id_almacen:

            raise ValueError(
                "La zona no tiene "
                "id_almacen asociado."
            )

        almacen = await (
            self.almacen_repository
            .obtener_por_id(
                id_almacen
            )
        )

        if not almacen:

            raise ValueError(
                "No se encontró el almacén "
                f"{id_almacen}."
            )

        id_empresa = (
            self._obtener_id(
                almacen,
                "id_empresa"
            )
        )


        # ========================================================
        # CATEGORIA
        # ========================================================

        categoria = (
            self._normalizar_texto(
                producto.get(
                    "categoria"
                )
            )
        )


        # ========================================================
        # PRODUCTOS DEL ALMACEN
        # ========================================================

        productos_almacen = await (
            self.producto_repository
            .obtener_por_almacen(
                id_almacen
            )
        )

        ids_productos_almacen = (
            self._obtener_ids_productos(
                productos_almacen
            )
        )


        # ========================================================
        # CATEGORIA GLOBAL
        # ========================================================

        productos_categoria_global = []

        if categoria:

            productos_categoria_global = await (
                self.producto_repository
                .obtener_por_categoria(
                    categoria
                )
            )

        ids_productos_categoria_global = (
            self._obtener_ids_productos(
                productos_categoria_global
            )
        )


        # ========================================================
        # CATEGORIA DENTRO DEL ALMACEN
        # ========================================================

        productos_categoria_almacen = []

        if categoria:

            categoria_normalizada = (
                categoria.casefold()
            )

            for producto_almacen in (
                productos_almacen
            ):

                categoria_producto = (
                    self._normalizar_texto(
                        producto_almacen.get(
                            "categoria"
                        )
                    )
                )

                if not categoria_producto:
                    continue

                if (
                    categoria_producto.casefold()
                    == categoria_normalizada
                ):

                    productos_categoria_almacen.append(
                        producto_almacen
                    )

        ids_productos_categoria_almacen = (
            self._obtener_ids_productos(
                productos_categoria_almacen
            )
        )


        # ========================================================
        # CONSUMO PRODUCTO
        # ========================================================

        consumo_producto = await (
            self.movimiento_repository
            .obtener_consumo_diario_producto(

                id_producto=
                    id_producto,

                fecha_inicio=
                    fecha_inicio_query,

                fecha_fin=
                    fecha_fin_query
            )
        )

        serie_producto = (
            self._crear_serie_diaria(

                consumos=
                    consumo_producto,

                fecha_base=
                    fecha_base_normalizada
            )
        )


        # ========================================================
        # CONSUMO DEPARTAMENTO
        # ========================================================

        consumo_categoria_almacen = []

        if ids_productos_categoria_almacen:

            consumo_categoria_almacen = await (
                self.movimiento_repository
                .obtener_consumo_diario_productos(

                    ids_productos=
                        ids_productos_categoria_almacen,

                    fecha_inicio=
                        fecha_inicio_query,

                    fecha_fin=
                        fecha_fin_query
                )
            )

        serie_categoria_almacen = (
            self._crear_serie_diaria(

                consumos=
                    consumo_categoria_almacen,

                fecha_base=
                    fecha_base_normalizada
            )
        )


        # ========================================================
        # CONSUMO ALMACEN
        # ========================================================

        consumo_almacen = []

        if ids_productos_almacen:

            consumo_almacen = await (
                self.movimiento_repository
                .obtener_consumo_diario_productos(

                    ids_productos=
                        ids_productos_almacen,

                    fecha_inicio=
                        fecha_inicio_query,

                    fecha_fin=
                        fecha_fin_query
                )
            )

        serie_almacen = (
            self._crear_serie_diaria(

                consumos=
                    consumo_almacen,

                fecha_base=
                    fecha_base_normalizada
            )
        )


        # ========================================================
        # FEATURES BASE
        # ========================================================

        item_features = (
            self._crear_item_features(
                serie_producto,
                fecha_base_normalizada
            )
        )

        dept_features = (
            self._crear_dept_features(
                serie_categoria_almacen,
                fecha_base_normalizada
            )
        )

        store_features = (
            self._crear_store_features(
                serie_almacen,
                fecha_base_normalizada
            )
        )

        aggregate_features = {

            **store_features,
            **dept_features,
            **item_features
        }


        # ========================================================
        # FUTURE FEATURES D+1 ... D+7
        # ========================================================

        future_features_by_horizon = {}

        for horizon in range(
            1,
            8
        ):

            future_features_by_horizon[
                horizon
            ] = (
                self._crear_future_features(

                    serie_almacen=
                        serie_almacen,

                    serie_departamento=
                        serie_categoria_almacen,

                    fecha_base=
                        fecha_base_normalizada,

                    horizon=
                        horizon
                )
            )


        # ========================================================
        # DEBUG FUTURE
        # ========================================================

        future_debug = {}

        for horizon in range(
            1,
            8
        ):

            effective_lag = (
                7 - horizon
            )

            future_debug[
                f"D+{horizon}"
            ] = {

                "effective_lag":
                    effective_lag,

                **future_features_by_horizon[
                    horizon
                ]
            }


        # ========================================================
        # RESPONSE
        # ========================================================

        return {

            "context":
                aggregate_features,

            "future_features_by_horizon":
                future_features_by_horizon,

            "future_debug":
                future_debug,

            "identificacion": {

                "id_inventario":
                    id_inventario,

                "id_producto":
                    id_producto,

                "categoria":
                    categoria,

                "id_rack":
                    id_rack,

                "id_zona":
                    id_zona,

                "id_almacen":
                    id_almacen,

                "id_empresa":
                    id_empresa
            },

            "periodo_agregacion": {

                "fecha_inicio":
                    (
                        fecha_base_normalizada
                        - timedelta(
                            days=self.MAX_LAG
                        )
                    ).isoformat(),

                "fecha_base":
                    fecha_base_normalizada.isoformat(),

                "dias":
                    self.MAX_LAG + 1
            },

            "inventario": {

                "id_inventario":
                    id_inventario,

                "id_producto":
                    id_producto,

                "id_rack":
                    id_rack,

                "stock_actual":
                    inventario.get(
                        "stock_actual"
                    ),

                "stock_minimo":
                    inventario.get(
                        "stock_minimo"
                    ),

                "stock_maximo":
                    inventario.get(
                        "stock_maximo"
                    )
            },

            "producto": {

                "id_producto":
                    id_producto,

                "nombre":
                    producto.get(
                        "nombre"
                    ),

                "categoria":
                    categoria,

                "marca":
                    producto.get(
                        "marca"
                    ),

                "id_rack":
                    producto.get(
                        "id_rack"
                    )
            },

            "rack": {

                "id_rack":
                    self._obtener_id(
                        rack,
                        "id_rack",
                        "id"
                    ),

                "id_zona":
                    id_zona,

                "nivel":
                    rack.get(
                        "nivel"
                    ),

                "capacidad":
                    rack.get(
                        "capacidad"
                    ),

                "estado":
                    rack.get(
                        "estado"
                    )
            },

            "zona": {

                "id_zona":
                    self._obtener_id(
                        zona,
                        "id_zona",
                        "id"
                    ),

                "id_almacen":
                    id_almacen,

                "nombre":
                    zona.get(
                        "nombre"
                    ),

                "tipo_zona":
                    zona.get(
                        "tipo_zona"
                    )
            },

            "almacen": {

                "id_almacen":
                    self._obtener_id(
                        almacen,
                        "id_almacen",
                        "id"
                    ),

                "id_empresa":
                    id_empresa,

                "nombre":
                    almacen.get(
                        "nombre"
                    ),

                "ubicacion":
                    almacen.get(
                        "ubicacion"
                    )
            },

            "agrupaciones": {

                "producto_actual": {

                    "id_producto":
                        id_producto,

                    "scope":
                        "producto_actual",

                    "cantidad_registros_consumo":
                        len(
                            consumo_producto
                        )
                },

                "categoria_global": {

                    "nombre":
                        categoria,

                    "cantidad_productos":
                        len(
                            ids_productos_categoria_global
                        ),

                    "ids_productos":
                        ids_productos_categoria_global,

                    "usado_para_dept_sales":
                        False
                },

                "categoria_en_almacen": {

                    "nombre":
                        categoria,

                    "id_almacen":
                        id_almacen,

                    "cantidad_productos":
                        len(
                            ids_productos_categoria_almacen
                        ),

                    "ids_productos":
                        ids_productos_categoria_almacen,

                    "usado_para_dept_sales":
                        True
                },

                "almacen": {

                    "id_almacen":
                        id_almacen,

                    "cantidad_productos":
                        len(
                            ids_productos_almacen
                        ),

                    "ids_productos":
                        ids_productos_almacen,

                    "usado_para_store_sales":
                        True
                }
            },

            "aggregate_features": {

                "store":
                    store_features,

                "department":
                    dept_features,

                "item":
                    item_features
            },

            "features_generadas": {

                "cantidad":
                    len(
                        aggregate_features
                    ),

                "nombres":
                    list(
                        aggregate_features.keys()
                    )
            }
        }


    # ============================================================
    # BASE CONTEXT
    # ============================================================

    async def build_base_context(
        self,
        id_inventario: str,
        fecha_base: Optional[
            date | datetime
        ] = None
    ) -> Dict[str, Any]:

        return await self.build(

            id_inventario=
                id_inventario,

            fecha_base=
                fecha_base
        )


    # ============================================================
    # FEATURE CONTEXT PARA UN HORIZON
    #
    # Devuelve:
    #
    # 13 features base
    # +
    # 2 future hierarchical
    #
    # TOTAL = 15
    # ============================================================

    async def build_feature_context(
        self,
        id_inventario: str,
        fecha_base: Optional[
            date | datetime
        ] = None,
        horizon: int = 1
    ) -> Dict[str, Any]:

        horizon = (
            self._validar_horizon(
                horizon
            )
        )

        resultado = await self.build(

            id_inventario=
                id_inventario,

            fecha_base=
                fecha_base
        )

        context = {

            **resultado[
                "context"
            ],

            **resultado[
                "future_features_by_horizon"
            ][
                horizon
            ]
        }

        return context


    # ============================================================
    # CONTEXTOS D+1 ... D+7
    #
    # Hace una sola lectura completa del contexto y genera
    # los siete contextos sin repetir consultas MongoDB.
    # ============================================================

    async def build_feature_contexts_7_days(
        self,
        id_inventario: str,
        fecha_base: Optional[
            date | datetime
        ] = None
    ) -> Dict[
        int,
        Dict[str, Any]
    ]:

        resultado = await self.build(

            id_inventario=
                id_inventario,

            fecha_base=
                fecha_base
        )

        base_context = (
            resultado[
                "context"
            ]
        )

        contexts = {}

        for horizon in range(
            1,
            8
        ):

            contexts[
                horizon
            ] = {

                **base_context,

                **resultado[
                    "future_features_by_horizon"
                ][
                    horizon
                ]
            }

        return contexts