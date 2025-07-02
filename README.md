# ISRO 1553B Backend API

This is a Django backend project for handling user authentication and file uploads, designed for the ISRO 1553B project.

## Features

- JWT authentication (using SimpleJWT)
- Custom user model with `full_name` and `role`
- File upload API (stores logs)
- CORS enabled for all origins (development)
- Admin interface

## Project Structure

```
ISRO Backend (Django)/
│
├── backend/
│   ├── analyzer/
│   │   ├── models.py
│   │   ├── serializers.py
│   │   ├── views.py
│   │   ├── urls.py
│   │   └── ...
│   ├── backend/
│   │   ├── settings.py
│   │   ├── urls.py
│   │   └── ...
│   └── manage.py
├── requirements.txt
└── README.md
```

## Setup

1. **Install dependencies:**
    ```sh
    pip install -r requirements.txt
    ```

2. **Apply migrations:**
    ```sh
    python manage.py migrate
    ```

3. **Create a superuser (optional, for admin access):**
    ```sh
    python manage.py createsuperuser
    ```

4. **Run the development server:**
    ```sh
    python manage.py runserver
    ```

## API Endpoints

- `POST /api/token/` — Obtain JWT token
- `POST /api/token/refresh/` — Refresh JWT token
- `POST /api/register/` — Register a new user (if implemented in `analyzer/urls.py`)
- `POST /api/upload/` — Upload a log file (JWT required)
- `GET /api/current-user/` — Get current user info (JWT required)
- `admin/` — Django admin interface

> **Note:** All analyzer app endpoints are prefixed with `/api/`.

## Custom User Model

The custom user model [`CustomUser`](backend/analyzer/models.py) extends Django's `AbstractUser` and adds:
- `full_name`
- `role` (default: "viewer")

## File Uploads

Uploaded files are stored in the `media/logs/` directory and tracked by the [`UploadedLog`](backend/analyzer/models.py) model.

## Development Notes

- Media files are served in development mode (`settings.DEBUG = True`).
- CORS is enabled for all origins (for development).

## License

MIT License (add your license here)