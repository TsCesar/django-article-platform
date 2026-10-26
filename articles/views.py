from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.exceptions import PermissionDenied, ValidationError
from django.core.paginator import Paginator
from django.db.models import Count, Q
from django.http import Http404, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from .forms import ArticleForm, CommentForm, ReviewForm
from .models import Article, Category, Comment, Like, Review, Tag
from .permissions import can_view_private, editor_required, is_editor

ARTICLES_PER_PAGE = 10


def paginate(request, queryset, per_page=ARTICLES_PER_PAGE):
    return Paginator(queryset, per_page).get_page(request.GET.get('page'))


def get_own_article(request, slug):
    """Return the article if the current user is its author, otherwise 403."""
    article = get_object_or_404(Article, slug=slug)
    if article.author != request.user:
        raise PermissionDenied('Solo el autor puede modificar este artículo.')
    return article


def liked_ids(user, articles):
    if not user.is_authenticated:
        return set()
    return set(
        Like.objects.filter(user=user, article__in=list(articles)).values_list('article_id', flat=True)
    )


# ---------------------------------------------------------------------------
# Public pages
# ---------------------------------------------------------------------------


def home(request):
    articles = Article.objects.for_listing()
    filters = {}

    author = request.GET.get('author', '').strip()
    if author:
        articles = articles.filter(author__username=author)
        filters['author'] = author
    category_slug = request.GET.get('category', '').strip()
    if category_slug:
        articles = articles.filter(category__slug=category_slug)
        filters['category'] = Category.objects.filter(slug=category_slug).first() or category_slug
    tag_slug = request.GET.get('tag', '').strip()
    if tag_slug:
        articles = articles.filter(tags__slug=tag_slug)
        filters['tag'] = Tag.objects.filter(slug=tag_slug).first() or tag_slug

    page_obj = paginate(request, articles)
    context = {
        'page_obj': page_obj,
        'filters': filters,
        'categories': Category.objects.annotate(
            num_published=Count('articles', filter=Q(articles__status=Article.Status.PUBLISHED))
        ),
        'authors': User.objects.filter(articles__status=Article.Status.PUBLISHED)
        .distinct()
        .order_by('username'),
        'popular_tags': Tag.objects.annotate(
            num_published=Count('articles', filter=Q(articles__status=Article.Status.PUBLISHED))
        )
        .filter(num_published__gt=0)
        .order_by('-num_published', 'name')[:12],
        'liked_ids': liked_ids(request.user, page_obj),
    }
    return render(request, 'articles/home.html', context)


def search(request):
    query = request.GET.get('q', '').strip()
    page_obj = None
    if query:
        matches = Article.objects.filter(
            Q(title__icontains=query)
            | Q(content__icontains=query)
            | Q(excerpt__icontains=query)
            | Q(author__username__icontains=query)
            | Q(category__name__icontains=query)
            | Q(tags__name__icontains=query)
        ).values('pk')
        page_obj = paginate(request, Article.objects.for_listing().filter(pk__in=matches))
    context = {
        'query': query,
        'page_obj': page_obj,
        'liked_ids': liked_ids(request.user, page_obj or []),
    }
    return render(request, 'articles/search.html', context)


def category_list(request):
    categories = Category.objects.annotate(
        num_published=Count('articles', filter=Q(articles__status=Article.Status.PUBLISHED))
    )
    return render(request, 'articles/category_list.html', {'categories': categories})


def category_detail(request, slug):
    category = get_object_or_404(Category, slug=slug)
    page_obj = paginate(request, Article.objects.for_listing().filter(category=category))
    context = {
        'category': category,
        'page_obj': page_obj,
        'liked_ids': liked_ids(request.user, page_obj),
    }
    return render(request, 'articles/category_detail.html', context)


def tag_detail(request, slug):
    tag = get_object_or_404(Tag, slug=slug)
    page_obj = paginate(request, Article.objects.for_listing().filter(tags=tag))
    context = {'tag': tag, 'page_obj': page_obj, 'liked_ids': liked_ids(request.user, page_obj)}
    return render(request, 'articles/tag_detail.html', context)


def author_detail(request, username):
    author = get_object_or_404(User, username=username)
    articles = Article.objects.for_listing().filter(author=author)
    page_obj = paginate(request, articles)
    context = {
        'author': author,
        'page_obj': page_obj,
        'published_count': page_obj.paginator.count,
        'liked_ids': liked_ids(request.user, page_obj),
    }
    return render(request, 'articles/author_detail.html', context)


def article_detail(request, slug):
    article = get_object_or_404(
        Article.objects.select_related('author', 'category').prefetch_related('tags'), slug=slug
    )
    if not article.is_published:
        # Unpublished content is never served here; its owner/editors use the private view.
        if can_view_private(request.user, article):
            return redirect(article.get_private_url())
        raise Http404('Artículo no encontrado.')

    context = {
        'article': article,
        'comments': article.comments.select_related('author'),
        'like_count': article.likes.count(),
        'user_liked': request.user.is_authenticated
        and article.likes.filter(user=request.user).exists(),
        'comment_form': CommentForm(),
    }
    return render(request, 'articles/article_detail.html', context)


# ---------------------------------------------------------------------------
# Author area
# ---------------------------------------------------------------------------


@login_required
def dashboard(request):
    articles = request.user.articles.select_related('category').order_by('-updated_at')
    counts = articles.aggregate(
        total=Count('pk'),
        drafts=Count('pk', filter=Q(status=Article.Status.DRAFT)),
        pending=Count('pk', filter=Q(status=Article.Status.PENDING_REVIEW)),
        published=Count('pk', filter=Q(status=Article.Status.PUBLISHED)),
        rejected=Count('pk', filter=Q(status=Article.Status.REJECTED)),
    )
    return render(request, 'articles/dashboard.html', {'articles': articles, 'counts': counts})


@login_required
def article_private_detail(request, slug):
    article = get_object_or_404(
        Article.objects.select_related('author', 'category').prefetch_related('tags'), slug=slug
    )
    if not can_view_private(request.user, article):
        raise PermissionDenied('No puedes ver este artículo.')
    context = {
        'article': article,
        'reviews': article.reviews.select_related('reviewer'),
        'is_owner': article.author == request.user,
    }
    return render(request, 'articles/article_private_detail.html', context)


@login_required
def article_create(request):
    form = ArticleForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        article = form.save(commit=False)
        article.author = request.user
        article.status = Article.Status.DRAFT
        article.save()
        form.save_m2m()
        messages.success(request, 'Artículo creado como borrador.')
        return redirect(article.get_private_url())
    return render(request, 'articles/article_form.html', {'form': form})


@login_required
def article_update(request, slug):
    article = get_own_article(request, slug)
    if not article.is_editable:
        messages.error(request, 'Este artículo no se puede editar en su estado actual.')
        return redirect(article.get_private_url())

    form = ArticleForm(request.POST or None, instance=article)
    if request.method == 'POST' and form.is_valid():
        form.save()
        messages.success(request, 'Artículo actualizado.')
        return redirect(article.get_private_url())
    return render(request, 'articles/article_form.html', {'form': form, 'article': article})


@login_required
def article_delete(request, slug):
    article = get_own_article(request, slug)
    if not article.is_editable:
        messages.error(request, 'Este artículo no se puede eliminar en su estado actual.')
        return redirect(article.get_private_url())

    if request.method == 'POST':
        article.delete()
        messages.success(request, 'Artículo eliminado.')
        return redirect('articles:dashboard')
    return render(request, 'articles/article_confirm_delete.html', {'article': article})


@require_POST
@login_required
def article_submit(request, slug):
    article = get_own_article(request, slug)
    try:
        article.submit_for_review()
    except ValidationError as error:
        for message in error.messages:
            messages.error(request, message)
    else:
        messages.success(request, 'Artículo enviado a revisión. Un editor lo revisará pronto.')
    return redirect(article.get_private_url())


# ---------------------------------------------------------------------------
# Comments and likes
# ---------------------------------------------------------------------------


@require_POST
@login_required
def comment_create(request, slug):
    article = get_object_or_404(Article.objects.published(), slug=slug)
    form = CommentForm(request.POST)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.article = article
        comment.author = request.user
        comment.save()
        messages.success(request, 'Comentario publicado.')
        return redirect(f'{article.get_absolute_url()}#comment-{comment.pk}')
    messages.error(request, 'El comentario no puede estar vacío.')
    return redirect(f'{article.get_absolute_url()}#comments')


@require_POST
@login_required
def comment_delete(request, pk):
    comment = get_object_or_404(Comment.objects.select_related('article'), pk=pk)
    if comment.author != request.user:
        raise PermissionDenied('Solo puedes eliminar tus propios comentarios.')
    article = comment.article
    comment.delete()
    messages.success(request, 'Comentario eliminado.')
    return redirect(f'{article.get_absolute_url()}#comments')


@require_POST
@login_required
def like_toggle(request, slug):
    article = get_object_or_404(Article.objects.published(), slug=slug)
    like, created = Like.objects.get_or_create(user=request.user, article=article)
    if not created:
        like.delete()
    liked = created
    count = article.likes.count()

    if request.headers.get('x-requested-with') == 'XMLHttpRequest':
        return JsonResponse({'liked': liked, 'count': count})
    return redirect(article.get_absolute_url())


# ---------------------------------------------------------------------------
# Editorial panel
# ---------------------------------------------------------------------------


@editor_required
def editor_dashboard(request):
    pending = (
        Article.objects.filter(status=Article.Status.PENDING_REVIEW)
        .select_related('author', 'category')
        .order_by('submitted_at', 'pk')
    )
    recent_reviews = Review.objects.select_related('article', 'reviewer')[:8]
    context = {'pending': pending, 'recent_reviews': recent_reviews}
    return render(request, 'articles/editor_dashboard.html', context)


@editor_required
def editor_review(request, slug):
    article = get_object_or_404(
        Article.objects.select_related('author', 'category').prefetch_related('tags'), slug=slug
    )
    if article.author == request.user:
        raise PermissionDenied('No puedes revisar tus propios artículos.')
    if article.status != Article.Status.PENDING_REVIEW:
        messages.info(request, 'Este artículo ya no está pendiente de revisión.')
        return redirect('articles:editor_dashboard')

    form = ReviewForm(request.POST or None, initial={'decision': request.GET.get('decision')})
    if request.method == 'POST' and form.is_valid():
        decision = form.cleaned_data['decision']
        article.review(request.user, decision, form.cleaned_data['comment'])
        if decision == Review.Decision.APPROVED:
            messages.success(request, f'"{article.title}" aprobado y publicado.')
        else:
            messages.warning(request, f'"{article.title}" rechazado. El autor verá el motivo.')
        return redirect('articles:editor_dashboard')

    context = {
        'article': article,
        'form': form,
        'previous_reviews': article.reviews.select_related('reviewer'),
    }
    return render(request, 'articles/editor_review.html', context)
