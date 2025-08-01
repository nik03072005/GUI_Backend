from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings 


class UploadedLog(models.Model):
    """
    Clean model for uploaded log files with performance optimizations
    """
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, 
        on_delete=models.CASCADE,
        db_index=True  # Performance: Index for faster queries
    )
    file = models.FileField(upload_to='logs/')
    uploaded_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True  # Performance: Index for time-based queries
    )

    class Meta:
        # Performance: Composite indexes for common queries
        indexes = [
            models.Index(fields=['user', 'uploaded_at']),
            models.Index(fields=['-uploaded_at']),  # Most recent first
        ]
        # Database optimizations
        ordering = ['-uploaded_at']  # Default ordering
        
    def __str__(self):
        return f"{self.user.email} - {self.file.name}"


class CustomUser(AbstractUser):
    """
    Clean custom user model with email authentication
    """
    full_name = models.CharField(max_length=255, db_index=True)
    role = models.CharField(max_length=20, default='viewer', db_index=True)
    email = models.EmailField(unique=True, db_index=True)
    
    # Authentication configuration
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']

    class Meta:
        # Performance: Indexes for common lookups
        indexes = [
            models.Index(fields=['email']),
            models.Index(fields=['role']),
            models.Index(fields=['is_active', 'email']),
        ]
        
    def __str__(self):
        return self.email