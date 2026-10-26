from django.conf import settings
from django.core.exceptions import ValidationError
from django.db import models, transaction
from django.urls import reverse
from django.utils import timezone
from django.utils.text import Truncator, slugify

# Slugs that would clash with fixed URLs under /articles/.
RESERVED_SLUGS = {'new'}
MIN_CONTENT_LENGTH = 100


def unique_slugify(instance, value, max_length=220):
    """Return a slug for ``value`` that is unique for the instance's model.

    Collisions get a numeric suffix: mi-articulo, mi-articulo-2, mi-articulo-3...
    """
    base = slugify(value)[: max_length - 10].strip('-') or 'articulo'
    queryset = type(instance)._default_manager.exclude(pk=instance.pk)
    slug, counter = base, 2
    while slug in RESERVED_SLUGS or queryset.filter(slug=slug).exists():
        slug = f'{base}-{counter}'
        counter += 1
    return slug


class Category(models.Model):
    name = models.CharField('nombre', max_length=80, unique=True)
    slug = models.SlugField(max_length=90, unique=True)
    description = models.TextField('descripción', blank=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'categoría'
        verbose_name_plural = 'categorías'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name, max_length=90)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('articles:category_detail', args=[self.slug])


class Tag(models.Model):
    name = models.CharField('nombre', max_length=50, unique=True)
    slug = models.SlugField(max_length=60, unique=True)

    class Meta:
        ordering = ['name']
        verbose_name = 'etiqueta'
        verbose_name_plural = 'etiquetas'

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.name, max_length=60)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('articles:tag_detail', args=[self.slug])


class ArticleQuerySet(models.QuerySet):
    def published(self):
        return self.filter(status=Article.Status.PUBLISHED)

    def with_counts(self):
        return self.annotate(
            num_likes=models.Count('likes', distinct=True),
            num_comments=models.Count('comments', distinct=True),
        )

    def for_listing(self):
        """Published articles ready to be rendered as cards."""
        return (
            self.published()
            .select_related('author', 'category')
            .prefetch_related('tags')
            .with_counts()
            .order_by('-published_at', '-pk')
        )


class Article(models.Model):
    class Status(models.TextChoices):
        DRAFT = 'DRAFT', 'Borrador'
        PENDING_REVIEW = 'PENDING_REVIEW', 'Pendiente de revisión'
        PUBLISHED = 'PUBLISHED', 'Publicado'
        REJECTED = 'REJECTED', 'Rechazado'

    EDITABLE_STATUSES = {Status.DRAFT, Status.REJECTED}

    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='articles',
        verbose_name='autor',
    )
    title = models.CharField('título', max_length=200)
    slug = models.SlugField(max_length=220, unique=True, editable=False)
    excerpt = models.CharField(
        'extracto',
        max_length=300,
        blank=True,
        help_text='Resumen breve. Si lo dejas vacío se genera a partir del contenido.',
    )
    content = models.TextField('contenido', blank=True)
    category = models.ForeignKey(
        Category,
        on_delete=models.PROTECT,
        related_name='articles',
        null=True,
        blank=True,
        verbose_name='categoría',
    )
    tags = models.ManyToManyField(Tag, related_name='articles', blank=True, verbose_name='etiquetas')
    status = models.CharField(
        'estado', max_length=20, choices=Status.choices, default=Status.DRAFT, db_index=True
    )
    created_at = models.DateTimeField('creado', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado', auto_now=True)
    submitted_at = models.DateTimeField('enviado a revisión', null=True, blank=True)
    published_at = models.DateTimeField('publicado', null=True, blank=True)

    objects = ArticleQuerySet.as_manager()

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'artículo'
        verbose_name_plural = 'artículos'
        permissions = [('review_article', 'Puede revisar artículos (aprobar o rechazar)')]

    def __str__(self):
        return self.title

    def save(self, *args, **kwargs):
        if not self.slug:
            self.slug = unique_slugify(self, self.title)
        super().save(*args, **kwargs)

    def get_absolute_url(self):
        return reverse('articles:article_detail', args=[self.slug])

    def get_private_url(self):
        return reverse('articles:article_private_detail', args=[self.slug])

    @property
    def summary(self):
        return self.excerpt or Truncator(self.content).chars(220)

    @property
    def is_published(self):
        return self.status == self.Status.PUBLISHED

    @property
    def is_editable(self):
        """Only drafts and rejected articles can be edited, deleted or submitted."""
        return self.status in self.EDITABLE_STATUSES

    def submission_errors(self):
        """List of reasons why the article cannot be sent to review yet."""
        errors = []
        if not self.is_editable:
            errors.append('Solo se pueden enviar a revisión borradores o artículos rechazados.')
        if not self.title.strip():
            errors.append('El artículo necesita un título.')
        if len(self.content.strip()) < MIN_CONTENT_LENGTH:
            errors.append(f'El contenido debe tener al menos {MIN_CONTENT_LENGTH} caracteres.')
        if self.category_id is None:
            errors.append('Selecciona una categoría.')
        return errors

    def submit_for_review(self):
        errors = self.submission_errors()
        if errors:
            raise ValidationError(errors)
        self.status = self.Status.PENDING_REVIEW
        self.submitted_at = timezone.now()
        self.save(update_fields=['status', 'submitted_at', 'updated_at'])

    @transaction.atomic
    def review(self, reviewer, decision, comment=''):
        """Approve or reject a pending article, recording a Review."""
        if self.status != self.Status.PENDING_REVIEW:
            raise ValidationError('Solo se pueden revisar artículos pendientes de revisión.')
        if decision == Review.Decision.REJECTED and not comment.strip():
            raise ValidationError('El rechazo necesita un comentario explicando el motivo.')

        review = Review.objects.create(
            article=self, reviewer=reviewer, decision=decision, comment=comment.strip()
        )
        if decision == Review.Decision.APPROVED:
            self.status = self.Status.PUBLISHED
            self.published_at = timezone.now()
        else:
            self.status = self.Status.REJECTED
        self.save(update_fields=['status', 'published_at', 'updated_at'])
        return review


class Review(models.Model):
    class Decision(models.TextChoices):
        APPROVED = 'APPROVED', 'Aprobado'
        REJECTED = 'REJECTED', 'Rechazado'

    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='reviews', verbose_name='artículo'
    )
    reviewer = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        related_name='reviews',
        verbose_name='revisor',
    )
    decision = models.CharField('decisión', max_length=10, choices=Decision.choices)
    comment = models.TextField('comentario', blank=True)
    created_at = models.DateTimeField('fecha', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'revisión'
        verbose_name_plural = 'revisiones'

    def __str__(self):
        return f'{self.get_decision_display()}: {self.article}'


class Comment(models.Model):
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='comments', verbose_name='artículo'
    )
    author = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='comments',
        verbose_name='autor',
    )
    content = models.TextField('comentario', max_length=2000)
    created_at = models.DateTimeField('creado', auto_now_add=True)
    updated_at = models.DateTimeField('actualizado', auto_now=True)

    class Meta:
        ordering = ['created_at']
        verbose_name = 'comentario'
        verbose_name_plural = 'comentarios'

    def __str__(self):
        return f'{self.author} en {self.article}'


class Like(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='likes',
        verbose_name='usuario',
    )
    article = models.ForeignKey(
        Article, on_delete=models.CASCADE, related_name='likes', verbose_name='artículo'
    )
    created_at = models.DateTimeField('fecha', auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        verbose_name = 'me gusta'
        verbose_name_plural = 'me gusta'
        constraints = [
            models.UniqueConstraint(fields=['user', 'article'], name='unique_like_per_user')
        ]

    def __str__(self):
        return f'{self.user} - {self.article}'
