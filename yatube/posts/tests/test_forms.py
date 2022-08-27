import shutil
import tempfile

from django.conf import settings
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.core.files.uploadedfile import SimpleUploadedFile


from posts.models import Group, Post, Comment
from posts.forms import PostForm, CommentForm

User = get_user_model()

TEMP_MEDIA_ROOT = tempfile.mkdtemp(dir=settings.BASE_DIR)


@override_settings(MEDIA_ROOT=TEMP_MEDIA_ROOT)
class PostsFormsTests(TestCase):
    """Тестирование формы поста."""

    @classmethod
    def setUpClass(cls):
        super().setUpClass()

        cls.form = PostForm()
        cls.user = User.objects.create_user(username='test-username')

        cls.group = Group.objects.create(
            title='Тестовый заголовок группы',
            slug='test-group-slug',
            description='test-description',
        )
        cls.group2 = Group.objects.create(
            title='Тестовый заголовок группы',
            slug='test-group2-slug',
            description='test-description',
        )

        cls.post = Post.objects.create(
            group=cls.group,
            author=cls.user,
            text='Текст формы')

        cls.form_data = {
            'group': cls.group.id,
            'text': cls.post.text,
        }

    @classmethod
    def tearDownClass(cls):
        super().tearDownClass()
        shutil.rmtree(TEMP_MEDIA_ROOT, ignore_errors=True)

    def setUp(self):
        self.guest_client = Client()
        self.authorized_client = self.client
        self.authorized_client.force_login(self.user)

    def test_create_new_post(self):
        """Тестирование создания новой записи."""
        count_posts = Post.objects.count()

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

        context = {
            'group': self.group.id,
            'text': 'Какой-то текст 1',
            'image': uploaded,
        }

        response = self.authorized_client.post(
            reverse('posts:post_create'), data=context, follow=False)

        self.assertEqual(
            Post.objects.latest('id').text, context['text'])

        self.assertEqual(
            Post.objects.latest('id').group_id, context['group'])

        self.assertRedirects(
            response,
            reverse('posts:profile', args=[self.user]))

        self.assertEqual(Post.objects.count(), count_posts + 1)

    def test_editing_post(self):
        """Тестирование редактирования записи."""
        count_posts = Post.objects.count()
        latest_post_id = Post.objects.latest('id').id
        context = {
            'group': self.group2.id,
            'text': 'Какой-то текст 2',
        }
        response = self.authorized_client.post(
            reverse(
                'posts:post_edit',
                kwargs={'post_id': latest_post_id}),
            data=context, follow=True)

        self.assertRedirects(
            response, reverse(
                'posts:post_detail',
                kwargs={'post_id': latest_post_id}
            ))

        self.assertEqual(Post.objects.count(), count_posts)

        self.assertTrue(Post.objects.filter(
            id=latest_post_id, text=context['text'],
            group=context['group']).exists())

    def test_guest_client_cannot_create_post(self):
        """Тестирование невозможности создания записи без
        регистрации.
        """
        post_count = Post.objects.count()

        response = self.guest_client.post(
            reverse('posts:post_create'),
            data={'group': 1, 'text': "Guest post"},
            follow=False)

        self.assertRedirects(
            response, '%s?next=/create/' % reverse('login')
        )

        self.assertEqual(Post.objects.count(), post_count)

    def test_fail_to_edit_other_person_post(self):
        """Тестирование невозможности редактировать чужие записи."""
        edited_post_before = 'Исправленный текст'
        response = self.guest_client.post(
            reverse('posts:post_edit', args=[self.post.pk]),
            data={'text': edited_post_before},
        )
        edited_post_after = get_object_or_404(Post, pk=self.post.pk).text
        self.assertNotEqual(edited_post_after, edited_post_before)
        self.assertRedirects(
            response, (
                f'/auth/login/?next=/posts/{self.post.pk}/edit/')
        )

    def test_post_help_text(self):
        """
        Тестирование text_field и group_field.
        """
        response = PostsFormsTests.post
        fields_help_texts = {
            'group': 'Группа, к которой будет относиться пост',
            'text': 'Текст нового поста',
        }

        for field, fields in fields_help_texts.items():
            with self.subTest(field=field):
                self.assertEqual(
                    response._meta.get_field(field).help_text, fields
                )


class CommentCreateFormTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.user = User.objects.create_user(username='TestUser')
        cls.group = Group.objects.create(
            title='test-title',
            slug='test-slug',
            description='test-descrp',
        )
        cls.post = Post.objects.create(
            text='test-text',
            author=cls.user,
            group=cls.group,
        )
        cls.comment = Comment.objects.create(
            post=cls.post,
            author=cls.user,
            text='test-comment',
        )
        cls.form = CommentForm()

    def setUp(self):
        self.authorized_client = Client()
        self.authorized_client.force_login(self.user)

    def test_create_comment(self):
        """Валидная форма создает запись в Comment."""
        comments_count = Comment.objects.count()
        text = 'Testcomment'
        form_data = {
            'text': text,
        }
        post = self.post.id
        response = self.authorized_client.post(
            reverse(
                'posts:add_comment', kwargs={'post_id': f'{post}'}
            ),
            data=form_data,
            follow=True
        )
        # Проверяем, сработал ли редирект
        self.assertRedirects(
            response, reverse(
                'posts:post_detail', kwargs={'post_id': f'{post}'})
        )
        # Проверяем, увеличилось ли число постов
        self.assertEqual(Comment.objects.count(), comments_count + 1)
        self.assertTrue(
            Comment.objects.filter(
                text=text,
            ).exists()
        )
