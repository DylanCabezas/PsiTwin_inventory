import json
from urllib import error, request

from app.config.settings import get_settings
from app.prompts.saiki_system_prompt import SAIKI_SYSTEM_PROMPT
from app.repositories.producto_repository import ProductoRepository
from app.services.alerta_service import AlertaService
from app.services.inventario_service import InventarioService
from app.services.inventory_risk_service import InventoryRiskService
from app.services.recomendacion_service import RecomendacionService


class SaikiService:

    def __init__(self):
        self.settings = get_settings()
        self.inventario_service = InventarioService()
        self.risk_service = InventoryRiskService()
        self.alerta_service = AlertaService()
        self.recomendacion_service = RecomendacionService()

    @staticmethod
    def get_system_prompt() -> str:
        return SAIKI_SYSTEM_PROMPT

    async def health(self) -> dict:
        try:
            answer = self._call_ollama(
                "Responde únicamente: conexión local disponible.",
                timeout=15,
            )
            return {
                "status": "ok",
                "ready": bool(answer),
                "ollama_base_url": self.settings.ollama_base_url,
                "model": self.settings.ollama_model,
            }
        except RuntimeError as exc:
            return {
                "status": "unavailable",
                "ready": False,
                "ollama_base_url": self.settings.ollama_base_url,
                "model": self.settings.ollama_model,
                "detail": str(exc),
            }

    async def ask(self, data) -> dict:
        context = await self._resolve_context(data)
        prompt = (
            "Usa únicamente el contexto entregado. No inventes datos. "
            "Si falta información, dilo claramente.\n\n"
            f"CONTEXTO PSI TWIN:\n{json.dumps(context, ensure_ascii=False, default=str, indent=2)}\n\n"
            f"PREGUNTA:\n{data.question}\n\n"
            "Responde en español y separa, cuando sea útil, dato real, "
            "predicción LightGBM, riesgo calculado e interpretación."
        )
        answer = self._call_ollama(prompt)
        return {
            "answer": answer,
            "model": self.settings.ollama_model,
            "base_url": self.settings.ollama_base_url,
            "source": "ollama",
            "context": context,
            "warnings": self._warnings(context),
        }

    async def _resolve_context(self, data) -> dict:
        context = dict(data.context)

        if data.id_inventario:
            inventario = await self.inventario_service.obtener_inventario(data.id_inventario)
            context["inventario"] = inventario
            id_producto = inventario.get("id_producto")
            if id_producto:
                context["producto"] = await ProductoRepository.obtener_por_id(id_producto)
            riesgo = await self.risk_service.evaluar(
                id_inventario=data.id_inventario,
                generar_alertas=False,
            )
            context["riesgo"] = riesgo.model_dump(mode="python")
            context["alertas"] = await self.alerta_service.listar_por_inventario(data.id_inventario)
            recomendaciones = await self.recomendacion_service.listar()
            context["recomendaciones"] = [
                item for item in recomendaciones
                if item.get("id_inventario") == data.id_inventario
            ]
        elif data.id_producto:
            context["producto"] = await ProductoRepository.obtener_por_id(data.id_producto)
        elif not context:
            context["inventarios"] = (await self.inventario_service.obtener_inventarios())[:20]

        return context

    def _call_ollama(self, prompt: str, timeout: int = 60) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "system": self.get_system_prompt(),
            "stream": False,
        }
        req = request.Request(
            url,
            data=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=timeout) as response:
                result = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"No se pudo obtener respuesta de Ollama en {url}: {exc}") from exc

        answer = result.get("response")
        if not answer:
            raise RuntimeError("Ollama no devolvió una respuesta útil.")
        return answer

    @staticmethod
    def _warnings(context: dict) -> list[str]:
        if "riesgo" in context:
            return ["El riesgo proviene de InventoryRiskService."]
        return []
