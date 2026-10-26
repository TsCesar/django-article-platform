from django.contrib import messages
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.db.models import Count, Q
from django.shortcuts import redirect, render

from articles.models import Article

from .forms import RegisterForm


def register(request):
    if request.user.is_authenticated:
        return redirect('articles:dashboard')

    form = RegisterForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        user = form.save()
        login(request, user)
        messages.success(request, f'Bienvenido a ArticleHub, {user.username}. Tu cuenta está lista.')
        return redirect('articles:dashboard')
    return render(request, 'accounts/register.html', {'form': form})


@login_required
def profile(request):
    stats = request.user.articles.aggregate(
        total=Count('pk'),
        published=Count('pk', filter=Q(status=Article.Status.PUBLISHED)),
    )
    context = {
        'stats': stats,
        'comment_count': request.user.comments.count(),
        'like_count': request.user.likes.count(),
    }
    return render(request, 'accounts/profile.html', context)
