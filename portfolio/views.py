import csv
import logging
import time

from django.contrib.admin.views.decorators import staff_member_required
from django.conf import settings
from django.contrib import messages
from django.core.mail import send_mail
from django.db.models import Q
from django.http import HttpResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .forms import ContactMessageForm, ProjectForm
from .models import ContactMessage, Project

logger = logging.getLogger(__name__)


def home(request):
    query = request.GET.get("q", "").strip()
    projects = Project.objects.all()
    if query:
        projects = projects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    featured_projects = Project.objects.filter(is_featured=True)[:3] if not query else []
    return render(
        request,
        "home.html",
        {
            "projects": projects,
            "featured_projects": featured_projects,
            "query": query,
            "project_count": projects.count(),
        },
    )


def contact(request):
    form = ContactMessageForm(request.POST or None)
    if request.method == "POST" and _is_contact_rate_limited(request):
        messages.error(
            request, "Trop de tentatives. Merci de patienter quelques minutes."
        )
        return render(request, "contact.html", {"form": form}, status=429)

    if request.method == "POST" and form.is_valid():
        contact_message = form.save()
        email_sent = True
        try:
            send_mail(
                subject=(
                    f"{settings.CONTACT_EMAIL_SUBJECT_PREFIX} "
                    f"{contact_message.subject}"
                ),
                message=(
                    f"Nom: {contact_message.name}\n"
                    f"Email: {contact_message.email}\n\n"
                    f"Message:\n{contact_message.message}"
                ),
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[settings.CONTACT_EMAIL],
                fail_silently=False,
            )
        except Exception:
            email_sent = False
            logger.exception("Failed to send contact notification email.")

        if email_sent:
            messages.success(
                request,
                "Votre message a ete envoye avec succes. Je vous repondrai rapidement.",
            )
        else:
            messages.warning(
                request,
                "Message enregistre, mais la notification email est temporairement indisponible.",
            )
        return redirect("portfolio:contact")

    return render(request, "contact.html", {"form": form})


@staff_member_required
def dashboard_home(request):
    context = {
        "project_count": Project.objects.count(),
        "featured_count": Project.objects.filter(is_featured=True).count(),
        "unread_count": ContactMessage.objects.filter(is_read=False).count(),
    }
    return render(request, "dashboard/home.html", context)


@staff_member_required
def dashboard_project_list(request):
    query = request.GET.get("q", "").strip()
    featured = request.GET.get("featured", "all")
    projects = _filter_projects(query=query, featured=featured)
    return render(
        request,
        "dashboard/project_list.html",
        {
            "projects": projects,
            "query": query,
            "featured": featured,
            "project_count": projects.count(),
        },
    )


@staff_member_required
def dashboard_project_create(request):
    form = ProjectForm(request.POST or None, request.FILES or None)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Projet cree avec succes.")
        return redirect("portfolio:dashboard_projects")

    return render(
        request,
        "dashboard/project_form.html",
        {
            "form": form,
            "page_title": "Nouveau projet",
            "submit_label": "Creer",
        },
    )


@staff_member_required
def dashboard_project_update(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    form = ProjectForm(request.POST or None, request.FILES or None, instance=project)
    if request.method == "POST" and form.is_valid():
        form.save()
        messages.success(request, "Projet mis a jour.")
        return redirect("portfolio:dashboard_projects")

    return render(
        request,
        "dashboard/project_form.html",
        {
            "form": form,
            "page_title": "Modifier projet",
            "submit_label": "Mettre a jour",
            "project": project,
        },
    )


@staff_member_required
@require_POST
def dashboard_project_delete(request, project_id):
    project = get_object_or_404(Project, pk=project_id)
    project.delete()
    messages.success(request, "Projet supprime.")

    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return redirect(next_url)
    return redirect("portfolio:dashboard_projects")


@staff_member_required
def contact_inbox(request):
    status = request.GET.get("status", "all")
    query = request.GET.get("q", "").strip()
    contact_messages = _filter_contact_messages(status=status, query=query)

    return render(
        request,
        "contact_inbox.html",
        {
            "contact_messages": contact_messages,
            "status": status,
            "query": query,
            "message_count": contact_messages.count(),
        },
    )


@staff_member_required
def contact_inbox_export(request):
    status = request.GET.get("status", "all")
    query = request.GET.get("q", "").strip()
    contact_messages = _filter_contact_messages(status=status, query=query)

    response = HttpResponse(content_type="text/csv")
    response["Content-Disposition"] = 'attachment; filename="contact-inbox.csv"'

    writer = csv.writer(response)
    writer.writerow(["id", "date", "name", "email", "subject", "message", "is_read"])
    for contact_message in contact_messages:
        writer.writerow(
            [
                contact_message.id,
                contact_message.created_at.isoformat(),
                contact_message.name,
                contact_message.email,
                contact_message.subject,
                contact_message.message,
                "yes" if contact_message.is_read else "no",
            ]
        )
    return response


@staff_member_required
@require_POST
def contact_inbox_update(request, message_id):
    contact_message = get_object_or_404(ContactMessage, pk=message_id)
    action = request.POST.get("action", "read")
    contact_message.is_read = action != "unread"
    contact_message.save(update_fields=["is_read"])

    next_url = request.POST.get("next", "")
    if next_url and url_has_allowed_host_and_scheme(
        next_url, allowed_hosts={request.get_host()}
    ):
        return redirect(next_url)
    return redirect("portfolio:contact_inbox")


def _is_contact_rate_limited(request) -> bool:
    now = time.time()
    key = "contact_submission_timestamps"
    window = settings.CONTACT_FORM_RATE_LIMIT_WINDOW_SECONDS
    limit = settings.CONTACT_FORM_RATE_LIMIT_COUNT

    recent = [
        timestamp
        for timestamp in request.session.get(key, [])
        if now - float(timestamp) < window
    ]
    is_limited = len(recent) >= limit
    if not is_limited:
        recent.append(now)
    request.session[key] = recent
    return is_limited


def _filter_contact_messages(status: str, query: str):
    contact_messages = ContactMessage.objects.all()
    if status == "read":
        contact_messages = contact_messages.filter(is_read=True)
    elif status == "unread":
        contact_messages = contact_messages.filter(is_read=False)

    if query:
        contact_messages = contact_messages.filter(
            Q(name__icontains=query)
            | Q(email__icontains=query)
            | Q(subject__icontains=query)
            | Q(message__icontains=query)
        )
    return contact_messages


def _filter_projects(query: str, featured: str):
    projects = Project.objects.all()
    if query:
        projects = projects.filter(
            Q(title__icontains=query) | Q(description__icontains=query)
        )

    if featured == "yes":
        projects = projects.filter(is_featured=True)
    elif featured == "no":
        projects = projects.filter(is_featured=False)
    return projects
