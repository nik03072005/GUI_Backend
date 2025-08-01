from django.urls import path
from .views import RegisterView, FileUploadView, home, CurrentUserView, login_view, logout_view
from rest_framework_simplejwt.views import TokenRefreshView
from .views import BMDataEvaluationView

urlpatterns = [
    path('', home),
    path('register/', RegisterView.as_view(), name='register'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('current-user/', CurrentUserView.as_view(), name='current-user'),
    path('token/', login_view, name='token_obtain_pair'),  # Use custom login view
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('login/', login_view, name='login'),  # Alternative endpoint
    path('logout/', logout_view, name='logout'),
    path('evaluate/<int:file_id>/', BMDataEvaluationView.as_view(), name='bm-evaluate'),
]
