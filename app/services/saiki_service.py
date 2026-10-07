import json
from urllib import error, request

from fastapi import HTTPException, status

from app.config.settings import get_settings
from app.dto.saiki_dto import SaikiAskRequest
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

    async def ask(self, data: SaikiAskRequest) -> dict:
        context = dict(data.context)
        if data.id_inventario:
            result, _ = await self.tools.execute(
                "get_inventory", {"id_inventario": data.id_inventario}
            )
            context["inventario"] = result
        if data.id_producto:
            result, _ = await self.tools.execute(
                "get_product", {"id_producto": data.id_producto}
            )
            context["producto"] = result

        messages = [
            {"role": "system", "content": self.get_system_prompt()},
            *data.history,
            {
                "role": "user",
                "content": self._build_prompt(data.message or "", context),
            },
        ]
        try:
            answer, tool_data, sources = await self._agent_loop(messages)
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

    async def _agent_loop(self, messages: list[dict]) -> tuple[str, dict, set[str]]:
        tool_data: dict[str, object] = {}
        sources: set[str] = set()
        for _ in range(self.max_tool_iterations):
            response = self._call_ollama_chat(messages)
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
                result, source = await self.tools.execute(name, arguments)
                sources.add(source)
                tool_data[name] = result
                messages.append(
                    {
                        "role": "tool",
                        "tool_name": name,
                        "content": json.dumps(
                            result, ensure_ascii=False, default=str
                        ),
                    }
                )
        raise RuntimeError("Se alcanzó el límite de consultas de Saiki.")

    def _call_ollama_chat(self, messages: list[dict], timeout: int = 60) -> dict:
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

    def _call_ollama(self, prompt: str, timeout: int = 60) -> str:
        response = self._call_ollama_chat(
            [
                {"role": "system", "content": self.get_system_prompt()},
                {"role": "user", "content": prompt},
            ],
            timeout=timeout,
        )
        message = response.get("message", {})
        answer = message.get("content") if isinstance(message, dict) else None
        if not isinstance(answer, str) or not answer.strip():
            raise RuntimeError("Ollama no devolvió una respuesta útil.")
        return answer.strip()

    def _parse_tool_call(self, tool_call: object) -> tuple[str, dict]:
        if not isinstance(tool_call, dict):
            raise ValueError("Tool call inválida.")
        function = tool_call.get("function")
        if not isinstance(function, dict) or not isinstance(
            function.get("name"), str
        ):
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
