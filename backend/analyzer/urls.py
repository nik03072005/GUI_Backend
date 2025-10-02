from django.urls import path
from .views import RegisterView, FileUploadView, home, CurrentUserView, login_view, logout_view, change_password_view
from rest_framework_simplejwt.views import TokenRefreshView
from .views import BMDataEvaluationView, health_check, list_files

urlpatterns = [
    path('', home),
    path('register/', RegisterView.as_view(), name='register'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('current-user/', CurrentUserView.as_view(), name='current-user'),
    path('login/', login_view, name='login'),  # Primary login endpoint
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('logout/', logout_view, name='logout'),
    path('change-password/', change_password_view, name='change-password'),
    path('evaluate/<int:file_id>/', BMDataEvaluationView.as_view(), name='bm-evaluate'),
    path('health/', health_check, name='health-check'),
    path('files/', list_files, name='list-files'),
]
