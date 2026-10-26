from django.urls import reverse

from articles.models import Article

from .base import LONG_CONTENT, ArticleHubTestCase


class ArticleCrudTests(ArticleHubTestCase):
    def setUp(self):
        self.client.force_login(self.author)

    def form_data(self, **overrides):
        data = {
            'title': 'Nuevo artículo',
            'excerpt': 'Resumen',
            'content': LONG_CONTENT,
            'category': self.category.pk,
            'tags': [self.tag.pk],
        }
        data.update(overrides)
        return data

    def test_create_article_as_draft_ignoring_manipulated_fields(self):
        data = self.form_data(status='PUBLISHED', author=self.other.pk, published_at='2020-01-01')
        response = self.client.post(reverse('articles:article_create'), data)
        article = Article.objects.get(title='Nuevo artículo')
        self.assertRedirects(response, article.get_private_url())
        self.assertEqual(article.status, Article.Status.DRAFT)
        self.assertEqual(article.author, self.author)
        self.assertIsNone(article.published_at)
        self.assertEqual(list(article.tags.all()), [self.tag])

    def test_create_requires_login(self):
        self.client.logout()
        response = self.client.get(reverse('articles:article_create'))
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)

    def test_edit_own_draft(self):
        article = self.make_article()
        url = reverse('articles:article_update', args=[article.slug])
        response = self.client.post(url, self.form_data(title='Título editado'))
        self.assertRedirects(response, article.get_private_url())
        article.refresh_from_db()
        self.assertEqual(article.title, 'Título editado')

    def test_edit_cannot_change_status(self):
        article = self.make_article(Article.Status.REJECTED)
        url = reverse('articles:article_update', args=[article.slug])
        self.client.post(url, self.form_data(status='PUBLISHED'))
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.REJECTED)

    def test_delete_own_draft(self):
        article = self.make_article()
        response = self.client.post(reverse('articles:article_delete', args=[article.slug]))
        self.assertRedirects(response, reverse('articles:dashboard'))
        self.assertFalse(Article.objects.filter(pk=article.pk).exists())

    def test_other_user_cannot_edit(self):
        article = self.make_article(author=self.other)
        url = reverse('articles:article_update', args=[article.slug])
        self.assertEqual(self.client.get(url).status_code, 403)
        self.assertEqual(self.client.post(url, self.form_data(title='Hackeado')).status_code, 403)
        article.refresh_from_db()
        self.assertEqual(article.title, 'Artículo de prueba')

    def test_other_user_cannot_delete(self):
        article = self.make_article(author=self.other)
        response = self.client.post(reverse('articles:article_delete', args=[article.slug]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Article.objects.filter(pk=article.pk).exists())

    def test_pending_article_is_not_editable_nor_deletable(self):
        article = self.make_article(Article.Status.PENDING_REVIEW)
        self.client.post(
            reverse('articles:article_update', args=[article.slug]), self.form_data(title='Cambio')
        )
        self.client.post(reverse('articles:article_delete', args=[article.slug]))
        article.refresh_from_db()
        self.assertEqual(article.title, 'Artículo de prueba')
        self.assertEqual(article.status, Article.Status.PENDING_REVIEW)

    def test_published_article_is_not_editable(self):
        article = self.make_article(Article.Status.PUBLISHED)
        response = self.client.get(reverse('articles:article_update', args=[article.slug]))
        self.assertRedirects(response, article.get_private_url())


class DashboardTests(ArticleHubTestCase):
    def test_dashboard_requires_login(self):
        response = self.client.get(reverse('articles:dashboard'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('articles:dashboard')}")

    def test_dashboard_lists_only_own_articles_with_counters(self):
        self.make_article(title='Mi borrador')
        self.make_article(Article.Status.REJECTED, title='Mi rechazado')
        self.make_article(author=self.other, title='Ajeno')
        self.client.force_login(self.author)
        response = self.client.get(reverse('articles:dashboard'))
        self.assertContains(response, 'Mi borrador')
        self.assertContains(response, 'Mi rechazado')
        self.assertNotContains(response, 'Ajeno')
        counts = response.context['counts']
        self.assertEqual((counts['total'], counts['drafts'], counts['rejected']), (2, 1, 1))
