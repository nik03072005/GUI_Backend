from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.http import JsonResponse
from django.conf import settings
import os
import pandas as pd

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

            file = uploaded_file.file
            file_path = file.path
            ext = os.path.splitext(file_path)[1].lower()

            try:
                if ext == '.csv':
                    df = pd.read_csv(file_path)
                    data = {
                        'columns': list(df.columns),
                        'rows': df.to_dict(orient='records'),
                    }

                elif ext in ['.txt', '.json']:
                    import json
                    with open(file_path, 'r') as f:
                        parsed_json = json.load(f)

                    data = parsed_json  # Directly return your JSON dashboard data

                else:
                    return Response({
                        'message': '❌ Unsupported file format',
                        'filename': file.name
                    }, status=status.HTTP_400_BAD_REQUEST)

                return Response({
                    'message': '📁 File uploaded and parsed successfully',
                    'file_id': uploaded_file.id,
                    'filename': uploaded_file.file.name,
                    'uploaded_at': uploaded_file.uploaded_at,
                    'parsedData': data,
                }, status=status.HTTP_201_CREATED)

            except Exception as e:
                return Response({
                    'message': '📁 File uploaded, but processing failed',
                    'error': str(e),
                }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
