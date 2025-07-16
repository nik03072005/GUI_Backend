from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.parsers import MultiPartParser, FormParser
from rest_framework import status, permissions
from rest_framework.permissions import AllowAny, IsAuthenticated
from django.http import JsonResponse
from django.conf import settings
import os
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import io
import base64
from datetime import datetime

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

class BMDataEvaluationView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            uploaded_log = UploadedLog.objects.get(id=file_id, user=request.user)
            file_path = uploaded_log.file.path

            df = self._parse_excel(file_path)
            if df is None:
                return Response({"error": "Invalid Excel file format or missing required columns."}, status=status.HTTP_400_BAD_REQUEST)
            analysis = self._analyze_data(df)
            return Response(analysis, status=status.HTTP_200_OK)

        except UploadedLog.DoesNotExist:
            return Response({"error": "File not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    # def _parse_csv(self, path):
    #     df = pd.read_csv(path)
    #     df['timestamp'] = pd.to_numeric(df['timestamp'], errors='coerce')
    #     df.dropna(subset=['timestamp'], inplace=True)
    #     df.sort_values('timestamp', inplace=True)
    #     return df

    def _parse_excel(self, file):
        try:
            df = pd.read_excel(file, engine='openpyxl')

            if 'Timestamp' not in df.columns or 'MessageType' not in df.columns:
                raise ValueError("Missing required columns: 'Timestamp' and/or 'MessageType'")

            df = df[['Timestamp', 'MessageType']].copy()
            df.rename(columns={'Timestamp': 'timestamp', 'MessageType': 'message_type'}, inplace=True)

            df['timestamp'] = pd.to_datetime(df['timestamp'], format='%H:%M:%S.%f', errors='coerce')
            base_time = df['timestamp'].min()
            df['timestamp'] = (df['timestamp'] - base_time).dt.total_seconds()
            df.dropna(subset=['timestamp'], inplace=True)
            df.sort_values('timestamp', inplace=True)
            return df

        except Exception as e:
            print(f"[Error parsing Excel file]: {e}")
            return None

    
    def _analyze_data(self, df):
        result = {}

        for msg_type, group in df.groupby("message_type"):
            timestamps = group["timestamp"].values
            if len(timestamps) < 2:
                continue

            intervals = np.diff(timestamps)

            result[msg_type] = {
                "average_periodicity": round(float(np.mean(intervals)), 6),
                "min_periodicity": round(float(np.min(intervals)), 6),
                "max_periodicity": round(float(np.max(intervals)), 6),
                "jitter_std_dev": round(float(np.std(intervals)), 6),
                "periodicity_plot": self._plot_timestamps(timestamps, msg_type),
                "jitter_histogram": self._plot_histogram(intervals, msg_type)
            }

        return result

    def _plot_timestamps(self, timestamps, label):
        plt.figure()
        intervals = np.diff(timestamps)
        plt.plot(range(len(intervals)), intervals, marker='o')
        plt.title(f"Periodicity of {label}")
        plt.xlabel("Occurrence")
        plt.ylabel("Timestamp")
        return self._encode_plot()

    def _plot_histogram(self, intervals, label):
        plt.figure()
        plt.hist(intervals, bins=20, edgecolor='black')
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