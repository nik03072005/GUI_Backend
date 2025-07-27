from django.urls import path
from .views import RegisterView, FileUploadView, home, CurrentUserView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from .views import BMDataEvaluationView
from .views import MilStd1553Module1AnalysisView

urlpatterns = [
    path('', home),
    path('register/', RegisterView.as_view(), name='register'),
    path('upload/', FileUploadView.as_view(), name='file-upload'),
    path('current-user/', CurrentUserView.as_view(), name='current-user'),
    path('token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),
    path('evaluate/<int:file_id>/', BMDataEvaluationView.as_view(), name='bm-evaluate'),
    path('mil-std-analysis/<int:file_id>/', MilStd1553Module1AnalysisView.as_view(), name='mil_std_module1_analysis'),
    
]
