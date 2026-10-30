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
            payload = self._call_ollama(
                prompt="Comprueba la conexión con el modelo local.",
                include_context=False,
                timeout=15,
            )
            return {
                "status": "ok",
                "ollama_base_url": self.settings.ollama_base_url,
                "model": self.settings.ollama_model,
                "ready": bool(payload),
            }
        except Exception as exc:
            return {
                "status": "unavailable",
                "ollama_base_url": self.settings.ollama_base_url,
                "model": self.settings.ollama_model,
                "detail": str(exc),
            }

    async def ask(self, request_model) -> dict:
        context = await self._resolve_context(
            question=request_model.question,
            id_inventario=request_model.id_inventario,
            id_producto=request_model.id_producto,
            extra_context=request_model.context,
        )

        prompt = self._build_prompt(
            question=request_model.question,
            context=context,
        )

        answer = self._call_ollama(
            prompt=prompt,
            include_context=False,
            timeout=60,
        )

        return {
            "answer": answer,
            "model": self.settings.ollama_model,
            "base_url": self.settings.ollama_base_url,
            "source": "ollama",
            "context": context,
            "warnings": self._build_warnings(context),
        }

    def _build_prompt(self, question: str, context: dict) -> str:
        context_json = json.dumps(
            context,
            ensure_ascii=False,
            default=str,
            indent=2,
        )
        return (
            "Usa únicamente la información del contexto que te entrego, "
            "no inventes datos ni valores. "
            "Si falta información, dilo claramente.\n\n"
            f"CONTEXTO PSI TWIN:\n{context_json}\n\n"
            f"PREGUNTA DEL USUARIO:\n{question}\n\n"
            "Responde en español y explica brevemente qué es dato real, "
            "qué es predicción LightGBM, qué es riesgo calculado y qué es tu interpretación."
        )

    def _build_warnings(self, context: dict) -> list[str]:
        warnings: list[str] = []
        if not context:
            warnings.append("No se encontraron datos operativos para este análisis.")
        if "forecast" in context and context["forecast"] is not None:
            warnings.append("La predicción mostrada proviene del pipeline LightGBM existente.")
        if "riesgo" in context and context["riesgo"] is not None:
            warnings.append("El riesgo mostrado corresponde a InventoryRiskService.")
        return warnings

    async def _resolve_context(
        self,
        question: str,
        id_inventario: str | None,
        id_producto: str | None,
        extra_context: dict | None = None,
    ) -> dict:
        context: dict = {}

        if extra_context:
            context["contexto_extra"] = extra_context

        if id_inventario:
            try:
                inventario = await self.inventario_service.obtener_inventario(id_inventario)
                context["inventario"] = inventario
                if inventario and inventario.get("id_producto"):
                    producto = await ProductoRepository.obtener_por_id(inventario["id_producto"])
                    context["producto"] = producto
                    context["id_producto"] = inventario["id_producto"]
                try:
                    riesgo = await self.risk_service.evaluar(id_inventario=id_inventario, generar_alertas=False)
                    context["riesgo"] = riesgo.model_dump(mode="python")
                except Exception as exc:
                    context["riesgo_error"] = str(exc)
                try:
                    alertas = await self.alerta_service.listar_por_inventario(id_inventario)
                    context["alertas"] = alertas
                except Exception as exc:
                    context["alertas_error"] = str(exc)
                try:
                    recomendaciones = await self.recomendacion_service.listar()
                    context["recomendaciones"] = [
                        item for item in recomendaciones if item.get("id_inventario") == id_inventario
                    ][-10:]
                except Exception as exc:
                    context["recomendaciones_error"] = str(exc)
            except Exception as exc:
                context["inventario_error"] = str(exc)

        elif id_producto:
            try:
                producto = await ProductoRepository.obtener_por_id(id_producto)
                context["producto"] = producto
            except Exception as exc:
                context["producto_error"] = str(exc)

        if "forecast" in question.lower() or "demanda" in question.lower() or "ventas" in question.lower() or "predicci" in question.lower():
            if id_inventario:
                try:
                    riesgo = await self.risk_service.evaluar(id_inventario=id_inventario, generar_alertas=False)
                    context["forecast"] = riesgo.model_dump(mode="python").get("forecast")
                except Exception as exc:
                    context["forecast_error"] = str(exc)

        if not context:
            try:
                inventarios = await self.inventario_service.obtener_inventarios()
                context["inventarios"] = inventarios[:20]
            except Exception as exc:
                context["inventarios_error"] = str(exc)

        return context

    def _call_ollama(self, prompt: str, include_context: bool = False, timeout: int = 60) -> str:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/generate"
        payload = {
            "model": self.settings.ollama_model,
            "prompt": prompt,
            "stream": False,
            "system": self.get_system_prompt(),
        }
        if include_context:
            payload["context"] = {}

        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        req = request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=timeout) as response:
                body = response.read().decode("utf-8")
        except error.URLError as exc:
            raise RuntimeError(
                f"No se pudo conectar con Ollama en {url}. "
                f"Verifica que esté ejecutándose y que la variable OLLAMA_BASE_URL sea correcta."
            ) from exc
        except TimeoutError as exc:
            raise RuntimeError("La consulta a Ollama excedió el tiempo de espera.") from exc

        try:
            result = json.loads(body)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Ollama devolvió una respuesta no JSON: {body[:200]}") from exc

        answer = result.get("response")
        if not answer:
            raise RuntimeError("Ollama no devolvió respuesta útil.")

        return answer
