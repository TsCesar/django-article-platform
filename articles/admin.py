from django.contrib import admin

from .models import Article, Category, Comment, Like, Review, Tag


@admin.register(Category)
class CategoryAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name', 'description']
    prepopulated_fields = {'slug': ['name']}


@admin.register(Tag)
class TagAdmin(admin.ModelAdmin):
    list_display = ['name', 'slug']
    search_fields = ['name']
    prepopulated_fields = {'slug': ['name']}


class ReviewInline(admin.TabularInline):
    model = Review
    extra = 0
    fields = ['decision', 'reviewer', 'comment', 'created_at']
    readonly_fields = ['created_at']


@admin.register(Article)
class ArticleAdmin(admin.ModelAdmin):
    list_display = ['title', 'author', 'category', 'status', 'submitted_at', 'published_at', 'updated_at']
    list_filter = ['status', 'category', 'tags', 'created_at']
    search_fields = ['title', 'excerpt', 'content', 'author__username']
    date_hierarchy = 'created_at'
    filter_horizontal = ['tags']
    list_select_related = ['author', 'category']
    readonly_fields = ['slug', 'created_at', 'updated_at']
    inlines = [ReviewInline]
    fieldsets = [
        (None, {'fields': ['title', 'slug', 'author', 'category', 'tags']}),
        ('Contenido', {'fields': ['excerpt', 'content']}),
        ('Flujo editorial', {'fields': ['status', 'submitted_at', 'published_at', 'created_at', 'updated_at']}),
    ]


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ['article', 'decision', 'reviewer', 'created_at']
    list_filter = ['decision', 'created_at']
    search_fields = ['article__title', 'reviewer__username', 'comment']
    date_hierarchy = 'created_at'
    list_select_related = ['article', 'reviewer']


@admin.register(Comment)
class CommentAdmin(admin.ModelAdmin):
    list_display = ['author', 'article', 'short_content', 'created_at']
    list_filter = ['created_at']
    search_fields = ['content', 'author__username', 'article__title']
    date_hierarchy = 'created_at'
    list_select_related = ['author', 'article']

    @admin.display(description='Comentario')
    def short_content(self, obj):
        return obj.content[:80]


@admin.register(Like)
class LikeAdmin(admin.ModelAdmin):
    list_display = ['user', 'article', 'created_at']
    list_filter = ['created_at']
    search_fields = ['user__username', 'article__title']
    date_hierarchy = 'created_at'
    list_select_related = ['user', 'article']
