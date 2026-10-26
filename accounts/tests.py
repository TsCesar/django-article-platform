from django.contrib.auth import get_user
from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse


class RegisterTests(TestCase):
    url = reverse('accounts:register')

    def post(self, **overrides):
        data = {
            'username': 'nuevo',
            'email': 'nuevo@example.com',
            'password1': 'unaClaveSegura-123',
            'password2': 'unaClaveSegura-123',
        }
        data.update(overrides)
        return self.client.post(self.url, data)

    def test_register_creates_user_logs_in_and_redirects(self):
        response = self.post()
        self.assertRedirects(response, reverse('articles:dashboard'))
        user = User.objects.get(username='nuevo')
        self.assertEqual(user.email, 'nuevo@example.com')
        self.assertEqual(get_user(self.client), user)

    def test_duplicate_email_is_rejected_case_insensitively(self):
        User.objects.create_user('existente', 'nuevo@example.com', 'x-Clave-12345')
        response = self.post(email='NUEVO@example.com')
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Ya existe una cuenta con este email.')
        self.assertFalse(User.objects.filter(username='nuevo').exists())

    def test_password_confirmation_must_match(self):
        response = self.post(password2='otraClave-999')
        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(username='nuevo').exists())


class LoginLogoutTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user('ana', 'ana@example.com', 'clave-Segura-1')

    def test_login_with_valid_credentials(self):
        response = self.client.post(
            reverse('accounts:login'), {'username': 'ana', 'password': 'clave-Segura-1'}
        )
        self.assertRedirects(response, reverse('articles:dashboard'))
        self.assertEqual(get_user(self.client), self.user)

    def test_login_with_wrong_password_fails(self):
        response = self.client.post(
            reverse('accounts:login'), {'username': 'ana', 'password': 'incorrecta'}
        )
        self.assertEqual(response.status_code, 200)
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_logout_requires_post_and_logs_out(self):
        self.client.force_login(self.user)
        self.assertEqual(self.client.get(reverse('accounts:logout')).status_code, 405)
        response = self.client.post(reverse('accounts:logout'))
        self.assertRedirects(response, reverse('articles:home'))
        self.assertFalse(get_user(self.client).is_authenticated)

    def test_profile_requires_login(self):
        response = self.client.get(reverse('accounts:profile'))
        self.assertRedirects(response, f"{reverse('accounts:login')}?next={reverse('accounts:profile')}")
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('accounts:profile')), 'ana@example.com')
