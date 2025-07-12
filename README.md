# Stylish Fashion Backend

A Django REST API for AI-powered fashion analysis, user management, and admin tools. Includes Celery for async tasks, Redis for message brokering, JWT authentication, and more.

---

## Features

- User registration, login, OTP verification, password reset
- Admin and superadmin management
- AI-powered outfit analysis and chat endpoints
- User outfit and conversation history
- Prompt management for AI system
- Asynchronous email sending with Celery
- JWT and token authentication
- CORS support for frontend integration

---

## Requirements

- Python 3.8+
- Redis (for Celery broker)
- (Windows users: use Memurai or WSL for Redis)

Install dependencies:
```bash
pip install -r requirements.txt
```

---

## Environment Setup

- Copy `.env.example` to `.env` and set your environment variables (e.g. `OPENAI_API_KEY`, DB credentials if using Postgres)
- Set up your email credentials in `settings.py` for email features

---

## Running the Project

### 1. Database Migrations
```bash
python manage.py migrate
```

### 2. Create Superuser (optional)
```bash
python manage.py createsuperuser
```

### 3. Start Redis (Memurai on Windows, or use Docker/WSL)

### 4. Start Celery Worker
```bash
celery -A fashion_style worker --pool=solo --loglevel=info
```

### 5. Start Django Server
```bash
python manage.py runserver
```

### 6. (Optional) Run with Waitress (Windows production)
```bash
waitress-serve --port=8000 fashion_style.wsgi:application
```

---

## API Endpoints (Examples)

- `POST   /api/register/` — User registration
- `POST   /api/login/` — User login
- `POST   /api/verify-otp/` — OTP verification
- `POST   /api/change-password/` — Change password
- `GET    /api/admin/users/` — List users (paginated)
- `GET    /api/ai/outfit-history/` — User outfit history (paginated)
- `POST   /api/ai/analyze-outfit/` — AI outfit analysis
- `POST   /api/ai/text-query/` — AI text query
- `POST   /api/prompt/reset/` — Reset AI prompt (admin only)

---

## Postman Example Inputs

### Change Password
```json
{
  "old_password": "your_current_password",
  "new_password": "your_new_password",
  "retype_new_password": "your_new_password"
}
```

### Admin Action
```json
{
  "action": "activate" // or "deactivate", "change_role", etc.
}
```

### Prompt Reset
- POST to `/api/prompt/reset/` with an empty body (admin only)

---

## Notes
- Gunicorn does not work on Windows. Use Waitress or Django's runserver for local/Windows development.
- Celery must be running for async tasks (email, etc.)
- See `settings.py` for all configuration options.

---

## License
MIT
