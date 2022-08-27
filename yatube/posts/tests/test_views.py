import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django import forms
from django.core.files.uploadedfile import SimpleUploadedFile
from django.core.cache import cache

from posts.forms import PostForm
from posts.models import Group, Post, Follow
from posts.views import POST_QUANTITY

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsViewsTests(TestCase):
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
            title='Тестовый заголовок группы',
            slug='test-group-slug',
            description='test-description',
        )
        cls.group2 = Group.objects.create(
            title='Тестовый заголовок группы2',
            slug='test-group-slug2',
            description='test-description2',
        )
        small_gif = (
            b'\x47\x49\x46\x38\x39\x61\x02\x00'
            b'\x01\x00\x80\x00\x00\x00\x00\x00'
            b'\xFF\xFF\xFF\x21\xF9\x04\x00\x00'
            b'\x00\x00\x00\x2C\x00\x00\x00\x00'
            b'\x02\x00\x01\x00\x00\x02\x02\x0C'
            b'\x0A\x00\x3B'
        )
        uploaded = SimpleUploadedFile(
            name='small.gif',
            content=small_gif,
            content_type='image/gif'
        )
        # словарь для тестового поста
        cls.post_data = {
            'text': 'Тестовый пост',
            'group': cls.group,
            'author': cls.author,
            'image': uploaded,
        }

        # тестовый пост
        for i in range(0, 10):
            cls.post = Post.objects.create(
                text=cls.post_data['text'],
                group=cls.post_data['group'],
                author=cls.post_data['author'],
                image=cls.post_data['image'],
            )

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.user = User.objects.create_user(username='views_user')
        self.guest_client = Client()
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)
        cache.clear()

    # Проверяем используемые шаблоны
    def test_pages_uses_correct_template(self):
        """URL-адрес использует соответствующий шаблон."""
        self.authorized_client = self.client
        self.authorized_client.force_login(self.author)
        # Собираем в словарь пары "имя_html_шаблона: reverse(name)"
        templates_page_names = {
            reverse('posts:index'): 'posts/index.html',
            reverse('posts:group_posts', kwargs={'slug': self.group.slug}):
                'posts/group_list.html',
            reverse('posts:profile',
                    kwargs={'username': self.author.username}):
                        'posts/profile.html',
            reverse('posts:post_detail', kwargs={'post_id': self.post.id}):
                'posts/post_detail.html',
            reverse('posts:post_edit', kwargs={'post_id': self.post.id}):
                'posts/post_create.html',
            reverse('posts:post_create'): 'posts/post_create.html',
        }
        # Проверяем, что при обращении к name
        # вызывается соответствующий HTML-шаблон
        for reverse_name, template in templates_page_names.items():
            with self.subTest(template=template):
                response = self.authorized_client.get(reverse_name)
                self.assertTemplateUsed(response, template)

    def service_asserts(self, test_object):
        """Служебные asserts."""
        self.assertEqual(test_object.pk, self.post.pk)
        self.assertEqual(
            test_object.author.username, self.post.author.username)
        self.assertEqual(test_object.group.title, self.group.title)
        self.assertEqual(test_object.text, self.post.text)

    def service_asserts_group(self, test_object):
        """Служебные asserts для тестирования групп."""
        self.assertEqual(test_object.pk, self.group.id)
        self.assertEqual(test_object.slug, self.group.slug)
        self.assertEqual(test_object.title, self.group.title)
        self.assertEqual(
            test_object.description, self.group.description)

    def helper_contexts(self, response, context):
        """Контексты для тестирования."""
        context_detail = {
            context.text: self.post_data['text'],
            context.author.username: self.post_data['author'].username,
            context.group.title: self.post_data['group'].title,
        }

        for context, expected in context_detail.items():
            with self.subTest(response=response, context=context):
                self.assertEqual(context, expected)

    def test_homepage_show_correct_contexts(self):
        """View: index получают соответствующий контекст."""
        response = self.authorized_client.get(reverse('posts:index'))
        context = response.context['page_obj'].object_list[0]
        self.assertEqual(context, self.post)
        self.helper_contexts(response, context)
        self.service_asserts(context)

    def test_profile_show_correct_contexts(self):
        """View: profile получает соответствующий контекст."""
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            )
        )

        context = response.context['page_obj'].object_list[0]
        self.assertEqual(context, self.post)
        self.helper_contexts(response, context)
        self.service_asserts(context)

        context = response.context['author']
        self.assertEqual(context, self.author)

        context = response.context['posts_count']
        self.assertEqual(context, self.post_data['author'].posts.count())

    def test_group_posts_context(self):
        """View: group_posts имеет соответствующий контекст."""
        response = self.authorized_client.get(
            reverse(
                'posts:group_posts',
                kwargs={'slug': self.group.slug}
            )
        )
        context = response.context['group']
        self.assertEqual(context, self.group)
        self.service_asserts_group(context)

        context = response.context['page_obj'].object_list[0]
        self.assertEqual(context, self.post)
        self.helper_contexts(response, context)
        self.service_asserts(context)

    def test_post_detail_show_correct_context(self):
        """View: post_detail имеет соответствующий контекст."""
        response = self.authorized_client.get(
            reverse('posts:post_detail', kwargs={'post_id': self.post.id})
        )
        context = response.context['post']
        self.assertEqual(context, self.post)
        self.helper_contexts(response, context)

        context = response.context['author']
        self.assertEqual(context, self.author)

        context = response.context['posts_count']
        self.assertEqual(context, self.post_data['author'].posts.count())

    def test_create_post_correct_context(self):
        """
        View: post_create и post_edit имеют соответствующий
        контекст.
        """
        self.authorized_client = self.client
        self.authorized_client.force_login(self.author)

        response_types = [
            self.authorized_client.get(reverse('posts:post_create')),
            self.authorized_client.get(
                reverse('posts:post_edit', kwargs={'post_id': self.post.id})
            ),
        ]

        form_fields = {
            'group': forms.fields.ChoiceField,
            'text': forms.fields.CharField,
        }

        for response in response_types:
            if response.resolver_match.func.__name__ == 'post_create':
                self.assertNotIn('is_edit', response.context)

            if response.resolver_match.func.__name__ == 'post_edit':
                context = response.context['post']
                self.assertEqual(context, self.post)

                context = response.context['is_edit']
                self.assertTrue(context)

            self.assertIsInstance(
                response.context['form'], PostForm
            )
            for value, values in form_fields.items():
                with self.subTest(value=value):
                    f_field = response.context['form'].fields.get(value)
                    self.assertIsInstance(f_field, values)

    def test_new_post_appearance(self):
        """Проверка появления новой записи на всех страницах."""
        # На главной
        response = self.authorized_client.get(reverse('posts:index'))
        self.assertEqual(
            response.context['page_obj'][0], self.post)

        # В группе
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group.slug})
        )
        self.assertEqual(response.context['page_obj'][0], self.post)

        # В профиле пользователя
        response = self.authorized_client.get(
            reverse(
                'posts:profile',
                kwargs={'username': self.author.username}
            )
        )
        post_in_profile = response.context['page_obj'][0]
        self.assertEqual(post_in_profile, self.post)

        context = {
            response.context['page_obj'][0]: self.post,
            post_in_profile.group: self.group,
        }

        for entity, entities in context.items():
            with self.subTest(element=entity):
                self.assertEqual(entity, entities)

    def test_post_not_found(self):
        """Проверка отсутствия записи не в той группе."""
        response = self.authorized_client.get(
            reverse('posts:group_posts', kwargs={'slug': self.group2.slug})
        )
        context = response.context['page_obj'].object_list
        self.assertNotIn(self.post, context)

    def test_cache_index_page(self):
        """Тест работы кэша."""
        post = Post.objects.create(author=self.user, text="Тестим кэш")

        url = reverse("posts:index")

        response = self.authorized_client.get(url)
        post.delete()
        response_cached = self.authorized_client.get(url)
        self.assertEqual(response.content, response_cached.content)

        cache.clear()
        response_cleared = self.authorized_client.get(url)
        self.assertNotEqual(response_cached.content, response_cleared.content)


class PaginatorViewsTest(TestCase):
    """Тестирование паджинатора."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.post_quantity_second_page = 3
        range_size = POST_QUANTITY + cls.post_quantity_second_page
        cls.posts = []
        cls.author = User.objects.create_user(
            username='paginator_author'
        )
        cls.group = Group.objects.create(
            title='Заголовок для паджинатора',
            slug='paginator_views',
            description='Описание для паджинатора',
        )

        for paginator_post in range(range_size):
            cls.posts.append(
                Post(
                    author=cls.author,
                    group=cls.group,
                    text=f'{paginator_post}',
                )
            )
        Post.objects.bulk_create(cls.posts)

    def setUp(self):
        self.user = User.objects.create_user(
            username='paginator_user'
        )
        self.authorized_client = self.client
        self.authorized_client.force_login(self.user)

    def test_paginator(self):
        self.authorized_client = self.client
        self.authorized_client.force_login(self.author)

        post_quantity_second_page = self.post_quantity_second_page

        response_types = {
            self.authorized_client.get(
                reverse('posts:index')
            ): POST_QUANTITY,
            self.authorized_client.get(
                reverse('posts:index') + '?page=2'
            ): post_quantity_second_page,

            self.authorized_client.get(
                reverse('posts:group_posts', kwargs={'slug': self.group.slug})
            ): POST_QUANTITY,
            self.authorized_client.get(
                reverse('posts:group_posts', kwargs={'slug': self.group.slug})
                + '?page=2'
            ): post_quantity_second_page,

            self.authorized_client.get(
                reverse(
                    'posts:profile',
                    kwargs={'username': self.author.username}
                )
            ): POST_QUANTITY,
            self.authorized_client.get(
                reverse(
                    'posts:profile',
                    kwargs={'username': self.author.username}
                )
                + '?page=2'
            ): post_quantity_second_page,
        }

        for response, quantity in response_types.items():
            self.assertEqual(len(response.context['page_obj']), quantity)


class FollowTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.author = User.objects.create_user(username='author')

        cls.post0 = Post.objects.create(
            text='Какой-то текст.',
            author=cls.author,
        )
        cls.post1 = Post.objects.create(
            text='Снова какой-то текст.',
            author=cls.author,
        )

    def setUp(self):
        self.user = User.objects.create_user(username='user')
        self.authorized_client = self.client
        self.authorized_client.force_login(self.user)
        cache.clear()

    def test_authorized_user_cannot_subscribe_on_himself(self):
        """Пользователь имеет возможность подписаться."""
        self.assertFalse(self.user.follower.exists())

        self.authorized_client.get(
            reverse(
                'posts:profile_follow',
                kwargs={'username': self.author.username}
            )
        )
        self.assertEqual(self.user.follower.first().author, self.author)

    def test_forbidden_user_subscribe_to_himself(self):
        """Пользователь не может подписаться на себя."""
        author_client = self.client
        author_client.force_login(self.author)

        response = author_client.get(
            reverse('posts:profile_follow',
                    kwargs={'username': self.author.username})
        )
        expected_redirect_url = reverse(
            'posts:profile', kwargs={'username': self.author.username}
        )
        self.assertRedirects(response, expected_redirect_url)

    def test_authorized_user_unsubscribe(self):
        """Пользователь имеет возможность отписаться."""
        Follow.objects.create(user=self.user, author=self.author)
        self.authorized_client.get(
            reverse(
                'posts:profile_unfollow',
                kwargs={'username': self.author.username}
            )
        )
        self.assertFalse(self.user.follower.exists())

    def test_new_post_shown_in_feed_subscriber(self):
        """Пост появляется в ленте подписанного пользователя."""
        Follow.objects.create(user=self.user, author=self.author)
        response = self.authorized_client.get(reverse('posts:follow_index'))
        context = response.context.get('page_obj').object_list
        self.assertIn(self.post0, context)

    def test_new_post_doesnt_show_in_feed_unsubscribed(self):
        """Пост не появляется в ленте у неподписанного пользователя."""
        unsubscribe = User.objects.create_user(username='unsubscribe_user')
        unsubscribed_client = self.client
        unsubscribed_client.force_login(unsubscribe)

        response = unsubscribed_client.get(reverse('posts:follow_index'))
        context = response.context.get('page_obj').object_list
        self.assertNotIn(self.post1, context)
