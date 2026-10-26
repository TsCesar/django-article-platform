#!/usr/bin/env bash
# Render build script for ArticleHub.
set -o errexit

pip install -r requirements.txt

python manage.py collectstatic --noinput
python manage.py migrate --noinput

# Optional superuser, created only once when all three variables are set.
if [ -n "$DJANGO_SUPERUSER_USERNAME" ] && [ -n "$DJANGO_SUPERUSER_EMAIL" ] && [ -n "$DJANGO_SUPERUSER_PASSWORD" ]; then
    if python manage.py shell -c "import os, sys; from django.contrib.auth import get_user_model; sys.exit(0 if get_user_model().objects.filter(username=os.environ['DJANGO_SUPERUSER_USERNAME']).exists() else 1)"; then
        echo "Superuser '$DJANGO_SUPERUSER_USERNAME' already exists, skipping."
    else
        python manage.py createsuperuser --noinput
    fi
fi
