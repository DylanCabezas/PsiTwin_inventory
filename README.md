# PsiTwin_inventory

## Ejecutar

```bash
docker start psitwin-mongo            # MongoDB en localhost:27017
.venv/bin/pip install -r requirements.txt
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
.venv/bin/python -m unittest discover -s tests
```

Variables en `.env` (ver `.env.example`). `CORS_ORIGINS` = orígenes del frontend separados por comas
(default `http://localhost:5173`). El correo (SMTP) es opcional: si no está configurado, ninguna acción se bloquea.

## Roles y autenticación

Todo `/api/v1/*` exige `Authorization: Bearer <token>` salvo `POST /auth/login` y `POST /auth/register`.
`POST /auth/login {correo, password}` sirve para los tres roles y devuelve
`{access_token, token_type, rol, empresa, operario, proveedor, debe_cambiar_password}`.
Contrato completo con el frontend: `FRontPsy/docs/ROLES.md`.

| Rol | Cómo nace | Qué hace |
|---|---|---|
| **EMPRESA** | `POST /auth/register` | CRUD de almacenes y zonas; crea/borra racks; crea cuentas de operario y proveedor; valida, devuelve o cancela solicitudes de reposición; lee inventario, movimientos (historial con autor), recepciones, alertas, recomendaciones, riesgo y forecast. |
| **OPERARIO** | Lo crea la empresa (`POST /operarios`, con almacén, correo y contraseña temporal) | Solo su almacén: edita racks (estado, temperatura), asigna rack de referencia a productos, crea inventarios y edita límites, registra SALIDAS (venta, vencimiento), crea solicitudes de reposición, registra recepciones y resuelve evaluaciones, valida recomendaciones. |
| **PROVEEDOR** | Lo crea la empresa (`POST /proveedores` con `password_temporal`, o `POST /proveedores/{id}/reset-password`) | Crea y edita sus productos; ve las órdenes ENVIADAS a él y registra el despacho. |

Operario y proveedor deben cambiar la contraseña temporal en su primer ingreso (`PATCH /auth/me/password`); hasta entonces
todo salvo `GET /auth/me` responde `403 {"detail": "Debe cambiar su contraseña", "code": "PASSWORD_CHANGE_REQUIRED"}`.

Flujo de reposición: operario crea la solicitud (`PENDIENTE`) → empresa `validar` (`ENVIADA`) o `devolver` con comentario
(`OBSERVADA` → el operario corrige y `reenviar`) → proveedor registra `despacho` → operario registra la recepción
(`PARCIAL` / `RECIBIDA`).

Racks: `capacidad` es la carga máxima en kg; un rack por nivel de la zona; temperatura solo en zonas refrigeradas.
Un producto solo entra a un rack DISPONIBLE, con kg libres y (si es refrigerado) con un rango de temperatura dentro del suyo.

### Credenciales demo

| Rol | Correo | Contraseña |
|---|---|---|
| EMPRESA (Empresa Demo) | demo@psitwin.com | demo123 |
| OPERARIO (Carlos Ramos, Almacén Central Lima) | operario1@psitwin.com | oper123 |
| OPERARIO (Lucía Torres, Almacén Central Lima) | operario2@psitwin.com | oper234 |
| PROVEEDOR (Distribuidora Andina SAC) | proveedor1@psitwin.com | prov123 |
| PROVEEDOR (Lácteos del Sur SAC) | proveedor2@psitwin.com | prov234 |
