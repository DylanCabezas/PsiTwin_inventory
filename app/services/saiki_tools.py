from typing import Any, Awaitable, Callable

from pydantic import BaseModel, Field

from app.controllers.forecast_controller import predict_7_days
from app.repositories.producto_repository import ProductoRepository
from app.services.alerta_service import AlertaService
from app.services.inventario_service import InventarioService
from app.services.inventory_risk_service import InventoryRiskService
from app.services.movimiento_service import MovimientoService
from app.services.recomendacion_service import RecomendacionService
from app.services.acceso_service import AccesoService


class InventoryArgs(BaseModel):
    id_inventario: str = Field(min_length=1)


class ProductArgs(BaseModel):
    id_producto: str = Field(min_length=1)


class ForecastArgs(BaseModel):
    id_inventario: str = Field(min_length=1)
    dias: int = Field(default=30, ge=7, le=500)


class OptionalInventoryArgs(BaseModel):
    id_inventario: str | None = None


ToolHandler = Callable[[BaseModel], Awaitable[Any]]


class SaikiToolRegistry:
    """Whitelist of read-only operations available to Saiki."""

    def __init__(self):
        self.inventario_service = InventarioService()
        self.risk_service = InventoryRiskService()
        self.alerta_service = AlertaService()
        self.recomendacion_service = RecomendacionService()
        self.movimiento_service = MovimientoService()
        self._handlers: dict[str, tuple[type[BaseModel], ToolHandler, str]] = {
            "get_inventory": (
                InventoryArgs,
                self.get_inventory,
                "INVENTARIO",
            ),
            "get_product": (
                ProductArgs,
                self.get_product,
                "PRODUCTO",
            ),
            "get_forecast": (
                ForecastArgs,
                self.get_forecast,
                "LIGHTGBM",
            ),
            "get_inventory_risk": (
                InventoryArgs,
                self.get_inventory_risk,
                "INVENTORY_RISK",
            ),
            "get_active_alerts": (
                OptionalInventoryArgs,
                self.get_active_alerts,
                "ALERTAS",
            ),
            "get_recommendations": (
                OptionalInventoryArgs,
                self.get_recommendations,
                "RECOMENDACIONES",
            ),
            "get_recent_movements": (
                InventoryArgs,
                self.get_recent_movements,
                "MOVIMIENTOS",
            ),
            "get_warehouse_status": (
                OptionalInventoryArgs,
                self.get_warehouse_status,
                "INVENTARIO",
            ),
        }

    @property
    def names(self) -> set[str]:
        return set(self._handlers)

    def definitions(self) -> list[dict[str, Any]]:
        return [
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": f"Consulta de solo lectura: {name}.",
                    "parameters": model.model_json_schema(),
                },
            }
            for name, (model, _, _) in self._handlers.items()
        ]

    async def execute(
        self,
        name: str,
        arguments: dict[str, Any],
        user=None,
    ) -> tuple[Any, str]:
        if name not in self._handlers:
            raise ValueError(f"Tool no autorizada: {name}")
        model, handler, source = self._handlers[name]
        try:
            validated = model.model_validate(arguments)
        except Exception as exc:
            raise ValueError(f"Argumentos inválidos para {name}: {exc}") from exc
        if user is not None:
            await self._authorize(name, validated, user)
        return await handler(validated), source

    async def _authorize(self, name: str, args: BaseModel, user) -> None:
        if hasattr(args, "id_inventario") and args.id_inventario:
            await AccesoService.verificar_inventario(user, args.id_inventario)
        if name == "get_product" and args.id_producto:
            await AccesoService.verificar_producto(user, args.id_producto)
        if name in {"get_warehouse_status", "get_active_alerts", "get_recommendations"}:
            visible = await AccesoService.ids_inventarios(user)
            if name == "get_warehouse_status":
                self._visible_inventory_ids = visible

    async def get_inventory(self, args: InventoryArgs):
        return await self.inventario_service.obtener_inventario(args.id_inventario)

    async def get_product(self, args: ProductArgs):
        return await ProductoRepository.obtener_por_id(args.id_producto)

    async def get_forecast(self, args: ForecastArgs):
        return await predict_7_days(args.id_inventario, args.dias)

    async def get_inventory_risk(self, args: InventoryArgs):
        result = await self.risk_service.evaluar(
            id_inventario=args.id_inventario,
            generar_alertas=False,
        )
        return result.model_dump(mode="python")

    async def get_active_alerts(self, args: OptionalInventoryArgs):
        if args.id_inventario:
            return await self.alerta_service.listar_por_inventario(args.id_inventario)
        alerts = await self.alerta_service.listar_activas()
        visible = getattr(self, "_visible_inventory_ids", None)
        return [item for item in alerts if visible is None or item.get("id_inventario") in visible]

    async def get_recommendations(self, args: OptionalInventoryArgs):
        if args.id_inventario:
            return await self.recomendacion_service.listar_por_inventario(
                args.id_inventario
            )
        recommendations = await self.recomendacion_service.listar()
        visible = getattr(self, "_visible_inventory_ids", None)
        return [
            item
            for item in recommendations
            if visible is None or item.get("id_inventario") in visible
        ]

    async def get_recent_movements(self, args: InventoryArgs):
        movements = await self.movimiento_service.obtener_por_inventario(
            args.id_inventario
        )
        return sorted(
            movements,
            key=lambda item: str(item.get("fecha_hora", "")),
            reverse=True,
        )[:20]

    async def get_warehouse_status(self, args: OptionalInventoryArgs):
        inventories = await self.inventario_service.obtener_inventarios()
        visible = getattr(self, "_visible_inventory_ids", None)
        if visible is not None:
            inventories = [
                item for item in inventories
                if item.get("id_inventario") in visible
            ]
        return {
            "total_inventarios": len(inventories),
            "stock_total": sum(
                item.get("stock_actual", 0) or 0 for item in inventories
            ),
            "inventarios": inventories[:20],
        }
