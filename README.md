# pintapp

## Descripción

# Frontend

# Backend

API HTTP del probador virtual de ropa. El backend recibe la foto del cliente, consulta el catálogo
y las existencias, y genera la imagen del cliente con las prendas puestas.

**Fase 1 (este prototipo):** el inventario y la IA generadora de imágenes están **simulados**, detrás de
interfaces intercambiables. La base de datos relacional todavía no se usa para datos de negocio.

## Tecnologías

| Pieza | Para qué |
|---|---|
| Python 3.14 | Lenguaje (fijado en `.python-version`; el repo del frontend también usa 3.14) |
| FastAPI + Uvicorn | API HTTP asíncrona, validación automática y documentación en `/docs` |
| Pydantic / pydantic-settings | Validación de datos y configuración por variables de entorno |
| Pillow | Validación y procesamiento seguro de la foto (formato, tamaño, orientación, metadatos) |
| SQLAlchemy 2 (asyncio) | Conexión independiente del motor: PostgreSQL, MariaDB/MySQL, etc. |
| uv | Gestión de dependencias y del entorno virtual |

## Instalación y ejecución

Todos los comandos se ejecutan **desde la raíz del repositorio**:

```bash
# 1. Entorno virtual + dependencias
python -m venv backend/.venv
source backend/.venv/bin/activate        # Windows: backend\.venv\Scripts\activate
pip install -r backend/requirements.txt

# 2. (opcional) configuración local
cp backend/.env.example backend/.env     # Windows: copy backend\.env.example backend\.env

# 3. Levantar el servidor http://127.0.0.1:8000/
python -m backend.main 
```

Con el servidor en marcha, la documentación interactiva de todos los endpoints queda en
`http://127.0.0.1:8000/docs` (solo en `PINTAPP_ENVIRONMENT=development`).

Para desarrollo con reinicio automático: `PINTAPP_RELOAD=true`.

## Estructura

```
backend/
├── main.py              # Arranca Uvicorn
├── app.py               # Fábrica de la app FastAPI + middlewares de seguridad
├── container.py         # Ensamblado: aquí se elige qué implementación usa cada puerto
├── config.py            # Settings (variables PINTAPP_*)
├── controller/          # Capa HTTP: routers, contratos JSON (schemas), errores, dependencias
├── service/             # Lógica de negocio: sesión, foto, catálogo, probador, generación
├── model/               # Entidades y errores del dominio (Python puro, sin HTTP)
├── port/                # Interfaces: InventoryRepository, ImageGenerator, SessionStore, JobStore
├── adapter/             # Implementaciones: inventario simulado, IA simulada, memoria, BD
├── data/catalog_seed.json   # Catálogo de prueba (12 prendas, con tallas agotadas a propósito)
├── .env.example
└── pyproject.toml / uv.lock / .python-version
```

La regla de dependencias es: `controller → service → port ← adapter`. Los servicios nunca importan
FastAPI ni un adaptador concreto; por eso cambiar inventario, IA o base de datos no toca la lógica.

## Cómo funciona
### Flujo del cliente 

Toda petición del cliente, salvo crear la sesión, lleva el encabezado `X-Session-Token`.

| Paso del caso de uso | Endpoint |
|---|---|
| Toca la pantalla: crea sesión temporal y entrega el aviso de términos | `POST /api/v1/sessions` |
| Acepta el aviso (si rechaza, la sesión se cierra sin guardar nada) | `PUT /api/v1/sessions/me/consent` `{"accepted": true}` |
| Toma su foto (cuerpo crudo JPEG/PNG/WebP) | `PUT /api/v1/sessions/me/photo` |
| Consulta el catálogo, filtra por categoría, talla o color | `GET /api/v1/catalog/garments?category=&size=&color=&in_stock=` |
| Selecciona una prenda (agregar al probador) | `POST /api/v1/sessions/me/fitting` `{"garment_id": "jean", "sku": "PAN-JEA-32"}` |
| Quita una prenda | `DELETE /api/v1/sessions/me/fitting/{garment_id}` |
| Presiona "finalizar" | `POST /api/v1/sessions/me/generations` |
| Muestra el progreso | `GET /api/v1/sessions/me/generations/{job_id}` (consultar cada 1–2 s) |
| Muestra el resultado | `GET /api/v1/sessions/me/generations/{job_id}/image` |
| Generación fallida o tiempo agotado: reintentar | `POST /api/v1/sessions/me/generations/{job_id}/retry` |
| Termina la sesión (borra todo) | `DELETE /api/v1/sessions/me` |

También existen `GET /api/v1/terms`, `GET /api/v1/sessions/me` (estado, para resincronizar el frontend),
`GET /api/v1/catalog/categories`, `GET /api/v1/catalog/garments/{id}`, `GET .../fitting` y `GET /health`.

### Sesión

- El token es aleatorio (`secrets.token_urlsafe(32)`). Vive **solo en memoria**.
- Expira por inactividad (10 min) y por vida máxima (30 min); una tarea en segundo plano limpia las vencidas.
- Cerrar o expirar una sesión borra la foto, las prendas y las imágenes generadas, y cancela la
  generación en curso.
- La foto no se acepta sin consentimiento previo.

### Foto

La foto es entrada no confiable. Se valida el **formato real** (no el que declara el cliente), se limitan
bytes y píxeles **antes** de decodificar, se corrige la orientación, se eliminan metadatos (EXIF/GPS) y se
recomprime a JPEG. Si no es válida responde `422 invalid_photo` con `details.reason`
(`empty`, `unsupported_format`, `too_many_pixels`, `too_small`, `animated`, `unreadable`) y el cliente puede
volver a tomarla sin perder la sesión.

### Probador y zonas del cuerpo

Cada categoría se traduce a una zona (`service/body_zones.py`): `head`, `upper_inner` (camisas, camisetas),
`upper_outer` (chaquetas), `lower` (pantalones) y `feet` (zapatos). **Una prenda por zona**: si la zona está
ocupada responde `409 zone_occupied`; repite con `"replace": true` para cambiarla. Solo se pueden agregar
prendas con existencias (`409 garment_out_of_stock`). Las categorías desconocidas responden
`422 unsupported_category`.

### Generación (cola)

`finalizar` valida (consentimiento, foto, al menos una prenda, un solo trabajo activo por sesión) y encola.
Workers asíncronos toman los trabajos, llaman al generador con un **tiempo máximo** y terminan en
`completed`, `failed` o `timed_out`. Hay un límite de reintentos por sesión y una cola con tamaño máximo
(`503 queue_full` si está llena). El progreso se informa **por estados** y posición en cola, no como
porcentaje: los generadores de imágenes no lo entregan.

### Errores

Todos los errores tienen el mismo formato, con un `code` estable para el frontend:

```json
{"error": {"code": "zone_occupied", "message": "Ya hay una prenda en esa zona del cuerpo.", "details": {"zone": "upper_inner"}}}
```
## Configuración

Variables de entorno con prefijo `PINTAPP_` o archivo `backend/.env` (ver `.env.example`). Las principales:

| Variable | Por defecto | Descripción |
|---|---|---|
| `ENVIRONMENT` | `development` | En `production` se ocultan `/docs` y `/openapi.json` |
| `HOST` / `PORT` | `127.0.0.1` / `8000` | Dirección del servidor |
| `DATABASE_URL` | — | URL de la BD (ver más abajo) |
| `SIM_MIN_SECONDS` / `SIM_MAX_SECONDS` | `3` / `6` | Duración de la IA simulada |
| `SIM_FAILURE_RATE` | `0` | Probabilidad de fallo simulado (para probar reintentos en el frontend) |
| `GENERATION_TIMEOUT_SECONDS` | `60` | Tiempo máximo por generación |
| `GENERATION_WORKERS` / `GENERATION_QUEUE_MAX` | `1` / `20` | Concurrencia y tamaño de la cola |
| `SESSION_IDLE_TTL_SECONDS` | `600` | Inactividad máxima de la sesión |
| `PHOTO_MAX_BYTES` | 8 MB | Tamaño máximo de la foto |

El resto (límites de píxeles, calidad JPEG, reintentos, CORS, etc.) está en `config.py`.

## Partes simuladas y cómo reemplazarlas

### Base de datos / inventario real

PintApp **no administra inventario**: lo consulta a través de `port/inventory.py` (solo lectura). La fuente
real (la BD del e-commerce, o su API) se conecta así:

1. Instalar el driver del motor: `uv sync --project backend --extra postgres` o `--extra mariadb`.
2. Definir la URL en `.env`:
   `PINTAPP_DATABASE_URL=postgresql+psycopg://usuario:clave@host:5432/base` o
   `mariadb+asyncmy://usuario:clave@host:3306/base`.
   `GET /health` verifica la conexión.
3. Crear `adapter/sql_inventory.py` con una clase que implemente `InventoryRepository` usando el motor
   (`container.db_engine`) y SQLAlchemy Core (sin SQL propio de un motor) para mantener la compatibilidad.
   Debe devolver `Garment`/`Variant` del dominio y lanzar `InventoryUnavailableError` si la BD no responde.
4. Registrar el proveedor nuevo en `config.py` (`inventory_provider`) y en `_build_inventory` de `container.py`.

Un adaptador a la API de un e-commerce se hace igual, implementando el mismo puerto.

> Solo se probó la conexión con SQLite en desarrollo y la creación del motor con las URLs de PostgreSQL
> y MariaDB. Hay que validar el adaptador definitivo contra el motor real cuando exista la BD.

### IA generadora de imágenes

Implementar `ImageGenerator` (`port/image_generator.py`) en un adaptador nuevo y registrarlo en
`_build_generator`. Debe lanzar `GenerationFailedError` si falla; el tiempo máximo y los reintentos los
controla el servicio. **Al usar un proveedor externo la foto sale del servidor:** hay que actualizar el texto
de términos (`terms_text`), que hoy afirma que la foto solo se procesa localmente. Ese texto es provisional
y debe ser reemplazado por el texto legal definitivo.

## Seguridad

- Token de sesión aleatorio, expiración por inactividad y por vida máxima, cupo máximo de sesiones.
- Foto: formato real, límites de bytes y píxeles antes de decodificar, sin EXIF, recompresión.
- Cuerpos de petición limitados (por `Content-Length` y contando bytes al vuelo).
- Cada sesión solo accede a sus propios trabajos de generación.
- Respuestas con `Cache-Control: no-store` y `X-Content-Type-Options: nosniff`; sin encabezado `Server`.
- Los errores internos no revelan detalles; las contraseñas de la URL de BD nunca se escriben en logs.
- CORS desactivado por defecto (la app de escritorio no lo necesita).
- Escucha solo en `127.0.0.1` por defecto. En producción, usar un proxy inverso (TLS, límites de
  tasa y de tamaño) delante del servidor.
