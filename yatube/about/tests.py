from http import HTTPStatus

from django.contrib.auth import get_user_model
from django.test import TestCase

User = get_user_model()


class StaticPagesURLTests(TestCase):
    """Проверка статических страниц."""

    def setUp(self):
        self.guest_client = self.client
        self.user = User.objects.create_user(username='test-username')
        self.authorized_client = self.client
        self.authorized_client.force_login(self.user)

        self.clients = {
            'guest': self.guest_client,
            'user': self.authorized_client,
        }

    def test_urls_available_to_any_client(self):
        """Проверка URLs доступных любому пользователю"""
        urls = [
            '/about/author/',
            '/about/tech/',
        ]

        for client in self.clients:
            for url_address in urls:
                with self.subTest(client=client, address=url_address):
                    response = self.clients[client].get(url_address)
                    self.assertEqual(response.status_code, HTTPStatus.OK)

    def test_static_url_uses_correct_template(self):
        """Проверка соответствия шаблонов к их URL'ам."""
        templates_static_urls = {
            '/about/author/': 'about/author.html',
            '/about/tech/': 'about/tech.html',
        }

        for url_address, template in templates_static_urls.items():
            with self.subTest(address=url_address):
                response = self.guest_client.get(url_address)
                self.assertTemplateUsed(response, template)
