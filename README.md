# PsiTwin Inventory

Sistema de inventario inteligente para equipos de frío: backend (FastAPI + MongoDB + MQTT) y frontend (React + Vite).

## Estructura

```
.
├── backend/     API FastAPI, modelos ML, sensores MQTT, tests
├── frontend/    App React + TypeScript (Vite)
├── docs/        Especificaciones, contratos API y documentación de Saiki/sensores
└── README.md
```

## Arranque rápido

Requisitos: Python 3.11+, Node 20+, Docker, MongoDB.

```bash
# 0) Entorno Python (una sola vez, en la raíz del repo)
python3 -m venv .venv
.venv/bin/pip install -r backend/requirements.txt

# 1) Servicios
docker start psitwin-mongo
docker start psitwin-mosquitto      # sensores (opcional para trabajar solo con inventario)

# 2) Backend  → http://localhost:8000
cd backend
cp .env.example .env
../.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload

# 3) Frontend → http://localhost:5173 (Vite reenvía /api al backend)
cd frontend
cp .env.example .env
npm install
npm run dev
```

Pruebas del backend:

```bash
cd backend
../.venv/bin/python -m unittest discover -s tests
```

## Documentación

| Documento | Contenido |
|---|---|
| [`backend/README.md`](backend/README.md) | Roles, autenticación, flujo de reposición, credenciales demo, sensores |
| [`docs/ROLES.md`](docs/ROLES.md) | Contrato de roles backend ↔ frontend |
| [`docs/SENSORES.md`](docs/SENSORES.md) | Contrato de sensores (MQTT, alertas, WebSocket) |
| [`docs/ESPECIFICACION_COMPLETA_PSITWIN.md`](docs/ESPECIFICACION_COMPLETA_PSITWIN.md) | Especificación funcional completa |
| [`docs/`](docs/) | Resto de especificaciones, diccionarios y documentación de Saiki |

## Credenciales demo

| Rol | Correo | Contraseña |
|---|---|---|
| EMPRESA | demo@psitwin.com | demo123 |
| OPERARIO | operario1@psitwin.com | oper123 |
| PROVEEDOR | proveedor1@psitwin.com | prov123 |

Más detalles en [`backend/README.md`](backend/README.md).
