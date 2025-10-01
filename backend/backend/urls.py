"""
URL configuration for backend project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import JsonResponse
from django.db import connection
import logging

logger = logging.getLogger(__name__)

def health_check(request):
    """
    Comprehensive health check that tests database connectivity
    """
    health_status = {
        "status": "healthy",
        "database": "disconnected",
        "timestamp": None
    }
    
    try:
        # Test database connectivity
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            health_status["database"] = "connected"
        
        from django.utils import timezone
        health_status["timestamp"] = timezone.now().isoformat()
        
    except Exception as e:
        logger.warning(f"Health check database error: {e}")
        health_status["database"] = f"error: {str(e)[:100]}"
        health_status["status"] = "degraded"
    
    # Return 200 even if database is down - the app might still be partially functional
    return JsonResponse(health_status)

urlpatterns = [
    path('', health_check, name='health_check'),  # Root health check
    path('healthz/', health_check, name='health_check_alt'),  # Alternative health check
    path('api/health/', health_check, name='api_health_check'),  # API health check for Render
    path('admin/', admin.site.urls),
    
    # Analyzer App Endpoints (includes login)
    path('api/', include('analyzer.urls')),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
