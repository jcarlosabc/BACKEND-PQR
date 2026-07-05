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

## Puesta en marcha en desarrollo

```bash
cd backend
python -m venv .venv
.venv/Scripts/activate          # En Linux/Mac: source .venv/bin/activate
pip install -r requirements-dev.txt

cp .env.example .env             # ajusta valores si es necesario; por defecto usa SQLite

python manage.py migrate
python manage.py seed_demo       # crea usuarios y PQR de ejemplo (ver credenciales abajo)
python manage.py runserver
```

La API queda disponible en `http://localhost:8000/api/`. El panel de
administración de Django, en `http://localhost:8000/admin/` (usa las
credenciales del usuario `admin` creadas por `seed_demo`, ver más abajo).

Todo el proceso, desde clonar hasta tener la API respondiendo, toma entre 5 y
10 minutos.

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

## Producción (sin Docker)

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

En producción, `gunicorn` debe correr detrás de un proxy como nginx que
sirva `staticfiles/` y termine TLS. La guía paso a paso para VPS
(Gunicorn + Nginx) se documenta por separado en `docs/despliegue.md` del
repositorio `pqr-sistema`.

## Docker

Este repositorio incluirá su propio `docker-compose.yml` (backend +
PostgreSQL) para levantar solo la API de forma aislada. El
`docker-compose.yml` que levanta el sistema completo (backend + frontend +
base de datos) vive en el repositorio `pqr-sistema`. Ambos se agregan en la
etapa de dockerización del proyecto.

## Estructura del proyecto

```
backend/
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
