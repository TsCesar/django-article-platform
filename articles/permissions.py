from functools import wraps

from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied


def is_editor(user):
    """Editors are members of the Editors group (via its permission), staff or superusers."""
    return user.is_authenticated and (
        user.is_staff or user.has_perm('articles.review_article')
    )


def can_view_private(user, article):
    return user.is_authenticated and (user == article.author or is_editor(user))


def editor_required(view_func):
    """Require login, then answer 403 to authenticated users without the editor role."""

    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        if not is_editor(request.user):
            raise PermissionDenied('No tienes permisos de editor.')
        return view_func(request, *args, **kwargs)

    return login_required(wrapper)
