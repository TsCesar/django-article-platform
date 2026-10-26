from datetime import timedelta

from django.contrib.auth.models import Group, User
from django.core.management.base import BaseCommand
from django.db import transaction
from django.utils import timezone

from articles.apps import EDITORS_GROUP
from articles.models import Article, Category, Comment, Like, Review, Tag

DEMO_PASSWORD = 'demo-pass-2026'
DEMO_USERS = {
    'lucia_demo': {'email': 'lucia@example.com'},
    'marcos_demo': {'email': 'marcos@example.com'},
    'editor_demo': {'email': 'editor@example.com', 'editor': True},
}

CATEGORIES = {
    'Programación': 'Lenguajes, frameworks y buenas prácticas de desarrollo.',
    'Ciencia de datos': 'Análisis, visualización y aprendizaje automático.',
    'Diseño': 'Interfaces, experiencia de usuario y accesibilidad.',
    'Ciberseguridad': 'Protección de aplicaciones, datos y personas.',
    'Cultura digital': 'Tecnología, sociedad y forma de trabajar.',
}

TAGS = ['python', 'django', 'javascript', 'css', 'ia', 'seguridad', 'accesibilidad',
        'productividad', 'open-source', 'bases-de-datos']


def paragraphs(*items):
    return '\n\n'.join(items)


# (author, title, category, tags, status, days_ago, excerpt, content)
ARTICLES = [
    ('lucia_demo', 'Por qué Django sigue siendo una gran elección en 2026', 'Programación',
     ['python', 'django'], 'PUBLISHED', 2,
     'Baterías incluidas, un ORM maduro y una comunidad estable: repasamos qué hace a Django tan productivo.',
     paragraphs(
         'Cada pocos meses aparece un framework que promete cambiarlo todo. Sin embargo, cuando hay que entregar una aplicación web completa, con autenticación, administración y una base de datos relacional, Django sigue siendo una apuesta difícil de superar.',
         'Su mayor virtud es la coherencia: el ORM, el sistema de plantillas, los formularios y el admin están pensados para trabajar juntos. Eso reduce las decisiones triviales y deja más tiempo para el problema real del proyecto.',
         'Además, la seguridad viene de serie: protección CSRF, escape automático en plantillas y un sistema de permisos que se integra con grupos. No es magia, pero sí un punto de partida sólido.',
     )),
    ('marcos_demo', 'Accesibilidad web: cinco errores que todavía cometemos', 'Diseño',
     ['accesibilidad', 'css'], 'PUBLISHED', 4,
     'Contraste insuficiente, foco invisible y formularios sin etiquetas siguen siendo demasiado habituales.',
     paragraphs(
         'La accesibilidad no es una capa que se añade al final. Es una forma de diseñar que beneficia a todas las personas, incluidas las que navegan con teclado, lectores de pantalla o en condiciones de luz difíciles.',
         'El primer error clásico es eliminar el contorno de foco por estética. Si lo quitas, sustitúyelo por un estilo visible. El segundo, usar colores con poco contraste en textos secundarios.',
         'Los otros tres se repiten en formularios: campos sin label, mensajes de error que solo se indican con color y botones que en realidad son enlaces o divs sin semántica.',
     )),
    ('lucia_demo', 'Introducción práctica a pandas para analistas', 'Ciencia de datos',
     ['python', 'bases-de-datos'], 'PUBLISHED', 7,
     'Del CSV al informe en pocas líneas: las operaciones de pandas que más se usan en el día a día.',
     paragraphs(
         'pandas se ha convertido en la navaja suiza del análisis de datos en Python. Con un DataFrame puedes cargar, limpiar, agrupar y exportar información sin salir del mismo entorno.',
         'Las operaciones que más utilizarás son read_csv, groupby, merge y pivot_table. Dominar estas cuatro cubre buena parte de los informes habituales.',
         'Un consejo: antes de transformar nada, revisa los tipos de cada columna y los valores nulos. La mayoría de resultados extraños nacen de un dato mal interpretado.',
     )),
    ('marcos_demo', 'Contraseñas, gestores y doble factor sin dramas', 'Ciberseguridad',
     ['seguridad', 'productividad'], 'PUBLISHED', 10,
     'Una guía tranquila para mejorar la seguridad de tus cuentas sin complicarte la vida.',
     paragraphs(
         'La mayoría de incidentes personales no empiezan con un ataque sofisticado, sino con una contraseña reutilizada que aparece en una filtración ajena.',
         'Un gestor de contraseñas resuelve el problema de raíz: una contraseña distinta y larga para cada servicio, sin necesidad de memorizarlas.',
         'El segundo paso es activar el doble factor en el correo y en los servicios críticos. Si puedes elegir, prefiere una app de autenticación o una llave física frente a los SMS.',
     )),
    ('lucia_demo', 'Trabajar en abierto: lo que aprendí contribuyendo a open source', 'Cultura digital',
     ['open-source', 'productividad'], 'PUBLISHED', 15,
     'Contribuir a proyectos abiertos enseña a leer código ajeno, comunicar mejor y aceptar revisiones.',
     paragraphs(
         'Mi primera contribución a un proyecto de código abierto fue corregir una errata en la documentación. Parecía poca cosa, pero me obligó a entender cómo se organizaba el repositorio y cómo se revisaban los cambios.',
         'Con el tiempo descubrí que lo más valioso no era el código, sino la conversación: explicar una propuesta, responder a dudas y ajustar el trabajo tras una revisión.',
         'Si estás empezando, busca issues etiquetados como good first issue y lee las guías de contribución antes de abrir tu primer pull request.',
     )),
    ('marcos_demo', 'CSS moderno: container queries y :has() en la práctica', 'Diseño',
     ['css', 'javascript'], 'PUBLISHED', 21,
     'Dos herramientas que permiten componentes más autónomos y menos JavaScript decorativo.',
     paragraphs(
         'Durante años, adaptar un componente a su espacio disponible exigía media queries globales o JavaScript. Las container queries permiten que el propio componente reaccione al tamaño de su contenedor.',
         'El selector :has() completa la jugada: por fin podemos estilar un elemento padre según su contenido, por ejemplo una tarjeta que contiene una imagen o una etiqueta marcada.',
         'Ambas funcionalidades tienen buen soporte en navegadores actuales y permiten eliminar bastante código de apoyo.',
     )),
    ('lucia_demo', 'Modelos de lenguaje en el aula: oportunidades y límites', 'Cultura digital',
     ['ia'], 'PENDING_REVIEW', 1,
     'Cómo integrar asistentes de IA en la enseñanza sin renunciar al pensamiento crítico.',
     paragraphs(
         'Los asistentes basados en modelos de lenguaje ya forman parte del día a día de muchos estudiantes. Prohibirlos sin más resulta poco realista; ignorarlos, también.',
         'Una alternativa es usarlos de forma explícita: pedir al alumnado que contraste respuestas, detecte errores y explique por qué una solución es correcta.',
         'El reto está en diseñar evaluaciones que valoren el proceso y no solo el resultado final.',
     )),
    ('marcos_demo', 'Diez trucos rápidos de JavaScript', 'Programación',
     ['javascript'], 'REJECTED', 3,
     'Una lista de atajos de JavaScript para escribir menos código.',
     paragraphs(
         'JavaScript tiene muchos atajos que permiten escribir menos código. Algunos son útiles y otros dificultan la lectura si se abusa de ellos.',
         'En este artículo recopilo diez trucos rápidos: encadenamiento opcional, operador de fusión nula, desestructuración y algunos más.',
     )),
    ('marcos_demo', 'Notas sobre bases de datos para principiantes', 'Programación',
     ['bases-de-datos'], 'DRAFT', 0,
     '',
     'Borrador: ideas sueltas sobre índices, claves foráneas y normalización.'),
]

COMMENTS = [
    ('Por qué Django sigue siendo una gran elección en 2026', 'marcos_demo',
     'Totalmente de acuerdo con lo del admin: ahorra semanas en proyectos internos.'),
    ('Por qué Django sigue siendo una gran elección en 2026', 'editor_demo',
     'Buen resumen. Quizá en otro artículo podrías profundizar en el sistema de permisos.'),
    ('Accesibilidad web: cinco errores que todavía cometemos', 'lucia_demo',
     'Lo del foco invisible lo veo constantemente. Gracias por la lista.'),
    ('Introducción práctica a pandas para analistas', 'marcos_demo',
     'Añadiría value_counts a la lista de imprescindibles.'),
    ('Contraseñas, gestores y doble factor sin dramas', 'lucia_demo',
     'Me has convencido para activar el doble factor en el correo.'),
]

LIKES = [
    ('Por qué Django sigue siendo una gran elección en 2026', ['marcos_demo', 'editor_demo']),
    ('Accesibilidad web: cinco errores que todavía cometemos', ['lucia_demo', 'editor_demo']),
    ('Introducción práctica a pandas para analistas', ['marcos_demo']),
    ('Contraseñas, gestores y doble factor sin dramas', ['lucia_demo', 'editor_demo']),
    ('CSS moderno: container queries y :has() en la práctica', ['lucia_demo']),
]

REJECTION_COMMENT = (
    'El tema es interesante, pero el artículo es todavía muy breve y no explica cuándo '
    'conviene usar cada truco. Añade ejemplos de código comentados y una conclusión.'
)


class Command(BaseCommand):
    help = 'Crea datos de demostración: usuarios, categorías, etiquetas, artículos, comentarios y likes.'

    def add_arguments(self, parser):
        parser.add_argument(
            '--reset',
            action='store_true',
            help='Elimina antes los usuarios demo (y sus artículos, comentarios y likes).',
        )

    @transaction.atomic
    def handle(self, *args, **options):
        if options['reset']:
            deleted, _ = User.objects.filter(username__in=DEMO_USERS).delete()
            self.stdout.write(f'Datos demo anteriores eliminados ({deleted} objetos).')

        users = self.create_users()
        categories = {
            name: Category.objects.get_or_create(name=name, defaults={'description': desc})[0]
            for name, desc in CATEGORIES.items()
        }
        tags = {name: Tag.objects.get_or_create(name=name)[0] for name in TAGS}

        created = 0
        now = timezone.now()
        for author, title, category, tag_names, status, days_ago, excerpt, content in ARTICLES:
            if Article.objects.filter(author=users[author], title=title).exists():
                continue
            article = Article.objects.create(
                author=users[author],
                title=title,
                excerpt=excerpt,
                content=content,
                category=categories[category],
            )
            article.tags.set([tags[name] for name in tag_names])
            self.apply_status(article, status, users['editor_demo'])
            moment = now - timedelta(days=days_ago, hours=3)
            Article.objects.filter(pk=article.pk).update(
                created_at=moment - timedelta(days=1),
                submitted_at=moment if status != 'DRAFT' else None,
                published_at=moment if status == 'PUBLISHED' else None,
            )
            created += 1

        for title, username, content in COMMENTS:
            article = Article.objects.get(title=title)
            Comment.objects.get_or_create(article=article, author=users[username], content=content)
        for title, usernames in LIKES:
            article = Article.objects.get(title=title)
            for username in usernames:
                Like.objects.get_or_create(article=article, user=users[username])

        self.stdout.write(self.style.SUCCESS(
            f'Datos demo listos: {created} artículos nuevos, '
            f'{Article.objects.published().count()} publicados en total.'
        ))
        self.stdout.write(f'Usuarios demo: {", ".join(DEMO_USERS)} (contraseña: {DEMO_PASSWORD})')

    def create_users(self):
        editors = Group.objects.get(name=EDITORS_GROUP)
        users = {}
        for username, data in DEMO_USERS.items():
            user, created = User.objects.get_or_create(username=username, defaults={'email': data['email']})
            if created:
                user.set_password(DEMO_PASSWORD)
                user.save()
            if data.get('editor'):
                user.groups.add(editors)
            users[username] = user
        return users

    def apply_status(self, article, status, editor):
        """Drive the article through the real editorial workflow."""
        if status == 'DRAFT':
            return
        article.submit_for_review()
        if status == 'PUBLISHED':
            article.review(editor, Review.Decision.APPROVED, '¡Publicado! Buen trabajo.')
        elif status == 'REJECTED':
            article.review(editor, Review.Decision.REJECTED, REJECTION_COMMENT)
