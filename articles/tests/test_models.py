from django.core.exceptions import ValidationError
from django.db import IntegrityError

from articles.models import Article, Like, Review

from .base import ArticleHubTestCase


class SlugTests(ArticleHubTestCase):
    def test_slug_is_generated_from_title(self):
        article = self.make_article(title='Mi Artículo sobre Django')
        self.assertEqual(article.slug, 'mi-articulo-sobre-django')

    def test_slug_collisions_get_numeric_suffix(self):
        slugs = [self.make_article(title='Mi artículo').slug for _ in range(3)]
        self.assertEqual(slugs, ['mi-articulo', 'mi-articulo-2', 'mi-articulo-3'])

    def test_slug_is_stable_when_title_changes(self):
        article = self.make_article(title='Título original')
        article.title = 'Título nuevo'
        article.save()
        self.assertEqual(article.slug, 'titulo-original')

    def test_reserved_slug_is_avoided(self):
        self.assertEqual(self.make_article(title='New').slug, 'new-2')

    def test_category_slug_is_generated(self):
        self.assertEqual(self.category.slug, 'programacion')


class WorkflowModelTests(ArticleHubTestCase):
    def test_new_article_starts_as_draft(self):
        article = Article.objects.create(author=self.author, title='Sin estado')
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_submission_requires_category_and_content(self):
        article = self.make_article(content='corto', category=None)
        with self.assertRaises(ValidationError) as ctx:
            article.submit_for_review()
        self.assertEqual(len(ctx.exception.messages), 2)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_review_only_allowed_when_pending(self):
        article = self.make_article()
        with self.assertRaises(ValidationError):
            article.review(self.editor, Review.Decision.APPROVED)
        self.assertFalse(Review.objects.exists())

    def test_like_is_unique_per_user_and_article(self):
        article = self.make_article(Article.Status.PUBLISHED)
        Like.objects.create(user=self.other, article=article)
        with self.assertRaises(IntegrityError):
            Like.objects.create(user=self.other, article=article)
