from django.core.paginator import Paginator
from django.db.models import Q
from django.shortcuts import get_object_or_404, redirect, render

from .models import Post


POSTS_PER_PAGE = 6


def render_posts(request):
    query = request.GET.get("q", "").strip()
    posts = Post.objects.all()
    if query:
        posts = posts.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    paginator = Paginator(posts, POSTS_PER_PAGE)
    page_obj = paginator.get_page(request.GET.get("page"))
    total_posts = posts.count()
    return render(
        request,
        "blog.html",
        {
            "posts": page_obj.object_list,
            "page_obj": page_obj,
            "query": query,
            "total_posts": total_posts,
        },
    )


def post_detail(request, slug):
    post = get_object_or_404(Post, slug=slug)
    return render(request, "post_detail.html", {"post": post})


def post_detail_legacy(request, post_id):
    post = get_object_or_404(Post, pk=post_id)
    if not post.slug:
        post.save(update_fields=["slug"])
    return redirect("blog:post_detail", slug=post.slug, permanent=True)
