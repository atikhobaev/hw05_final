from django.core.paginator import Paginator
from django.contrib.auth.models import User
from django.contrib.auth.decorators import login_required
from django.shortcuts import render, get_object_or_404, redirect


from .models import Post, Group, Comment, Follow
from .forms import PostForm, CommentForm

POST_QUANTITY = 10
CACHE_REFRESH = 20


def index(request):
    """Главная страница с постами."""
    posts = Post.objects.select_related('author').select_related('group').all()
    paginator = Paginator(posts, POST_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    index = True

    context = {
        'page_obj': page_obj,
        'index': index,
        'cache_refresh': CACHE_REFRESH,
    }

    return render(request, 'posts/index.html', context)


def group_posts(request, slug):
    """Страница группы с постами."""
    group = get_object_or_404(Group, slug=slug)
    posts = group.posts.all()
    paginator = Paginator(posts, POST_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'group': group,
        'page_obj': page_obj,
        'cache_refresh': CACHE_REFRESH,
    }
    return render(request, 'posts/group_list.html', context)


def profile(request, username):
    """Страница с постами автора."""
    author = get_object_or_404(User, username=username)
    posts = author.posts.all()
    paginator = Paginator(posts, POST_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    following = (request.user.is_authenticated
                 and request.user.follower.filter(
                     user=request.user,
                     author=author
                 ).exists())

    context = {
        'author': author,
        'page_obj': page_obj,
        'posts_count': author.posts.count(),
        'following': following,
        'cache_refresh': CACHE_REFRESH,
    }

    return render(request, 'posts/profile.html', context)


def post_detail(request, post_id):
    """Страница одного поста."""
    post = get_object_or_404(Post, pk=post_id)
    comment = Comment.objects.filter(post=post_id)
    form = CommentForm(request.POST or None)

    context = {
        'post': post,
        'author': post.author,
        'posts_count': post.author.posts.count(),
        'comments': comment,
        'form': form,
    }

    return render(request, 'posts/post_detail.html', context)


@login_required
def post_create(request):
    """Создать новый пост."""
    form = PostForm(
        request.POST or None,
    )

    if form.is_valid():
        post = form.save(False)
        post.author = request.user
        post.save()
        return redirect('posts:profile', request.user.username)

    context = {
        'form': form,
    }

    return render(request, 'posts/post_create.html', context)


@login_required
def post_edit(request, post_id):
    """Отредактировать пост."""
    post = get_object_or_404(Post, pk=post_id)
    form = PostForm(
        request.POST or None,
        files=request.FILES or None,
        instance=post,
    )

    if not request.user == post.author:
        return redirect('posts:post_detail', post_id=post_id)

    if form.is_valid():
        form.save()
        return redirect('posts:post_detail', post_id=post_id)

    context = {
        'post': post,
        'form': form,
        'is_edit': True,
    }
    return render(request, 'posts/post_create.html', context)


@login_required
def add_comment(request, post_id):
    post = Post.objects.get(pk=post_id)
    form = CommentForm(request.POST or None)
    if form.is_valid():
        comment = form.save(commit=False)
        comment.author = request.user
        comment.post = post
        comment.save()
    return redirect('posts:post_detail', post_id=post_id)


@login_required
def follow_index(request):
    post_list = Post.objects.filter(author__following__user=request.user)
    follow = True
    paginator = Paginator(post_list, POST_QUANTITY)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    context = {
        'page_obj': page_obj,
        'follow': follow,
        'cache_refresh': CACHE_REFRESH,
    }
    return render(request, 'posts/follow.html', context)


@login_required
def profile_follow(request, username):
    author = get_object_or_404(User, username=username)
    if author != request.user:
        Follow.objects.get_or_create(user=request.user, author=author)
    return redirect("posts:profile", username=username)


@login_required
def profile_unfollow(request, username):
    author = get_object_or_404(User, username=username)
    Follow.objects.filter(user=request.user, author=author).delete()
    return redirect("posts:profile", username=username)
