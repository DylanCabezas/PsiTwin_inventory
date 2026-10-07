import asyncio

import pytest

from app.dto.saiki_dto import SaikiAskRequest
from app.services.saiki_service import SaikiService


def test_request_accepts_message_and_legacy_question():
    assert SaikiAskRequest(message="hola").message == "hola"
    assert SaikiAskRequest(question="hola").message == "hola"


def test_request_requires_message():
    with pytest.raises(ValueError):
        SaikiAskRequest()


def test_agent_loop_executes_read_only_tool_and_tracks_source(monkeypatch):
    service = SaikiService()
    responses = iter(
        [
            {
                "message": {
                    "role": "assistant",
                    "tool_calls": [
                        {
                            "function": {
                                "name": "get_inventory",
                                "arguments": {"id_inventario": "inv-1"},
                            }
                        }
                    ],
                }
            },
            {"message": {"role": "assistant", "content": "Stock disponible."}},
        ]
    )
    monkeypatch.setattr(service, "_call_ollama_chat", lambda messages: next(responses))

    async def execute(name, arguments):
        assert name == "get_inventory"
        assert arguments == {"id_inventario": "inv-1"}
        return {"stock_actual": 4}, "INVENTARIO"

    monkeypatch.setattr(service.tools, "execute", execute)
    result = asyncio.run(service.ask(SaikiAskRequest(message="¿Hay stock?")))

    assert result["answer"] == "Stock disponible."
    assert result["sources"] == ["INVENTARIO"]
    assert result["data"]["get_inventory"]["stock_actual"] == 4


def test_invalid_tool_is_rejected():
    service = SaikiService()
    with pytest.raises(ValueError, match="Tool no autorizada"):
        asyncio.run(service.tools.execute("delete_inventory", {}))


def test_agent_loop_has_a_limit(monkeypatch):
    service = SaikiService()
    monkeypatch.setattr(
        service,
        "_call_ollama_chat",
        lambda messages: {
            "message": {
                "role": "assistant",
                "tool_calls": [
                    {
                        "function": {
                            "name": "get_inventory",
                            "arguments": {"id_inventario": "inv-1"},
                        }
                    }
                ],
            }
        },
    )

    async def execute(name, arguments):
        return {}, "INVENTARIO"

    monkeypatch.setattr(service.tools, "execute", execute)
    with pytest.raises(RuntimeError, match="límite"):
        asyncio.run(
            service._agent_loop(
                [{"role": "user", "content": "repite"}]
            )
        )
