from io import StringIO

from django.core.management import call_command
from django.test import Client
from django.urls import reverse

from articles.models import Article, Comment, Like

from .base import ArticleHubTestCase


class CommentTests(ArticleHubTestCase):
    def setUp(self):
        self.article = self.make_article(Article.Status.PUBLISHED)
        self.url = reverse('articles:comment_create', args=[self.article.slug])

    def test_comment_on_published_article(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url, {'content': 'Muy interesante'})
        comment = Comment.objects.get()
        self.assertRedirects(
            response, f'{self.article.get_absolute_url()}#comment-{comment.pk}', fetch_redirect_response=False
        )
        self.assertEqual((comment.author, comment.content), (self.other, 'Muy interesante'))

    def test_empty_comment_is_rejected(self):
        self.client.force_login(self.other)
        self.client.post(self.url, {'content': '   '})
        self.assertFalse(Comment.objects.exists())

    def test_cannot_comment_unpublished_article(self):
        draft = self.make_article(title='Privado')
        self.client.force_login(self.other)
        response = self.client.post(
            reverse('articles:comment_create', args=[draft.slug]), {'content': 'Hola'}
        )
        self.assertEqual(response.status_code, 404)
        self.assertFalse(Comment.objects.exists())

    def test_anonymous_cannot_comment(self):
        response = self.client.post(self.url, {'content': 'Hola'})
        self.assertEqual(response.status_code, 302)
        self.assertFalse(Comment.objects.exists())

    def test_delete_own_comment(self):
        comment = Comment.objects.create(article=self.article, author=self.other, content='Mío')
        self.client.force_login(self.other)
        self.client.post(reverse('articles:comment_delete', args=[comment.pk]))
        self.assertFalse(Comment.objects.exists())

    def test_cannot_delete_someone_elses_comment(self):
        comment = Comment.objects.create(article=self.article, author=self.other, content='Ajeno')
        self.client.force_login(self.author)
        response = self.client.post(reverse('articles:comment_delete', args=[comment.pk]))
        self.assertEqual(response.status_code, 403)
        self.assertTrue(Comment.objects.filter(pk=comment.pk).exists())


class LikeTests(ArticleHubTestCase):
    def setUp(self):
        self.article = self.make_article(Article.Status.PUBLISHED)
        self.url = reverse('articles:like_toggle', args=[self.article.slug])
        self.ajax = {'HTTP_X_REQUESTED_WITH': 'XMLHttpRequest'}

    def test_like_and_unlike_via_ajax(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url, **self.ajax)
        self.assertEqual(response.json(), {'liked': True, 'count': 1})
        response = self.client.post(self.url, **self.ajax)
        self.assertEqual(response.json(), {'liked': False, 'count': 0})
        self.assertFalse(Like.objects.exists())

    def test_like_without_js_redirects_to_article(self):
        self.client.force_login(self.other)
        response = self.client.post(self.url)
        self.assertRedirects(response, self.article.get_absolute_url())
        self.assertEqual(Like.objects.count(), 1)

    def test_likes_from_different_users_are_counted_without_duplicates(self):
        for user in (self.other, self.editor):
            self.client.force_login(user)
            self.client.post(self.url, **self.ajax)
        self.assertEqual(self.article.likes.count(), 2)
        self.assertEqual(Like.objects.filter(user=self.other, article=self.article).count(), 1)

    def test_like_endpoint_requires_login_and_post(self):
        response = self.client.post(self.url, **self.ajax)
        self.assertEqual(response.status_code, 302)
        self.assertIn(reverse('accounts:login'), response.url)
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(self.url).status_code, 405)
        self.assertFalse(Like.objects.exists())

    def test_cannot_like_unpublished_article(self):
        draft = self.make_article(title='Borrador')
        self.client.force_login(self.other)
        response = self.client.post(reverse('articles:like_toggle', args=[draft.slug]))
        self.assertEqual(response.status_code, 404)

    def test_like_requires_csrf_token(self):
        client = Client(enforce_csrf_checks=True)
        client.force_login(self.other)
        self.assertEqual(client.post(self.url, **self.ajax).status_code, 403)
        self.assertFalse(Like.objects.exists())


class SeedDemoTests(ArticleHubTestCase):
    def test_seed_demo_is_repeatable(self):
        call_command('seed_demo', stdout=StringIO())
        counts = (Article.objects.count(), Comment.objects.count(), Like.objects.count())
        call_command('seed_demo', stdout=StringIO())
        self.assertEqual(counts, (Article.objects.count(), Comment.objects.count(), Like.objects.count()))
        statuses = set(Article.objects.values_list('status', flat=True))
        self.assertEqual(statuses, set(Article.Status.values))
