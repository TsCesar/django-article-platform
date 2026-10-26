from django.urls import path

from . import views

app_name = 'articles'

urlpatterns = [
    path('', views.home, name='home'),
    path('search/', views.search, name='search'),
    path('categories/', views.category_list, name='category_list'),
    path('categories/<slug:slug>/', views.category_detail, name='category_detail'),
    path('tags/<slug:slug>/', views.tag_detail, name='tag_detail'),
    path('authors/<str:username>/', views.author_detail, name='author_detail'),
    # Author area
    path('dashboard/', views.dashboard, name='dashboard'),
    path('articles/new/', views.article_create, name='article_create'),
    path('articles/<slug:slug>/', views.article_detail, name='article_detail'),
    path('articles/<slug:slug>/preview/', views.article_private_detail, name='article_private_detail'),
    path('articles/<slug:slug>/edit/', views.article_update, name='article_update'),
    path('articles/<slug:slug>/delete/', views.article_delete, name='article_delete'),
    path('articles/<slug:slug>/submit/', views.article_submit, name='article_submit'),
    # Interaction
    path('articles/<slug:slug>/like/', views.like_toggle, name='like_toggle'),
    path('articles/<slug:slug>/comments/', views.comment_create, name='comment_create'),
    path('comments/<int:pk>/delete/', views.comment_delete, name='comment_delete'),
    # Editorial panel
    path('editor/', views.editor_dashboard, name='editor_dashboard'),
    path('editor/articles/<slug:slug>/', views.editor_review, name='editor_review'),
]
