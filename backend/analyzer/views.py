from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.http import JsonResponse

from .models import UploadedLog
from .serializers import UploadedLogSerializer, UserSerializer

def home(request):
    return JsonResponse({"message": "🚀 Welcome to ISRO 1553B Backend API"})

class RegisterView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response({"message": "✅ User registered successfully"}, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


class CurrentUserView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        serializer = UserSerializer(request.user)
        return Response(serializer.data)


class FileUploadView(APIView):
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]

    def post(self, request, format=None):
        serializer = UploadedLogSerializer(data=request.data, context={'request': request})
        if serializer.is_valid():
            uploaded_file = serializer.save()
            return Response({
                'message': '📁 File uploaded successfully',
                'file_id': uploaded_file.id,
                'filename': uploaded_file.file.name,
                'uploaded_at': uploaded_file.uploaded_at,
            }, status=status.HTTP_201_CREATED)
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
