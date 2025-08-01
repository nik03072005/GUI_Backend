from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.http import JsonResponse
from django.conf import settings
from django.contrib.auth import authenticate, login, logout
from rest_framework_simplejwt.tokens import RefreshToken
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime
import math

from .models import UploadedLog
from .serializers import UploadedLogSerializer, UserSerializer

def home(request):
    return JsonResponse({"message": "🚀 Welcome to ISRO 1553B Backend API"})


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Custom login view that accepts email or username with password
    Compatible with JWT token endpoint format
    """
    # Handle both formats: {'email': ..., 'password': ...} or {'username': ..., 'password': ...}
    email_or_username = (
        request.data.get('email') or 
        request.data.get('username') or 
        request.data.get('Email') or 
        request.data.get('Username')
    )
    password = request.data.get('password') or request.data.get('Password')
    
    if not email_or_username or not password:
        return Response({
            'detail': 'Email/username and password are required'  # Use 'detail' for JWT compatibility
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Import User model
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()
    
    # Try to find user by email OR username
    try:
        user = User.objects.get(
            Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username)
        )
    except User.DoesNotExist:
        return Response({
            'detail': 'No active account found with the given credentials'  # JWT format
        }, status=status.HTTP_401_UNAUTHORIZED)
    except User.MultipleObjectsReturned:
        # If multiple users found, try exact email match first
        try:
            user = User.objects.get(email__iexact=email_or_username)
        except User.DoesNotExist:
            try:
                user = User.objects.get(username__iexact=email_or_username)
            except User.DoesNotExist:
                return Response({
                    'detail': 'No active account found with the given credentials'
                }, status=status.HTTP_401_UNAUTHORIZED)
    
    # Check password
    if user.check_password(password):
        # Generate JWT tokens
        refresh = RefreshToken.for_user(user)
        return Response({
            'refresh': str(refresh),
            'access': str(refresh.access_token),
            # Additional user info (optional)
            'user': {
                'id': user.id,
                'username': user.username,
                'email': user.email,
                'full_name': user.full_name,
                'role': user.role,
            }
        }, status=status.HTTP_200_OK)
    else:
        return Response({
            'detail': 'No active account found with the given credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def logout_view(request):
    """
    Logout view that blacklists the refresh token
    """
    try:
        refresh_token = request.data["refresh"]
        token = RefreshToken(refresh_token)
        token.blacklist()
        return Response({'message': 'Logout successful'}, status=status.HTTP_200_OK)
    except Exception as e:
        return Response({'error': 'Invalid token'}, status=status.HTTP_400_BAD_REQUEST)


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
                    return Response({
                        'message': '📁 File uploaded and parsed successfully',
                        'file_id': uploaded_file.id,
                        'filename': uploaded_file.file.name,
                        'uploaded_at': uploaded_file.uploaded_at,
                        'parsedData': data,
                    }, status=status.HTTP_201_CREATED)

                elif ext in ['.txt', '.json']:
                    import json
                    with open(file_path, 'r') as f:
                        parsed_json = json.load(f)
                    return Response({
                        'message': '📁 File uploaded and parsed successfully',
                        'file_id': uploaded_file.id,
                        'filename': uploaded_file.file.name,
                        'uploaded_at': uploaded_file.uploaded_at,
                        'parsedData': parsed_json,
                    }, status=status.HTTP_201_CREATED)

                elif ext == '.xlsx':
                    # For Excel, just return file_id and instruct to call evaluate
                    return Response({
                        'message': '📁 Excel file uploaded. Please call /api/evaluate/<file_id>/ for analysis.',
                        'file_id': uploaded_file.id,
                        'filename': uploaded_file.file.name,
                        'uploaded_at': uploaded_file.uploaded_at,
                    }, status=status.HTTP_201_CREATED)

                else:
                    return Response({
                        'message': '❌ Unsupported file format',
                        'filename': file.name
                    }, status=status.HTTP_400_BAD_REQUEST)

            except Exception as e:
                return Response({
                    'message': '📁 File uploaded, but processing failed',
                    'error': str(e),
                }, status=status.HTTP_201_CREATED)

        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)

class BMDataEvaluationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            uploaded_log = UploadedLog.objects.get(id=file_id, user=request.user)
            file_path = uploaded_log.file.path

            df = self._parse_excel(file_path)
            if df is None:
                return Response({"error": "Invalid Excel file format or missing required columns."}, status=status.HTTP_400_BAD_REQUEST)
            
            # Replace NaN values in the DataFrame with 0 before processing
            df = df.fillna(0)
            
            analysis = self._analyze_data(df)
            raw_data = {
                'columns': list(df.columns),
                'rows': df.to_dict(orient='records'),
            }
            
            # Sanitize all data before returning
            response_data = {
                'analysis': analysis,
                'rawData': raw_data,
            }
            sanitized_data = self._sanitize_data(response_data)
            
            return Response(sanitized_data, status=status.HTTP_200_OK)
    
        except UploadedLog.DoesNotExist:
            return Response({"error": "File not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _parse_excel(self, file):
        try:
            df = pd.read_excel(file, engine='openpyxl')
            # No column filtering, keep all columns
            return df
        except Exception as e:
            print(f"[Error parsing Excel file]: {e}")
            return None

    def _safe_float(self, val):
        try:
            f = float(val)
            if math.isnan(f) or math.isinf(f):
                return 0
            return round(f, 6)
        except Exception:
            return 0

    def _analyze_data(self, df):
        result = {}

        timestamp_col = None
        if 'timestamp' in df.columns:
            timestamp_col = 'timestamp'
        elif 'Timestamp' in df.columns:
            timestamp_col = 'Timestamp'
        else:
            raise Exception("Required column 'timestamp' or 'Timestamp' not found in file.")

        for msg_type, group in df.groupby("message_type"):
            timestamps = group[timestamp_col].values
            try:
                times = [datetime.strptime(str(t), "%H:%M:%S.%f") for t in timestamps if str(t) != "0"]
                if not times:
                    seconds = []
                else:
                    base = times[0]
                    seconds = [(t - base).total_seconds() for t in times]
            except Exception:
                seconds = pd.to_numeric(timestamps, errors='coerce')
                seconds = seconds[seconds != 0]  # Remove zeros

            if len(seconds) < 2:
                result[msg_type] = {
                    "average_periodicity": 0,
                    "min_periodicity": 0,
                    "max_periodicity": 0,
                    "jitter_std_dev": 0,
                    "periodicity_plot": None,
                    "jitter_histogram": None
                }
                continue

            intervals = np.diff(seconds)
            intervals = intervals[~np.isnan(intervals)]
            intervals = intervals[intervals != 0]  # Remove zero intervals

            if len(intervals) == 0:
                avg_periodicity = min_periodicity = max_periodicity = jitter_std_dev = 0
            else:
                avg_periodicity = self._safe_float(np.mean(intervals))
                min_periodicity = self._safe_float(np.min(intervals))
                max_periodicity = self._safe_float(np.max(intervals))
                jitter_std_dev = self._safe_float(np.std(intervals))

            result[msg_type] = {
                "average_periodicity": avg_periodicity,
                "min_periodicity": min_periodicity,
                "max_periodicity": max_periodicity,
                "jitter_std_dev": jitter_std_dev,
                "periodicity_plot": self._plot_timestamps(seconds, msg_type),
                "jitter_histogram": self._plot_histogram(intervals, msg_type)
            }

        return result

    def _plot_timestamps(self, timestamps, label):
        if len(timestamps) < 2:
            return None
        
        plt.figure()
        intervals = np.diff(timestamps)
        plt.plot(range(len(intervals)), intervals, marker='o')
        plt.title(f"Periodicity of {label}")
        plt.xlabel("Occurrence")
        plt.ylabel("Timestamp")
        return self._encode_plot()

    def _plot_histogram(self, intervals, label):
        if len(intervals) < 1:
            return None
            
        plt.figure()
        plt.hist(intervals, bins=min(20, len(intervals)), edgecolor='black')
        plt.title(f"Jitter Histogram: {label}")
        plt.xlabel("Interval (s)")
        plt.ylabel("Frequency")
        return self._encode_plot()

    def _encode_plot(self):
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png')
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        return f"data:image/png;base64,{encoded}"

    def _sanitize_data(self, data):
        """Recursively replace NaN/inf values with 0 in nested dictionaries and lists."""
        if isinstance(data, dict):
            return {k: self._sanitize_data(v) for k, v in data.items()}
        elif isinstance(data, list):
            return [self._sanitize_data(item) for item in data]
        elif isinstance(data, (float, np.float64, np.float32)):
            if math.isnan(data) or math.isinf(data):
                return 0
            return data
        else:
            return data

    def post(self, request, *args, **kwargs):
        # Assuming you get the file from request.FILES['file']
        file_obj = request.FILES['file']
        # Read Excel file into DataFrame
        df = pd.read_excel(file_obj)
        if df is None:
            return Response({"error": "Invalid Excel file format or missing required columns."}, status=status.HTTP_400_BAD_REQUEST)
        # Replace NaN values in the DataFrame with 0 before processing
        df = df.fillna(0)
        # Convert DataFrame to list of dicts for rawData
        raw_data = {
            'columns': list(df.columns),
            'rows': df.to_dict(orient='records'),
        }
        # Use the same analysis logic as in GET
        analysis = self._analyze_data(df)
        # Build response with both analysis and rawData
        response_data = {
            "analysis": analysis,
            "rawData": raw_data
        }
        sanitized_data = self._sanitize_data(response_data)
        return Response(sanitized_data, status=status.HTTP_200_OK)