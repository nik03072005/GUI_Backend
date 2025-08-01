from django.db import models
from django.contrib.auth.models import AbstractUser
from django.conf import settings 

class UploadedLog(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    file = models.FileField(upload_to='logs/')
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.user.username} - {self.file.name}"

class CustomUser(AbstractUser):
    full_name = models.CharField(max_length=255)
    role = models.CharField(max_length=20, default='viewer')
    email = models.EmailField(unique=True)  # Ensure email is unique for login
    
    # Make email the primary field for authentication
    USERNAME_FIELD = 'email'
    REQUIRED_FIELDS = ['username', 'full_name']  # Required when creating superuser

    def __str__(self):
        return self.email