from django import forms

from .models import Article, Category, Comment, Review, Tag


class ArticleForm(forms.ModelForm):
    """Author-facing form. Status, author and dates are controlled by the backend."""

    category = forms.ModelChoiceField(
        queryset=Category.objects.all(),
        required=False,
        label='Categoría',
        empty_label='Selecciona una categoría',
        help_text='Obligatoria para enviar el artículo a revisión.',
    )
    tags = forms.ModelMultipleChoiceField(
        queryset=Tag.objects.all(),
        required=False,
        label='Etiquetas',
        widget=forms.CheckboxSelectMultiple,
    )

    class Meta:
        model = Article
        fields = ['title', 'excerpt', 'category', 'tags', 'content']
        widgets = {
            'excerpt': forms.Textarea(attrs={'rows': 2}),
            'content': forms.Textarea(attrs={'rows': 18}),
        }

    def clean_title(self):
        title = self.cleaned_data['title'].strip()
        if not title:
            raise forms.ValidationError('El título no puede estar vacío.')
        return title


class CommentForm(forms.ModelForm):
    class Meta:
        model = Comment
        fields = ['content']
        labels = {'content': 'Tu comentario'}
        widgets = {
            'content': forms.Textarea(attrs={'rows': 3, 'placeholder': 'Escribe un comentario...'})
        }

    def clean_content(self):
        content = self.cleaned_data['content'].strip()
        if not content:
            raise forms.ValidationError('El comentario no puede estar vacío.')
        return content


class ReviewForm(forms.ModelForm):
    class Meta:
        model = Review
        fields = ['decision', 'comment']
        widgets = {
            'decision': forms.RadioSelect,
            'comment': forms.Textarea(
                attrs={'rows': 4, 'placeholder': 'Obligatorio si rechazas el artículo.'}
            ),
        }

    def clean(self):
        cleaned = super().clean()
        decision = cleaned.get('decision')
        comment = (cleaned.get('comment') or '').strip()
        if decision == Review.Decision.REJECTED and not comment:
            self.add_error('comment', 'Explica el motivo del rechazo.')
        cleaned['comment'] = comment
        return cleaned
