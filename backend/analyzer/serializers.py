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
    class Meta:
        model = User
        fields = ['id', 'username', 'email', 'full_name', 'role', 'password']  # ✅ Add 'password' here
        extra_kwargs = {'password': {'write_only': True}}

    def create(self, validated_data):
        user = User.objects.create_user(
            username=validated_data['username'],
            email=validated_data['email'],
            full_name=validated_data['full_name'],
            password=validated_data['password'],  # ✅ securely hashed
            role=validated_data.get('role', 'viewer')
        )
        return user

