from django.contrib.auth.models import Group, User
from django.test import TestCase
from django.utils import timezone

from articles.apps import EDITORS_GROUP
from articles.models import Article, Category, Tag

LONG_CONTENT = 'Contenido de prueba suficientemente largo para poder enviarse a revisión. ' * 3


class ArticleHubTestCase(TestCase):
    """Shared fixtures: two authors, one editor, a category and a tag."""

    @classmethod
    def setUpTestData(cls):
        cls.author = User.objects.create_user('autora', 'autora@example.com', 'pass-123456')
        cls.other = User.objects.create_user('otro', 'otro@example.com', 'pass-123456')
        cls.editor = User.objects.create_user('editora', 'editora@example.com', 'pass-123456')
        cls.editor.groups.add(Group.objects.get(name=EDITORS_GROUP))
        cls.category = Category.objects.create(name='Programación')
        cls.tag = Tag.objects.create(name='python')

    def make_article(self, status=Article.Status.DRAFT, author=None, **kwargs):
        kwargs.setdefault('title', 'Artículo de prueba')
        kwargs.setdefault('content', LONG_CONTENT)
        kwargs.setdefault('category', self.category)
        if status == Article.Status.PUBLISHED:
            kwargs.setdefault('published_at', timezone.now())
        return Article.objects.create(author=author or self.author, status=status, **kwargs)
