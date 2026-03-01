## Django Portfolio Example

Basic Django portfolio with a blog section.

![](./screenshot.png)

### Key Features

- Portfolio projects ordered by most recent date.
- Featured projects section on the home page.
- Project search on the portfolio page.
- Contact form with persistence in database and email notification.
- Staff inbox to review contact messages and mark them as read/unread.
- Staff inbox CSV export with current filters.
- Custom staff dashboard to manage portfolio projects (create/edit/delete).
- Contact anti-spam protection (honeypot + rate limiting).
- Blog posts with searchable list and pagination.
- SEO-friendly blog detail URLs based on slugs.
- Admin pages configured with filtering and search for faster content management.
- Test suite for main user flows.

### Installation

```bash
git clone https://github.com/FaztWeb/django-portfolio-simple.git
cd django-portfolio-simple
pip install -r requirements.txt
```

### Configuration

1. Copy `.env.example` to `.env` and adjust values for your environment.
2. Set a strong `DJANGO_SECRET_KEY` for production.
3. Set `DJANGO_DEBUG=False` and update `DJANGO_ALLOWED_HOSTS` in production.
4. Configure `DJANGO_CONTACT_EMAIL` for contact form notifications.
5. Configure SMTP settings (`DJANGO_EMAIL_HOST`, `DJANGO_EMAIL_PORT`, `DJANGO_EMAIL_HOST_USER`, `DJANGO_EMAIL_HOST_PASSWORD`, `DJANGO_EMAIL_USE_TLS`).

### Production SMTP Example

```env
DJANGO_EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
DJANGO_EMAIL_HOST=smtp-relay.brevo.com
DJANGO_EMAIL_PORT=587
DJANGO_EMAIL_HOST_USER=your_smtp_username
DJANGO_EMAIL_HOST_PASSWORD=your_smtp_password
DJANGO_EMAIL_USE_TLS=True
DJANGO_EMAIL_TIMEOUT=10
```

### Run

```bash
python manage.py migrate
python manage.py runserver
```

Open `http://localhost:8000`.

### Deploy on Render (PostgreSQL)

This repository includes a `render.yaml` blueprint for a free Render web service and free PostgreSQL database.

1. Push the project to GitHub.
2. In Render, create a new Blueprint and select your repository.
3. Render reads `render.yaml`, creates the web service and database, and injects `DATABASE_URL`.
4. After the first deploy, create an admin account from Render Shell:

```bash
python manage.py createsuperuser
```

For local development with SQLite, keep `DATABASE_URL` empty in `.env`.
