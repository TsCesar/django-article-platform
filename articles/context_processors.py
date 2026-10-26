from .permissions import is_editor


def editorial(request):
    return {'user_is_editor': is_editor(request.user)}
