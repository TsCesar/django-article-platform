from django.contrib import admin
from django.urls import include, path

admin.site.site_header = 'ArticleHub · Administración'
admin.site.site_title = 'ArticleHub'
admin.site.index_title = 'Gestión editorial'

urlpatterns = [
    path('admin/', admin.site.urls),
    path('accounts/', include('accounts.urls')),
    path('', include('articles.urls')),
]
