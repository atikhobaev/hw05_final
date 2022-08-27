from django.test import TestCase, Client
from http import HTTPStatus

from posts.models import Group, Post, User


class PostURLTests(TestCase):
    # Создадим записи в тестовой БД
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        # тестовый юзер profile/test-username/
        cls.author = User.objects.create(
            username='test-username',
            email='test-email@test-email.com',
            password='test-password',
        )
        # тестовая группа group/test-slug/
        cls.group = Group.objects.create(
            title='Тестовый заголовок',
            slug='test-slug',
            description='test-description',
        )

        # тестовый пост post/test-slug/
        cls.post = Post.objects.create(
            id=333,
            group=cls.group,
            author=cls.author,
            text='Тестовый текст',
        )

    def setUp(self):
        # Создаем неавторизованный клиент
        self.guest_client = Client()
        # Создаем авторизованый клиент
        self.user = User.objects.create_user(username='SemenUrlTester')
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    # Проверяем общедоступные страницы
    def test_url_response_status_code_for_guest(self):
        url_names_status_code = {
            '/': HTTPStatus.OK,
            '/group/test-slug/': HTTPStatus.OK,
            '/profile/test-username/': HTTPStatus.OK,
            f'/posts/{self.post.id}/': HTTPStatus.OK,
            f'/posts/{self.post.id}/edit': HTTPStatus.MOVED_PERMANENTLY,
            '/some-trash-link/': HTTPStatus.NOT_FOUND,
        }
        for url, status_code in url_names_status_code.items():
            with self.subTest(url=url):
                response = self.guest_client.get(url)
                self.assertEqual(response.status_code, status_code)

    def test_url_create_guest_redirect(self):
        """Редирект /create/ для гостя."""
        response = self.guest_client.post('/create/')
        self.assertRedirects(response, '/auth/login/?next=/create/')

    # Проверяем доступность страниц для авторизованного пользователя
    def test_url_response_status_code_for_guest(self):
        url_names_status_code = {
            f'/posts/{self.post.id}/edit/': HTTPStatus.FOUND,
            '/create/': HTTPStatus.OK,
        }
        for url, status_code in url_names_status_code.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertEqual(response.status_code, status_code)

    # Проверка вызываемых шаблонов для каждого адреса
    def test_urls_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        templates_url_names = {
            '/group/test-slug/': 'posts/group_list.html',
            '/create/': 'posts/post_create.html',
            '/posts/333/': 'posts/post_detail.html',
            '/profile/test-username/': 'posts/profile.html',
        }
        for url, template in templates_url_names.items():
            with self.subTest(url=url):
                response = self.authorized_client.get(url)
                self.assertTemplateUsed(response, template)
