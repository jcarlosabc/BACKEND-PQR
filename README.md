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
| `GET` | `/api/pqr` | Agente | Listar con filtros `tipo`, `estado`, `prioridad`, `categoria` |
| `GET` | `/api/pqr/{id}` | Agente | Detalle completo, con solicitante y seguimientos |
| `PATCH` | `/api/pqr/{id}/estado` | Agente | Cambiar estado y/o prioridad (valida transición) |
| `GET`/`POST` | `/api/pqr/{id}/seguimiento` | Agente | Ver o agregar entradas de seguimiento |
| `GET` | `/api/pqr/buscar?radicado=` | Público | Consulta liviana por radicado |
| `GET` | `/api/estadisticas` | Agente | Conteos por estado, tipo y prioridad |

La transición de estado sigue el flujo obligatorio
`recibida → en_gestion → resuelta → cerrada`; saltos o retrocesos se
rechazan con `400`.

## Tests y cobertura

```bash
pytest
pytest --cov=accounts --cov=pqr --cov-report=term-missing
```

17 pruebas cubren creación pública de PQR, reutilización de ciudadano
existente, filtros de listado, control de acceso, transiciones de estado
válidas e inválidas, seguimiento y autenticación. Cobertura actual: 96%.

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
