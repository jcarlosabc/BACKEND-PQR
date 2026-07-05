# PQR — Backend

API REST para el sistema de gestión de Peticiones, Quejas y Reclamos (PQR) de
Fundación Sersocial IPS. Permite a ciudadanos registrar solicitudes y
consultarlas por radicado, y a los agentes internos listarlas, gestionarlas y
dejar trazabilidad de seguimiento.

Este repositorio contiene únicamente el backend. El frontend vive en un
repositorio aparte, y la documentación de análisis (historias de usuario,
DER, diagrama de flujo, decisiones de arquitectura) y el `docker-compose`
que levanta el sistema completo viven en el repositorio `pqr-sistema`.

## Stack

- Python 3.11, Django 5, Django REST Framework
- PostgreSQL (SQLite como alternativa para desarrollo local sin Docker)
- Autenticación JWT (`djangorestframework-simplejwt`) con roles agente / supervisor / admin
- `django-filter` para filtros de listado, `django-cors-headers` para el frontend
- pytest + pytest-django para pruebas, black + ruff + isort para estilo

## Requisitos

- Python 3.11 o superior
- PostgreSQL 14+ (opcional en desarrollo; sin él, el proyecto usa SQLite automáticamente)

## Cómo ejecutar el proyecto

Hay dos formas de levantarlo. Cualquiera de las dos deja la API en
`http://localhost:8000/api/` en menos de 10 minutos.

### Opción A — Sin Docker (entorno virtual de Python)

Usa SQLite automáticamente (no necesitas instalar PostgreSQL).

```bash
git clone https://github.com/jcarlosabc/BACKEND-PQR.git backend-pqr
cd backend-pqr

python -m venv .venv
.venv/Scripts/activate          # En Linux/Mac: source .venv/bin/activate

pip install -r requirements-dev.txt

cp .env.example .env             # valores por defecto ya funcionan con SQLite

python manage.py migrate
python manage.py seed_demo       # crea usuarios y PQR de ejemplo (credenciales más abajo)
python manage.py runserver
```

La API queda en `http://localhost:8000/api/` y el admin de Django en
`http://localhost:8000/admin/`.

### Opción B — Con Docker (Postgres real, un solo comando)

Requiere Docker y Docker Compose instalados. No necesitas crear un
entorno virtual ni instalar Python localmente.

```bash
git clone https://github.com/jcarlosabc/BACKEND-PQR.git backend-pqr
cd backend-pqr

cp .env.example .env

docker compose up -d --build
docker compose exec backend python manage.py seed_demo
```

Esto levanta dos contenedores: `db` (PostgreSQL 16) y `backend` (Django
con Gunicorn). El primer arranque corre migraciones y `collectstatic`
automáticamente (ver `entrypoint.sh`). La API queda igual en
`http://localhost:8000/api/` y el admin en `http://localhost:8000/admin/`.

Para ver los logs: `docker compose logs -f backend`
Para parar todo: `docker compose down` (agrega `-v` si también quieres borrar los datos de Postgres)

Este `docker-compose.yml` levanta **solo** el backend + su base de datos,
para poder desarrollar y probar la API de forma aislada. Para levantar
backend + frontend juntos con un solo comando, usa el
`docker-compose.yml` del repositorio `pqr-sistema` (ver su README).

## Variables de entorno

Ver `.env.example` para la lista completa. Las más relevantes:

| Variable | Efecto |
|---|---|
| `POSTGRES_HOST` | Si está vacía, se usa SQLite (`db.sqlite3`). Si tiene un valor, se conecta a PostgreSQL con `POSTGRES_DB/USER/PASSWORD/PORT`. |
| `DEBUG` | `True` en desarrollo. En producción debe ser `False`. |
| `CORS_ALLOWED_ORIGINS` | Origen(es) del frontend autorizados a llamar la API. |
| `EMAIL_BACKEND` | `console` (por defecto, imprime los correos en la terminal) o `smtp` para enviarlos de verdad. |

## Usuarios y datos de ejemplo

`python manage.py seed_demo` crea, si no existen, tres usuarios internos y
cuatro PQR de ejemplo en distintos estados:

| Rol | Email | Contraseña |
|---|---|---|
| Admin | `admin@sersocial.demo` | `Admin1234!` |
| Supervisor | `supervisor@sersocial.demo` | `Supervisor1234!` |
| Agente | `agente@sersocial.demo` | `Agente1234!` |

Son credenciales de demostración, no usarlas en un despliegue real.

## Autenticación

```
POST /api/auth/login     { "email": "...", "password": "..." } -> { access, refresh }
POST /api/auth/refresh   { "refresh": "..." } -> { access }
GET  /api/auth/me        (requiere header Authorization: Bearer <access>)
```

Registrar una PQR (`POST /api/pqr`) y consultarla por radicado
(`GET /api/pqr/buscar`) son las dos únicas rutas públicas: reflejan que
cualquier ciudadano puede radicar y hacer seguimiento sin crear una cuenta.
El resto de la API (listar, ver detalle, cambiar estado, agregar
seguimiento, estadísticas) requiere un token de un usuario interno.

## Endpoints principales

| Método | Ruta | Acceso | Descripción |
|---|---|---|---|
| `POST` | `/api/pqr` | Público | Crear una PQR (incluye datos del solicitante) |
| `GET` | `/api/pqr` | Agente* | Listar con filtros `tipo`, `estado`, `prioridad`, `categoria` |
| `GET` | `/api/pqr/{id}` | Agente* | Detalle completo, con solicitante y seguimientos |
| `PATCH` | `/api/pqr/{id}/estado` | Agente* | Cambiar estado y/o prioridad (valida transición) |
| `GET`/`POST` | `/api/pqr/{id}/seguimiento` | Agente* | Ver o agregar entradas de seguimiento |
| `PATCH` | `/api/pqr/{id}/asignar` | Supervisor/Admin | Reasignar la PQR a otro usuario interno |
| `GET` | `/api/pqr/buscar?radicado=` | Público | Consulta liviana por radicado |
| `POST` | `/api/pqr/calificar` | Público | Calificar (1-5) una PQR ya cerrada, una sola vez |
| `GET` | `/api/pqr/exportar` | Agente* | Exporta a CSV el listado con los filtros activos |
| `GET` | `/api/estadisticas` | Agente* | Conteos por estado, tipo, prioridad, vencidas, calificación promedio |
| `GET` | `/api/usuarios` | Supervisor/Admin | Listar usuarios internos (para el combo de reasignación) |
| `POST` | `/api/usuarios` | Admin | Crear un usuario interno nuevo |
| `PATCH` | `/api/usuarios/{id}` | Admin | Cambiar rol y/o activar-desactivar un usuario |

\* Ver la sección "Roles y control de acceso" — un agente no ve/gestiona lo mismo que un supervisor.

La transición de estado sigue el flujo obligatorio
`recibida → en_gestion → resuelta → cerrada`; saltos o retrocesos se
rechazan con `400`.

`GET /api/pqr` acepta además `q` (busca en título y descripción) y
`vencidas=true` (solo PQR abiertas cuyo plazo de respuesta ya pasó).

## Roles y control de acceso

El rol de cada usuario interno (`agente` / `supervisor` / `admin`) no es
solo un dato: controla qué puede ver y hacer cada quien.

- **Agente**: en `GET /api/pqr` y en las acciones sobre una PQR
  (`estado`, `seguimiento`) solo ve/gestiona PQR **sin asignar** o
  **asignadas a sí mismo**. Si un agente actúa sobre una PQR sin asignar
  (cambia estado o agrega un seguimiento), esa PQR queda automáticamente
  asignada a él — no hay un paso manual de "tomar caso". Si intenta
  actuar sobre una PQR asignada a otro agente, la API responde `404`
  (no la ve, ni siquiera para saber que existe).
- **Supervisor / Admin**: ven y gestionan cualquier PQR sin ese filtro,
  y ambos pueden reasignar (`PATCH /api/pqr/{id}/asignar`) o listar los
  usuarios internos (`GET /api/usuarios`).
- **Admin**, además, es el único que puede **crear, activar/desactivar y
  cambiar el rol** de un usuario interno (`POST`/`PATCH /api/usuarios`) —
  un supervisor solo puede ver la lista, no gestionarla. Admin también
  conserva acceso al panel de Django (`/admin/`).

Ver `pqr-sistema/decisiones_arquitectura.md` para el detalle de por qué
se modeló así.

## SLA de respuesta

Cada PQR calcula su fecha límite de respuesta al crearse
(`PQR_DIAS_SLA` en `.env`, 15 días calendario por defecto). El campo
`sla_estado` (expuesto en listado, detalle y búsqueda pública) vale
`a_tiempo`, `por_vencer` (3 días o menos), `vencida`, o —una vez resuelta
o cerrada— `cumplido`/`incumplido` según si se respondió antes del plazo.
`GET /api/estadisticas` agrega los conteos `vencidas` y `por_vencer`.

## Tests y cobertura

```bash
pytest
pytest --cov=accounts --cov=pqr --cov-report=term-missing
```

42 pruebas cubren creación pública de PQR, reutilización de ciudadano
existente, filtros de listado, control de acceso por rol (agente vs.
supervisor/admin), auto-asignación, reasignación, gestión de usuarios
(admin), SLA de respuesta, búsqueda de texto, exportación CSV,
calificación, transiciones de estado válidas e inválidas, seguimiento y
autenticación. Cobertura actual: 94%.

## Calidad de código

```bash
black accounts pqr config conftest.py manage.py
isort accounts pqr config conftest.py manage.py
ruff check accounts pqr config conftest.py manage.py
```

## Despliegue en producción (VPS, sin Docker)

Si prefieres no usar Docker en el servidor:

```bash
pip install -r requirements.txt

export DEBUG=False
export SECRET_KEY=<valor aleatorio real>
export ALLOWED_HOSTS=tu-dominio.com
export POSTGRES_HOST=<host de tu base de datos>
export POSTGRES_DB=... POSTGRES_USER=... POSTGRES_PASSWORD=...

python manage.py migrate
python manage.py collectstatic --noinput
gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3
```

`gunicorn` debe correr detrás de un proxy como nginx que sirva
`staticfiles/` y termine TLS. La guía paso a paso completa (con Docker,
recomendada) está en `despliegue.md` del repositorio `pqr-sistema`.

## Solución de problemas comunes

**`sqlite3.OperationalError: no such table: usuarios`** (u otra tabla)
al correr `seed_demo` o `runserver`: te faltó `python manage.py migrate`
antes. El orden siempre es `migrate` → `seed_demo` → `runserver`.

**`no configuration file provided: not found`** al correr
`docker compose up`: estás parado en la carpeta equivocada. Este
repositorio (`backend-pqr`) tiene su propio `docker-compose.yml` (levanta
solo backend + Postgres) — créelo desde **dentro de `backend-pqr`**. El
`docker-compose.yml` del sistema completo (backend + frontend) está en
la carpeta **`pqr-sistema`** (con "a"), no en `pqr-system` (con "y", la
carpeta que las contiene a las tres) ni en `frontend-pqr`. Confirma en
qué carpeta estás con `pwd` (Linux/Mac) o `cd` sin argumentos (Windows)
antes de correr el comando.

**El frontend muestra "No se pudo conectar con el servidor"**: confirma
primero que el backend responde por su cuenta: `curl http://localhost:8000/api/estadisticas`
(debe dar `401`, no un error de conexión). Si el backend responde bien,
el problema está en el frontend o en el proxy de nginx — revisa
`frontend-pqr/README.md`.

## Estructura del proyecto

```
backend-pqr/
  config/           configuración de Django (settings, urls, wsgi/asgi)
  accounts/         usuario interno (auth, roles), login JWT
  pqr/              Ciudadano, PQR, Seguimiento, API, filtros, notificaciones
    management/commands/seed_demo.py
    tests/
  requirements.txt
  requirements-dev.txt
  pyproject.toml    configuración de black, isort y ruff
```

## Uso de IA

Este proyecto usó Claude Code (Anthropic) como asistente de desarrollo
durante la construcción del backend. Alcance: generación de código a partir
de decisiones de modelado, arquitectura y validación tomadas y revisadas
punto a punto durante el desarrollo (modelos, endpoints, permisos,
notificaciones, pruebas). Ajusta este párrafo si quieres precisar mejor el
alcance real antes de entregar.
