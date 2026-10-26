from datetime import timedelta

from django.contrib.auth.models import User
from django.urls import reverse
from django.utils import timezone

from articles.models import Article, Review

from .base import ArticleHubTestCase


class SubmitForReviewTests(ArticleHubTestCase):
    def submit(self, article, user=None):
        self.client.force_login(user or self.author)
        return self.client.post(reverse('articles:article_submit', args=[article.slug]))

    def test_submit_draft(self):
        article = self.make_article()
        response = self.submit(article)
        self.assertRedirects(response, article.get_private_url())
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.PENDING_REVIEW)
        self.assertIsNotNone(article.submitted_at)

    def test_resubmit_rejected(self):
        article = self.make_article(Article.Status.REJECTED)
        self.submit(article)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.PENDING_REVIEW)

    def test_submit_requires_post(self):
        article = self.make_article()
        self.client.force_login(self.author)
        response = self.client.get(reverse('articles:article_submit', args=[article.slug]))
        self.assertEqual(response.status_code, 405)

    def test_other_user_cannot_submit(self):
        article = self.make_article()
        self.assertEqual(self.submit(article, user=self.other).status_code, 403)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_incomplete_article_is_not_submitted(self):
        article = self.make_article(category=None)
        self.submit(article)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.DRAFT)

    def test_published_article_cannot_be_resubmitted(self):
        article = self.make_article(Article.Status.PUBLISHED)
        self.submit(article)
        article.refresh_from_db()
        self.assertEqual(article.status, Article.Status.PUBLISHED)


class EditorPanelTests(ArticleHubTestCase):
    def test_editor_panel_requires_login(self):
        response = self.client.get(reverse('articles:editor_dashboard'))
        self.assertEqual(response.status_code, 302)

    def test_regular_user_gets_403(self):
        self.client.force_login(self.other)
        response = self.client.get(reverse('articles:editor_dashboard'))
        self.assertEqual(response.status_code, 403)
        self.assertTemplateUsed(response, '403.html')

    def test_editor_and_staff_can_access(self):
        staff = User.objects.create_user('staff', password='x-123456', is_staff=True)
        for user in (self.editor, staff):
            self.client.force_login(user)
            self.assertEqual(self.client.get(reverse('articles:editor_dashboard')).status_code, 200)

    def test_panel_lists_pending_oldest_first(self):
        now = timezone.now()
        newer = self.make_article(Article.Status.PENDING_REVIEW, title='Reciente', submitted_at=now)
        older = self.make_article(
            Article.Status.PENDING_REVIEW,
            title='Antiguo',
            submitted_at=now - timedelta(days=2),
        )
        self.make_article(title='Borrador invisible')
        self.client.force_login(self.editor)
        response = self.client.get(reverse('articles:editor_dashboard'))
        self.assertEqual(list(response.context['pending']), [older, newer])


class ReviewTests(ArticleHubTestCase):
    def setUp(self):
        self.article = self.make_article(Article.Status.PENDING_REVIEW)
        self.url = reverse('articles:editor_review', args=[self.article.slug])

    def review(self, user, decision, comment=''):
        self.client.force_login(user)
        return self.client.post(self.url, {'decision': decision, 'comment': comment})

    def test_approve_publishes_and_records_review(self):
        response = self.review(self.editor, 'APPROVED')
        self.assertRedirects(response, reverse('articles:editor_dashboard'))
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PUBLISHED)
        self.assertIsNotNone(self.article.published_at)
        review = Review.objects.get(article=self.article)
        self.assertEqual((review.decision, review.reviewer), ('APPROVED', self.editor))

    def test_reject_records_review_with_reason(self):
        self.review(self.editor, 'REJECTED', 'Falta profundidad.')
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.REJECTED)
        self.assertIsNone(self.article.published_at)
        review = Review.objects.get(article=self.article)
        self.assertEqual((review.decision, review.comment), ('REJECTED', 'Falta profundidad.'))

    def test_reject_requires_comment(self):
        response = self.review(self.editor, 'REJECTED', '   ')
        self.assertEqual(response.status_code, 200)
        self.assertFormError(response.context['form'], 'comment', 'Explica el motivo del rechazo.')
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PENDING_REVIEW)
        self.assertFalse(Review.objects.exists())

    def test_regular_user_cannot_review(self):
        response = self.review(self.other, 'APPROVED')
        self.assertEqual(response.status_code, 403)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PENDING_REVIEW)

    def test_author_cannot_approve_own_article_even_as_editor(self):
        self.author.groups.add(*self.editor.groups.all())
        response = self.review(self.author, 'APPROVED')
        self.assertEqual(response.status_code, 403)
        self.article.refresh_from_db()
        self.assertEqual(self.article.status, Article.Status.PENDING_REVIEW)

    def test_cannot_review_article_that_is_not_pending(self):
        draft = self.make_article(title='Borrador')
        self.client.force_login(self.editor)
        self.client.post(
            reverse('articles:editor_review', args=[draft.slug]), {'decision': 'APPROVED'}
        )
        draft.refresh_from_db()
        self.assertEqual(draft.status, Article.Status.DRAFT)

    def test_author_sees_rejection_reason_but_others_do_not(self):
        self.article.review(self.editor, Review.Decision.REJECTED, 'Motivo confidencial')
        private_url = self.article.get_private_url()

        self.client.force_login(self.author)
        self.assertContains(self.client.get(private_url), 'Motivo confidencial')

        self.client.force_login(self.other)
        self.assertEqual(self.client.get(private_url).status_code, 403)
