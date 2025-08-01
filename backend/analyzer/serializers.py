from rest_framework import serializers
from .models import UploadedLog
from django.contrib.auth import get_user_model

User = get_user_model()

class UploadedLogSerializer(serializers.ModelSerializer):
    class Meta:
        model = UploadedLog
        fields = ['id', 'user', 'file', 'uploaded_at']
        read_only_fields = ['id', 'uploaded_at', 'user']

    def create(self, validated_data):
        user = self.context['request'].user
        return UploadedLog.objects.create(user=user, **validated_data)


class UserSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, min_length=8)
    
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'password', 'date_joined']
        extra_kwargs = {
            'password': {'write_only': True},
            'date_joined': {'read_only': True},
            'email': {'required': True},
            'full_name': {'required': True},
        }

    def validate_email(self, value):
        """Ensure email is unique"""
        if User.objects.filter(email=value).exists():
            raise serializers.ValidationError("A user with this email already exists.")
        return value

    def create(self, validated_data):
        """Create user with hashed password"""
        password = validated_data.pop('password')
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            role=validated_data.get('role', 'viewer'),
            password=password  # This will be hashed automatically
        )
        return user

