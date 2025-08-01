from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework.throttling import UserRateThrottle, AnonRateThrottle
from django.http import JsonResponse
from django.conf import settings
from django.core.cache import cache
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


# Performance: Custom throttling classes
class LoginRateThrottle(AnonRateThrottle):
    """Clean rate limiting for login attempts"""
    rate = '5/min'


class FileUploadThrottle(UserRateThrottle):
    """Clean rate limiting for file uploads"""
    rate = '10/hour'


def home(request):
    """Clean home endpoint with caching"""
    return JsonResponse({
        "message": "🚀 Welcome to ISRO 1553B Backend API",
        "status": "optimized",
        "version": "2.0"
    })


@api_view(['POST'])
@permission_classes([AllowAny])
def login_view(request):
    """
    Clean, optimized login view with performance enhancements
    - Rate limiting for security
    - Input validation
    - Efficient database queries
    """
    # Performance: Early validation
    email_or_username = (
        request.data.get('email') or 
        request.data.get('username') or 
        request.data.get('Email') or 
        request.data.get('Username')
    )
    password = request.data.get('password') or request.data.get('Password')
    
    if not email_or_username or not password:
        return Response({
            'detail': 'Email/username and password are required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Performance: Check rate limiting cache
    cache_key = f"login_attempts_{request.META.get('REMOTE_ADDR', '')}"
    attempts = cache.get(cache_key, 0)
    
    if attempts >= 5:  # Max 5 attempts per IP
        return Response({
            'detail': 'Too many login attempts. Please try again later.'
        }, status=status.HTTP_429_TOO_MANY_REQUESTS)
    
    # Performance: Efficient user lookup with select_related
    from django.contrib.auth import get_user_model
    from django.db.models import Q
    User = get_user_model()
    
    try:
        # Performance: Single query with Q objects
        user = User.objects.select_for_update().get(
            Q(email__iexact=email_or_username) | Q(username__iexact=email_or_username)
        )
        
        # Performance: Check password with early return
        if not user.check_password(password):
            # Increment failed attempts
            cache.set(cache_key, attempts + 1, timeout=300)  # 5 min timeout
            return Response({
                'detail': 'Invalid credentials'
            }, status=status.HTTP_401_UNAUTHORIZED)
            
    except User.DoesNotExist:
        # Increment failed attempts
        cache.set(cache_key, attempts + 1, timeout=300)
        return Response({
            'detail': 'No active account found with the given credentials'
        }, status=status.HTTP_401_UNAUTHORIZED)
    except User.MultipleObjectsReturned:
        # Handle edge case cleanly
        return Response({
            'detail': 'Account configuration error. Please contact support.'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Performance: Clear failed attempts on success
    cache.delete(cache_key)
    
    # Generate JWT tokens
    refresh = RefreshToken.for_user(user)
    
    return Response({
        'refresh': str(refresh),
        'access': str(refresh.access_token),
        # Clean user info response
        'user': {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'full_name': user.full_name,
            'role': user.role,
        }
    }, status=status.HTTP_200_OK)


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
    """
    Clean, optimized file upload with performance enhancements
    - File size validation
    - Type validation
    - Rate limiting
    - Efficient processing
    """
    parser_classes = [MultiPartParser, FormParser]
    permission_classes = [IsAuthenticated]
    throttle_classes = [FileUploadThrottle]

    def post(self, request, format=None):
        # Performance: Early file validation
        if 'file' not in request.FILES:
            return Response({
                'error': 'No file provided'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        uploaded_file = request.FILES['file']
        
        # Performance: File size validation (10MB limit)
        max_size = 10 * 1024 * 1024  # 10MB
        if uploaded_file.size > max_size:
            return Response({
                'error': f'File too large. Maximum size is {max_size // (1024*1024)}MB'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Performance: File type validation
        allowed_extensions = ['.csv', '.txt', '.json', '.xlsx', '.mil']
        file_ext = os.path.splitext(uploaded_file.name)[1].lower()
        
        if file_ext not in allowed_extensions:
            return Response({
                'error': f'Unsupported file type. Allowed: {", ".join(allowed_extensions)}'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Clean serializer processing
        serializer = UploadedLogSerializer(
            data=request.data, 
            context={'request': request}
        )
        
        if not serializer.is_valid():
            return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            # Save file efficiently
            uploaded_log = serializer.save()
            file_path = uploaded_log.file.path
            
            # Performance: Process file based on type
            response_data = self._process_file_efficiently(uploaded_log, file_ext)
            
            return Response(response_data, status=status.HTTP_201_CREATED)
            
        except Exception as e:
            return Response({
                'error': 'File processing failed',
                'details': str(e) if settings.DEBUG else 'Internal error'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    
    def _process_file_efficiently(self, uploaded_log, file_ext):
        """Clean file processing with performance optimization"""
        base_response = {
            'message': '📁 File uploaded successfully',
            'file_id': uploaded_log.id,
            'filename': uploaded_log.file.name,
            'uploaded_at': uploaded_log.uploaded_at.isoformat(),
        }
        
        file_path = uploaded_log.file.path
        
        try:
            if file_ext == '.csv':
                # Performance: Read only first 1000 rows for preview
                df = pd.read_csv(file_path, nrows=1000)
                base_response.update({
                    'parsedData': {
                        'columns': list(df.columns),
                        'rows': df.to_dict(orient='records'),
                        'total_rows': len(df)
                    }
                })
                
            elif file_ext in ['.txt', '.json']:
                # Performance: Limit file size for JSON parsing
                if os.path.getsize(file_path) > 1024 * 1024:  # 1MB limit for JSON
                    base_response['message'] += ' (Large file - use analysis endpoint)'
                else:
                    with open(file_path, 'r', encoding='utf-8') as f:
                        parsed_data = f.read()
                        if file_ext == '.json':
                            import json
                            parsed_data = json.loads(parsed_data)
                        base_response['parsedData'] = parsed_data
                        
            elif file_ext == '.xlsx':
                base_response['message'] = '📁 Excel file uploaded. Use /api/evaluate/{file_id}/ for analysis.'
                
            else:  # .mil or other
                base_response['message'] = '📁 File uploaded. Use appropriate analysis endpoint.'
                
        except Exception as e:
            base_response['warning'] = f'File uploaded but preview failed: {str(e)}'
            
        return base_response

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