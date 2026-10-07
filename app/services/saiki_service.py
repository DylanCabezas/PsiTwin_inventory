import asyncio
import json
from urllib import error, request

from fastapi import HTTPException, status

from app.config.settings import get_settings
from app.dto.saiki_dto import SaikiAskRequest
from app.dto.auth_dto import UsuarioActual
from app.prompts.saiki_system_prompt import SAIKI_SYSTEM_PROMPT
from app.services.saiki_tools import SaikiToolRegistry


class SaikiService:
    max_tool_iterations = 4

    def __init__(self):
        self.settings = get_settings()
        self.tools = SaikiToolRegistry()

    @staticmethod
    def get_system_prompt() -> str:
        return SAIKI_SYSTEM_PROMPT

    async def health(self) -> dict:
        base = {
            "ollama_base_url": self.settings.ollama_base_url,
            "model": self.settings.ollama_model,
        }
        try:
            models = await asyncio.to_thread(self._installed_models)
        except RuntimeError as exc:
            return {"status": "unavailable", "ready": False, **base, "detail": str(exc)}
        if self.settings.ollama_model not in models:
            return {
                "status": "unavailable",
                "ready": False,
                **base,
                "detail": f"El modelo {self.settings.ollama_model} no está descargado en Ollama.",
            }
        return {"status": "ok", "ready": True, **base}

    def _installed_models(self) -> list[str]:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/tags"
        try:
            with request.urlopen(url, timeout=5) as response:
                data = json.loads(response.read().decode("utf-8"))
        except (error.URLError, TimeoutError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"No se pudo conectar con Ollama en {url}: {exc}") from exc
        return [model.get("name", "") for model in data.get("models", [])]

    async def ask(
        self,
        data: SaikiAskRequest,
        user: UsuarioActual | None = None,
    ) -> dict:
        context = dict(data.context)
        if data.id_inventario and user is not None:
            context["inventario"] = await self._authorized_tool(
                "get_inventory", {"id_inventario": data.id_inventario}, user
            )
        if data.id_producto and user is not None:
            context["producto"] = await self._authorized_tool(
                "get_product", {"id_producto": data.id_producto}, user
            )

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            *data.history,
            {
                "role": "user",
                "content": self._build_prompt(data.message or "", context),
            },
        ]
        try:
            answer, tool_data, sources = await self._agent_loop(messages, user)
        except ValueError as exc:
            raise HTTPException(status_code=400, detail=str(exc)) from exc
        except RuntimeError as exc:
            raise HTTPException(
                status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
                detail="Saiki no está disponible en este momento.",
            ) from exc

        return {
            "answer": answer,
            "model": self.settings.ollama_model,
            "base_url": self.settings.ollama_base_url,
            "source": "ollama",
            "context": context,
            "data": tool_data,
            "visualization": self._visualization(tool_data),
            "sources": sorted(sources),
            "warnings": self._warnings(sources),
        }

    async def _authorized_tool(self, name, arguments, user):
        result, _ = await self.tools.execute(name, arguments, user)
        return result

    async def _execute_tool(self, name, arguments, user=None):
        if user is None:
            return await self.tools.execute(name, arguments)
        return await self.tools.execute(name, arguments, user)

    async def _agent_loop(
        self,
        messages: list[dict],
        user: UsuarioActual | None = None,
    ) -> tuple[str, dict, set[str]]:
        tool_data: dict[str, object] = {}
        sources: set[str] = set()
        for _ in range(self.max_tool_iterations):
            response = await asyncio.to_thread(self._call_ollama_chat, messages)
            message = response.get("message")
            if not isinstance(message, dict):
                raise RuntimeError("Ollama devolvió un mensaje inválido.")
            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                answer = message.get("content")
                if not isinstance(answer, str) or not answer.strip():
                    raise RuntimeError("Ollama no devolvió una respuesta útil.")
                return answer.strip(), tool_data, sources

            messages.append(message)
            for tool_call in tool_calls:
                name, arguments = self._parse_tool_call(tool_call)
                result, source = await self._execute_tool(name, arguments, user)
                sources.add(source)
                tool_data[name] = result
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(result, ensure_ascii=False, default=str),
                    }
                )
        raise RuntimeError("Se alcanzó el límite de consultas de Saiki.")

    def _call_ollama_chat(self, messages: list[dict], timeout: int = 300) -> dict:
        url = f"{self.settings.ollama_base_url.rstrip('/')}/api/chat"
        payload = {
            "model": self.settings.ollama_model,
            "messages": messages,
            "tools": self.tools.definitions(),
            "stream": False,
            "think": False,
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
            raise RuntimeError(f"No se pudo obtener respuesta de Ollama: {exc}") from exc
        if not isinstance(result, dict):
            raise RuntimeError("Ollama devolvió una respuesta inválida.")
        return result

    def _parse_tool_call(self, tool_call: object) -> tuple[str, dict]:
        if not isinstance(tool_call, dict):
            raise ValueError("Tool call inválida.")
        function = tool_call.get("function")
        if not isinstance(function, dict) or not isinstance(function.get("name"), str):
            raise ValueError("Tool call inválida.")
        arguments = function.get("arguments", {})
        if isinstance(arguments, str):
            try:
                arguments = json.loads(arguments)
            except json.JSONDecodeError as exc:
                raise ValueError("Los argumentos de la tool no son JSON válido.") from exc
        if not isinstance(arguments, dict):
            raise ValueError("Los argumentos de la tool deben ser un objeto.")
        return function["name"], arguments

    @staticmethod
    def _build_prompt(question: str, context: dict) -> str:
        return (
            "Usa únicamente el contexto y las tools autorizadas. No inventes datos. "
            "Si falta información, dilo claramente.\n\n"
            f"CONTEXTO PSI TWIN:\n{json.dumps(context, ensure_ascii=False, default=str, indent=2)}"
            f"\n\nPREGUNTA:\n{question}"
        )

    @staticmethod
    def _visualization(data: dict) -> dict:
        return {"type": "none"} if not data else {"type": "table", "data": data}

    @staticmethod
    def _warnings(sources: set[str]) -> list[str]:
        warnings = []
        if "INVENTORY_RISK" in sources:
            warnings.append("El riesgo proviene de InventoryRiskService.")
        if "LIGHTGBM" in sources:
            warnings.append("La predicción proviene del pipeline LightGBM.")
        return warnings
