from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import Client, TestCase

User = get_user_model()


class UserUrlTests(TestCase):
    """Проверка пользовательских страниц авторизации и
    регистрации.
    """
    def setUp(self):
        self.guest_client = Client()
        self.user = User.objects.create_user(username='test-username')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

        self.clients = {
            'guest': self.guest_client,
            'user': self.authorized_client,
        }

    def test_urls_guest(self):
        """Проверка по статусу кода URLs доступных любому
        пользователю.
        """
        guest_status_codes = {
            '/auth/signup/': HTTPStatus.OK,
            '/auth/login/': HTTPStatus.OK,
            '/auth/logout/': HTTPStatus.OK,
        }

        user_status_codes = {
            '/auth/signup/': HTTPStatus.OK,
            '/auth/login/': HTTPStatus.OK,
            '/auth/logout/': HTTPStatus.OK,
        }

        clients_status_codes = {
            'guest': guest_status_codes,
            'user': user_status_codes,
        }

        for client, status_codes in clients_status_codes.items():
            for url, status_code in status_codes.items():
                with self.subTest(client=client, url=url):
                    response = self.clients[client].get(url)
                    self.assertEqual(response.status_code, status_code)

    def test_url_uses_correct_template(self):
        """Проверка соответствия шаблонов к их URL'ам."""
        templates_urls = {
            '/auth/signup/': 'users/signup.html',
            '/auth/logout/': 'users/logged_out.html',
            '/auth/login/': 'users/login.html',
        }

        for url_address, template in templates_urls.items():
            with self.subTest(address=url_address):
                response = self.guest_client.get(url_address)
                self.assertTemplateUsed(response, template)
