from django.apps import AppConfig
from django.db.models.signals import post_migrate


EDITORS_GROUP = 'Editors'


def create_editors_group(sender, **kwargs):
    """Ensure the Editors group exists and holds the review permission."""
    from django.contrib.auth.models import Group, Permission
    from django.contrib.contenttypes.models import ContentType

    from .models import Article

    content_type = ContentType.objects.get_for_model(Article)
    permission, _ = Permission.objects.get_or_create(
        codename='review_article',
        content_type=content_type,
        defaults={'name': 'Puede revisar artículos (aprobar o rechazar)'},
    )
    group, _ = Group.objects.get_or_create(name=EDITORS_GROUP)
    group.permissions.add(permission)


class ArticlesConfig(AppConfig):
    name = 'articles'
    verbose_name = 'Artículos'

    def ready(self):
        post_migrate.connect(create_editors_group, sender=self)
