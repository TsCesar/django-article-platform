# ArticleHub

Plataforma colaborativa de publicación de artículos, al estilo de una revista digital o un blog editorial. Cualquier usuario registrado puede escribir artículos, pero solo se publican después de que un editor los apruebe.

Proyecto académico construido con Django, plantillas del servidor, CSS propio y JavaScript vanilla. Sin frameworks de frontend ni dependencias externas.

## Demo pública

Demo pública: [pendiente de URL]

## Características

- **Registro, login y logout** (el logout funciona por POST). El email no puede repetirse y, tras registrarse, el usuario inicia sesión automáticamente.
- **Artículos** con título, slug automático y único (`mi-articulo`, `mi-articulo-2`...), extracto, contenido, categoría y etiquetas.
- **Flujo editorial real**: borrador → pendiente de revisión → publicado o rechazado. El estado solo lo cambia el backend.
- **Revisiones**: cada aprobación o rechazo crea un registro `Review`. Rechazar exige un motivo, que el autor puede consultar en la ficha privada de su artículo.
- **Dashboard del autor** con contadores por estado y acciones según el estado de cada artículo.
- **Panel editorial** (`/editor/`) con la cola de artículos pendientes, de más antiguo a más reciente.
- **Comentarios** en artículos publicados. Cada usuario puede borrar solo los suyos.
- **Me gusta** con `fetch` y sin recargar la página. Sin JavaScript, el mismo formulario funciona como un POST normal.
- **Búsqueda** por título, contenido, extracto, autor, categoría y etiqueta.
- **Filtros** por autor, categoría y etiqueta en la portada, además de páginas dedicadas para categorías, etiquetas y autores.
- **Paginación** de 10 artículos en portada, búsqueda, categoría, etiqueta y autor.
- **Django Admin** configurado para todos los modelos.
- **Datos demo** con `python manage.py seed_demo`.
- **Diseño oscuro y responsive** con CSS propio, badges de estado y páginas 403 y 404 personalizadas.

## Tecnologías

- Python 3.14
- Django 6.1
- SQLite (desarrollo) y PostgreSQL (producción)
- Gunicorn y WhiteNoise (producción en Render)
- Django Templates, HTML y CSS propio
- JavaScript vanilla (`main.js`, `likes.js`)

## Instalación

```bash
python -m venv venv
```

Windows:

```bash
.\venv\Scripts\activate
```

Linux / macOS:

```bash
source venv/bin/activate
```

Después:

```bash
pip install -r requirements.txt
python manage.py migrate
python manage.py createsuperuser
python manage.py runserver
```

Abre <http://127.0.0.1:8000/>.

## Estructura

```
config/                 Configuración del proyecto (settings, urls)
accounts/               Registro, login/logout y página "Mi cuenta"
articles/               Modelos, vistas, formularios, permisos, admin y tests
  management/commands/  seed_demo
  tests/                Tests del flujo editorial, vistas públicas e interacciones
templates/              base.html, includes/, accounts/, articles/, 403.html, 404.html
static/css/style.css    Hoja de estilos
static/js/              main.js (menú, mensajes, confirmaciones) y likes.js
```

## Modelos

| Modelo     | Descripción |
|------------|-------------|
| `User`     | Usuario estándar de Django |
| `Category` | `name` y `slug` únicos, `description` opcional |
| `Tag`      | `name` y `slug` únicos; relación ManyToMany con `Article` |
| `Article`  | Autor, título, slug, extracto, contenido, categoría, etiquetas, estado y fechas (`created_at`, `updated_at`, `submitted_at`, `published_at`) |
| `Review`   | Artículo, revisor, decisión (`APPROVED` / `REJECTED`), comentario y fecha |
| `Comment`  | Artículo, autor, contenido y fechas |
| `Like`     | Usuario, artículo y fecha, con `UniqueConstraint(user, article)` |

## Flujo editorial

```
DRAFT ──► PENDING_REVIEW ──► PUBLISHED
                │
                └──► REJECTED ──(editar)──► PENDING_REVIEW
```

| Estado           | El autor puede |
|------------------|----------------|
| `DRAFT`          | ver, editar, eliminar y enviar a revisión |
| `PENDING_REVIEW` | solo verlo y esperar (no puede editarlo ni eliminarlo) |
| `REJECTED`       | leer el motivo, editarlo, eliminarlo y reenviarlo |
| `PUBLISHED`      | verlo; es público y no se puede editar directamente |

- Un artículo nuevo siempre empieza como `DRAFT`. `ArticleForm` no incluye `status`, `author` ni `published_at`.
- Para enviar un artículo a revisión necesita título, una categoría y al menos 100 caracteres de contenido.
- Al aprobarlo: `status = PUBLISHED` y `published_at = timezone.now()`. Al rechazarlo: `status = REJECTED`. En los dos casos se crea un `Review`.
- Un editor no puede revisar sus propios artículos.
- Los artículos sin publicar devuelven 404 en la URL pública. Su autor y los editores los ven en la ficha privada `/articles/<slug>/preview/`.

## Roles y permisos

- **Autor**: cualquier usuario autenticado.
- **Editor**: miembro del grupo `Editors`, que tiene el permiso `articles.review_article`. El personal staff y los superusuarios también pueden revisar.
- **Admin/Staff**: acceso a Django Admin.

El grupo `Editors` y su permiso se crean automáticamente al ejecutar `migrate`.

Todos los permisos se comprueban en el backend, con `login_required`, `require_POST`, `PermissionDenied` y `get_object_or_404`. Un usuario normal recibe un **403** si intenta entrar en `/editor/`, y el formulario de revisión no acepta peticiones de quien no sea editor.

### Cómo crear un editor

Opción 1, desde el admin:

1. Inicia sesión en `/admin/` con un superusuario.
2. Ve a **Usuarios** y abre el usuario.
3. En **Grupos**, añade `Editors` y guarda.

Opción 2, desde la shell:

```bash
python manage.py shell -c "from django.contrib.auth.models import Group, User; User.objects.get(username='NOMBRE').groups.add(Group.objects.get(name='Editors'))"
```

## Datos demo

```bash
python manage.py seed_demo          # crea los datos demo (puede ejecutarse varias veces)
python manage.py seed_demo --reset  # borra los usuarios demo y su contenido, y los vuelve a crear
```

Genera 5 categorías, 10 etiquetas, 3 usuarios y 9 artículos (6 publicados, 1 pendiente, 1 rechazado con su motivo y 1 borrador), además de comentarios y likes. Los artículos pasan por el flujo editorial real.

| Usuario       | Contraseña       | Rol    |
|---------------|------------------|--------|
| `lucia_demo`  | `demo-pass-2026` | Autora |
| `marcos_demo` | `demo-pass-2026` | Autor  |
| `editor_demo` | `demo-pass-2026` | Editor (grupo `Editors`) |

Son credenciales solo para demostración y no deben usarse fuera de desarrollo.

## URLs principales

| URL | Descripción |
|-----|-------------|
| `/` | Portada (`?author=`, `?category=`, `?tag=`) |
| `/search/?q=` | Búsqueda |
| `/categories/`, `/categories/<slug>/` | Categorías |
| `/tags/<slug>/` | Etiqueta |
| `/authors/<username>/` | Página de autor |
| `/articles/<slug>/` | Artículo publicado |
| `/articles/<slug>/preview/` | Ficha privada (autor y editores) |
| `/articles/new/`, `/articles/<slug>/edit/`, `/articles/<slug>/delete/` | CRUD |
| `/articles/<slug>/submit/` | Enviar a revisión (POST) |
| `/articles/<slug>/like/` | Me gusta / quitar Me gusta (POST) |
| `/dashboard/` | Panel del autor |
| `/editor/`, `/editor/articles/<slug>/` | Panel editorial y revisión |
| `/accounts/register/`, `/accounts/login/`, `/accounts/logout/`, `/accounts/profile/` | Cuentas |
| `/admin/` | Django Admin |

## Tests

```bash
python manage.py test
```

Cubren autenticación, CRUD y propiedad de los artículos, slugs y colisiones, el flujo editorial completo, la visibilidad pública, comentarios, likes (incluido CSRF), búsqueda, filtros, paginación, permisos y la idempotencia de `seed_demo`.

## Despliegue

ArticleHub está preparado para desplegarse en [Render](https://render.com) mediante un Blueprint (`render.yaml`):

- **Local**: SQLite (`db.sqlite3`), `DEBUG = True` y una `SECRET_KEY` de desarrollo. No hace falta ninguna variable de entorno.
- **Producción**: PostgreSQL de Render a través de `DATABASE_URL` (con `dj-database-url`), `DEBUG = False` y `SECRET_KEY` desde el entorno.
- **Gunicorn** sirve la aplicación WSGI (`config.wsgi:application`). Lee `PORT` y `WEB_CONCURRENCY` del entorno.
- **WhiteNoise** sirve los estáticos de `static/`, recopilados en `staticfiles/` con nombres con hash y compresión (`CompressedManifestStaticFilesStorage`).
- **`build.sh`** instala dependencias, ejecuta `collectstatic` y `migrate`, y crea el superusuario si se han definido sus variables. Si ya existe, no hace nada.
- **`render.yaml`** define la base de datos `articlehub-db` y el Web Service `articlehub`, ambos en el plan Free.
- **`.python-version`** fija Python 3.14 (Render usa el último parche de esa versión).

| Comando | Valor |
|---------|-------|
| Build   | `./build.sh` |
| Start   | `python -m gunicorn config.wsgi:application` |

### Variables de entorno

| Variable | Origen | Uso |
|----------|--------|-----|
| `DATABASE_URL` | `articlehub-db` | Conexión a PostgreSQL. Si no existe, se usa SQLite. |
| `SECRET_KEY` | Generada por Render | Obligatoria cuando `RENDER=true`. |
| `DEBUG` | `False` | Por defecto `True` en local y `False` en Render. |
| `WEB_CONCURRENCY` | `2` | Workers de Gunicorn (adecuado para los 512 MB del plan Free). |
| `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL`, `DJANGO_SUPERUSER_PASSWORD` | Las pide Render al crear el Blueprint | Superusuario inicial (opcional). |
| `RENDER`, `RENDER_EXTERNAL_HOSTNAME` | Las define Render automáticamente | Activan HTTPS (`SECURE_PROXY_SSL_HEADER`, cookies seguras, redirección) y añaden el dominio a `ALLOWED_HOSTS` y `CSRF_TRUSTED_ORIGINS`. |

Ningún secreto está en el repositorio.

### Crear el Blueprint en Render

1. En el dashboard de Render: **New** > **Blueprint**.
2. Conecta el repositorio `TsCesar/django-article-platform` (rama `main`).
3. Render lee `render.yaml` y muestra la base de datos y el Web Service.
4. Introduce `DJANGO_SUPERUSER_USERNAME`, `DJANGO_SUPERUSER_EMAIL` y `DJANGO_SUPERUSER_PASSWORD`.
5. Pulsa **Deploy Blueprint** y espera a que termine el build.
6. Abre `https://<servicio>.onrender.com/` y entra en `/admin/` con el superusuario.

### Editores en producción

El grupo `Editors` y su permiso `articles.review_article` se crean automáticamente con `migrate` (señal `post_migrate`), así que existen tras el primer build. Para convertir un usuario en editor, entra en `/admin/` con el superusuario, abre **Usuarios**, elige el usuario, añade `Editors` en **Grupos** y guarda. El plan Free de Render no ofrece shell, por eso se hace desde el admin.

### Datos demo en producción

`seed_demo` **no** se ejecuta en el build, para que cada deploy no altere los datos de la demo. Si se quiere cargar la demo una vez, hay dos opciones:

- En un plan de pago con shell: `python manage.py seed_demo`.
- Desde tu equipo, apuntando a la base de datos de Render con su *External Database URL*: `DATABASE_URL="<External Database URL>" python manage.py seed_demo`.

Los usuarios demo usan contraseñas públicas (ver *Datos demo*). En una demo pública, conviene cambiarlas desde el admin o no cargarlos.

### Limitaciones del plan Free

- El Web Service se suspende tras 15 minutos sin tráfico; la primera visita después tarda en responder.
- La base de datos Free expira a los 30 días de crearse (con 14 días de margen para pasar a un plan de pago).
- Sin shell ni SSH en el Web Service.

## Capturas

> Pendiente de añadir capturas de la portada, el detalle de un artículo, el dashboard y el panel editorial.

## Limitaciones conocidas

- El contenido es texto plano con saltos de línea. No admite Markdown ni editor enriquecido.
- Los artículos publicados no se pueden editar ni retirar desde la interfaz. Se gestionan desde el admin.
- Las etiquetas y categorías se crean desde el admin.
- La búsqueda usa `icontains` (sin búsqueda de texto completo ni ranking).
- La app no envía emails. `MAILERS` usa el backend de consola, por lo que `check --deploy` muestra `mail.E001`; no afecta al despliegue.
- HSTS (`SECURE_HSTS_SECONDS`) no está activado.
