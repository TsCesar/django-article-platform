from django.urls import reverse

from articles.models import Article, Category, Tag

from .base import ArticleHubTestCase


class PublicVisibilityTests(ArticleHubTestCase):
    def setUp(self):
        self.published = self.make_article(Article.Status.PUBLISHED, title='Visible publicado')
        self.hidden = [
            self.make_article(Article.Status.DRAFT, title='Oculto borrador'),
            self.make_article(Article.Status.PENDING_REVIEW, title='Oculto pendiente'),
            self.make_article(Article.Status.REJECTED, title='Oculto rechazado'),
        ]

    def assert_only_published(self, response):
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Visible publicado')
        for article in self.hidden:
            self.assertNotContains(response, article.title)

    def test_home_shows_only_published(self):
        self.assert_only_published(self.client.get(reverse('articles:home')))

    def test_category_page_shows_only_published(self):
        url = reverse('articles:category_detail', args=[self.category.slug])
        self.assert_only_published(self.client.get(url))

    def test_tag_page_shows_only_published(self):
        for article in [self.published, *self.hidden]:
            article.tags.add(self.tag)
        self.assert_only_published(self.client.get(reverse('articles:tag_detail', args=[self.tag.slug])))

    def test_author_page_shows_only_published(self):
        response = self.client.get(reverse('articles:author_detail', args=[self.author.username]))
        self.assert_only_published(response)
        self.assertEqual(response.context['published_count'], 1)

    def test_published_detail_is_public(self):
        response = self.client.get(self.published.get_absolute_url())
        self.assertContains(response, 'Visible publicado')

    def test_unpublished_detail_returns_404_for_anonymous_and_others(self):
        for article in self.hidden:
            response = self.client.get(article.get_absolute_url())
            self.assertEqual(response.status_code, 404)
            self.assertTemplateUsed(response, '404.html')
        self.client.force_login(self.other)
        for article in self.hidden:
            self.assertEqual(self.client.get(article.get_absolute_url()).status_code, 404)

    def test_private_detail_access_rules(self):
        draft = self.hidden[0]
        url = draft.get_private_url()
        self.assertEqual(self.client.get(url).status_code, 302)  # anonymous -> login
        self.client.force_login(self.other)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_login(self.author)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_login(self.editor)
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_owner_is_redirected_from_public_url_to_private_view(self):
        self.client.force_login(self.author)
        draft = self.hidden[0]
        self.assertRedirects(self.client.get(draft.get_absolute_url()), draft.get_private_url())


class SearchTests(ArticleHubTestCase):
    def setUp(self):
        self.by_title = self.make_article(Article.Status.PUBLISHED, title='Guía de Kubernetes')
        self.by_content = self.make_article(
            Article.Status.PUBLISHED,
            title='Infraestructura',
            content='Hablamos de kubernetes y contenedores en producción. ' * 3,
        )
        self.draft = self.make_article(title='Kubernetes en borrador')

    def search(self, query):
        return self.client.get(reverse('articles:search'), {'q': query})

    def test_search_by_title_and_content_only_published(self):
        response = self.search('kubernetes')
        results = list(response.context['page_obj'])
        self.assertCountEqual(results, [self.by_title, self.by_content])
        self.assertNotContains(response, 'Kubernetes en borrador')

    def test_search_by_author_category_and_tag(self):
        self.by_title.tags.add(self.tag)
        self.assertIn(self.by_title, self.search('autora').context['page_obj'])
        self.assertIn(self.by_title, self.search('Programación').context['page_obj'])
        self.assertEqual(list(self.search('python').context['page_obj']), [self.by_title])

    def test_empty_search_shows_no_results(self):
        response = self.search('')
        self.assertIsNone(response.context['page_obj'])


class FilterTests(ArticleHubTestCase):
    def setUp(self):
        self.other_category = Category.objects.create(name='Diseño')
        self.other_tag = Tag.objects.create(name='css')
        self.mine = self.make_article(Article.Status.PUBLISHED, title='De la autora')
        self.mine.tags.add(self.tag)
        self.theirs = self.make_article(
            Article.Status.PUBLISHED, author=self.other, title='Del otro', category=self.other_category
        )
        self.theirs.tags.add(self.other_tag)

    def home(self, **params):
        return list(self.client.get(reverse('articles:home'), params).context['page_obj'])

    def test_filter_by_author(self):
        self.assertEqual(self.home(author='otro'), [self.theirs])

    def test_filter_by_category(self):
        self.assertEqual(self.home(category='programacion'), [self.mine])

    def test_filter_by_tag(self):
        self.assertEqual(self.home(tag='css'), [self.theirs])

    def test_home_cards_include_counts(self):
        response = self.client.get(reverse('articles:home'))
        card = next(a for a in response.context['page_obj'] if a == self.mine)
        self.assertEqual((card.num_likes, card.num_comments), (0, 0))

    def test_home_is_paginated(self):
        for i in range(11):
            self.make_article(Article.Status.PUBLISHED, title=f'Extra {i}')
        page_one = self.client.get(reverse('articles:home'))
        self.assertEqual(len(page_one.context['page_obj']), 10)
        page_two = self.client.get(reverse('articles:home'), {'page': 2})
        self.assertEqual(len(page_two.context['page_obj']), 3)
