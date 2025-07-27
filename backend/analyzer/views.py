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
                    # Handle empty cells in CSV
                    df = self._clean_dataframe(df)
                    data = {
                        'columns': list(df.columns),
                        'rows': df.to_dict(orient='records'),
                    }

                elif ext in ['.xlsx', '.xls']:
                    # Handle Excel files
                    df = pd.read_excel(file_path, engine='openpyxl' if ext == '.xlsx' else 'xlrd')
                    # Handle empty cells in Excel
                    df = self._clean_dataframe(df)
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
                        'message': '❌ Unsupported file format. Supported formats: .csv, .xlsx, .xls, .txt, .json',
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

    def _clean_dataframe(self, df):
        """
        Clean dataframe by handling empty cells and data quality issues
        """
        # Remove completely empty rows
        df = df.dropna(how='all')
        
        # Remove completely empty columns
        df = df.dropna(axis=1, how='all')
        
        # Fill NaN values with appropriate defaults based on column type
        for column in df.columns:
            if df[column].dtype == 'object':  # String columns
                df[column] = df[column].fillna('')
            elif df[column].dtype in ['int64', 'float64']:  # Numeric columns
                df[column] = df[column].fillna(0)
            elif df[column].dtype == 'datetime64[ns]':  # DateTime columns
                # For datetime columns, you might want to handle differently
                # Here we'll forward fill then backward fill
                df[column] = df[column].fillna(method='ffill').fillna(method='bfill')
        
        # Remove any remaining rows that are all NaN (shouldn't happen after above, but safety check)
        df = df.dropna(how='all')
        
        # Clean column names - remove extra spaces and special characters if needed
        df.columns = df.columns.str.strip()
        
        return df


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
        

class MilStd1553Module1AnalysisView(APIView):
    """
    Module 1: Evaluate data from MIL-STD-1553 data bus over defined time duration
    Analyzes: Periodicity, Jitter, and Deviations
    """
    permission_classes = [permissions.IsAuthenticated]

    def get(self, request, file_id):
        try:
            uploaded_log = UploadedLog.objects.get(id=file_id, user=request.user)
            file_path = uploaded_log.file.path

            df = self._parse_mil_std_data(file_path)
            if df is None:
                return Response({"error": "Invalid file format or missing required columns."}, status=status.HTTP_400_BAD_REQUEST)
            
            analysis_results = self._perform_module1_analysis(df)
            return Response(analysis_results, status=status.HTTP_200_OK)

        except UploadedLog.DoesNotExist:
            return Response({"error": "File not found or access denied."}, status=status.HTTP_404_NOT_FOUND)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    def _parse_mil_std_data(self, file_path):
        """Parse the MIL-STD-1553B Excel data"""
        try:
            df = pd.read_excel(file_path, engine='openpyxl')
            
            # Check for required columns
            required_columns = ['Timestamp', 'MessageType', 'CW1', 'CW2', 'DecodedInfo1', 'SW1']
            missing_columns = [col for col in required_columns if col not in df.columns]
            
            if missing_columns:
                raise ValueError(f"Missing required columns: {missing_columns}")
            
            # Convert timestamp to datetime and calculate relative time
            df['Timestamp'] = pd.to_datetime(df['Timestamp'], format='%H:%M:%S.%f', errors='coerce')
            df = df.dropna(subset=['Timestamp'])
            df = df.sort_values('Timestamp')
            
            # Calculate relative time in seconds from start
            base_time = df['Timestamp'].min()
            df['relative_time'] = (df['Timestamp'] - base_time).dt.total_seconds()
            
            # Extract RT and SA information from DecodedInfo1
            df['RT'] = df['DecodedInfo1'].str.extract(r'RT-(\d+)', expand=False).astype('Int64')
            df['SA'] = df['DecodedInfo1'].str.extract(r'SA-(\d+)', expand=False).astype('Int64')
            
            # Create message identifier combining RT and SA, handling NaN values
            df['message_id'] = df.apply(lambda row: 
                f"RT{row['RT']}_SA{row['SA']}" if pd.notna(row['RT']) and pd.notna(row['SA']) 
                else f"MSG_{row.name}", axis=1)
            
            # Clean up SW1 column - ensure it's properly formatted
            if 'SW1' in df.columns:
                df['SW1'] = df['SW1'].apply(self._clean_status_word)
            
            return df

        except Exception as e:
            print(f"[Error parsing MIL-STD-1553B file]: {e}")
            return None

    def _clean_status_word(self, sw_value):
        """Clean and normalize status word values"""
        if pd.isna(sw_value):
            return None
        
        try:
            # If it's already a number, return it
            if isinstance(sw_value, (int, float)):
                return int(sw_value)
            
            # If it's a string, try to convert
            if isinstance(sw_value, str):
                sw_value = sw_value.strip()
                if sw_value.lower() in ['', 'nan', 'null', 'none']:
                    return None
                
                # Handle hex strings
                if sw_value.startswith('0x') or sw_value.startswith('0X'):
                    return int(sw_value, 16)
                
                # Handle regular numbers
                return int(float(sw_value))
            
            return None
        except (ValueError, TypeError):
            return None

    def _analyze_data_words(self, group):
        """
        Analyze MIL-STD-1553B Data Words (DW1-DW32)
        Look for patterns, missing data, and data integrity issues
        """
        analysis = {
            "total_data_words": 0,
            "anomalies": [],
            "data_statistics": {
                "words_per_message": [],
                "missing_data_count": 0, 
                "zero_data_count": 0,
                "data_patterns": {},
                "word_utilization": {}
            }
        }
        
        # Get all data word columns (DW1 through DW32)
        data_word_columns = [col for col in group.columns if col.startswith('DW') and col[2:].isdigit()]
        data_word_columns.sort(key=lambda x: int(x[2:]))  # Sort numerically
        
        for _, row in group.iterrows():
            words_in_message = 0
            missing_words = 0
            zero_words = 0
            
            for dw_col in data_word_columns:
                dw_value = row.get(dw_col)
                
                if pd.notna(dw_value) and dw_value is not None:
                    try:
                        # Convert to integer for analysis
                        if isinstance(dw_value, str):
                            if dw_value.startswith('0x') or dw_value.startswith('0X'):
                                data_word = int(dw_value, 16)
                            else:
                                data_word = int(dw_value)
                        else:
                            data_word = int(dw_value)
                        
                        words_in_message += 1
                        analysis["total_data_words"] += 1
                        
                        # Track zero data words (might indicate issues)
                        if data_word == 0:
                            zero_words += 1
                        
                        # Track data patterns (for detecting stuck bits, etc.)
                        data_hex = f"0x{data_word:04X}"
                        if data_hex in analysis["data_statistics"]["data_patterns"]:
                            analysis["data_statistics"]["data_patterns"][data_hex] += 1
                        else:
                            analysis["data_statistics"]["data_patterns"][data_hex] = 1
                        
                        # Track word utilization
                        if dw_col in analysis["data_statistics"]["word_utilization"]:
                            analysis["data_statistics"]["word_utilization"][dw_col] += 1
                        else:
                            analysis["data_statistics"]["word_utilization"][dw_col] = 1
                            
                    except (ValueError, TypeError):
                        missing_words += 1
                else:
                    missing_words += 1
            
            # Record statistics for this message
            analysis["data_statistics"]["words_per_message"].append(words_in_message)
            analysis["data_statistics"]["missing_data_count"] += missing_words
            analysis["data_statistics"]["zero_data_count"] += zero_words
            
            # Check for anomalies in this message
            if missing_words > 0:
                analysis["anomalies"].append({
                    "timestamp": row['relative_time'],
                    "type": "DATA_WORD_ERROR",
                    "description": f"Missing {missing_words} data words in message",
                    "severity": "MODERATE" if missing_words < 5 else "HIGH"
                })
            
            if zero_words > words_in_message * 0.8:  # More than 80% zeros
                analysis["anomalies"].append({
                    "timestamp": row['relative_time'],
                    "type": "DATA_INTEGRITY_WARNING",
                    "description": f"Suspicious: {zero_words} zero data words",
                    "severity": "LOW"
                })
        
        # Analyze data patterns for anomalies
        self._analyze_data_patterns(analysis)
        
        return analysis

    def _analyze_data_patterns(self, analysis):
        """
        Analyze data word patterns to detect stuck bits, repeated values, etc.
        """
        patterns = analysis["data_statistics"]["data_patterns"]
        total_words = analysis["total_data_words"]
        
        if total_words == 0:
            return
        
        # Look for excessively repeated patterns (might indicate stuck bits)
        for pattern, count in patterns.items():
            percentage = (count / total_words) * 100
            
            if percentage > 50:  # Same pattern in >50% of data words
                analysis["anomalies"].append({
                    "timestamp": 0,  # Pattern-based, not tied to specific timestamp
                    "type": "DATA_PATTERN_ANOMALY",
                    "description": f"Potential stuck bits: {pattern} appears in {percentage:.1f}% of data words",
                    "severity": "HIGH"
                })
            elif percentage > 25:  # Same pattern in >25% of data words
                analysis["anomalies"].append({
                    "timestamp": 0,
                    "type": "DATA_PATTERN_WARNING", 
                    "description": f"Repeated pattern detected: {pattern} appears in {percentage:.1f}% of data words",
                    "severity": "MODERATE"
                })
        
        # Check for word utilization issues
        utilization = analysis["data_statistics"]["word_utilization"]
        if utilization:
            max_usage = max(utilization.values())
            for word, usage in utilization.items():
                if usage < max_usage * 0.1:  # Less than 10% of max usage
                    analysis["anomalies"].append({
                        "timestamp": 0,
                        "type": "DATA_UTILIZATION_WARNING",
                        "description": f"{word} rarely used ({usage} times vs {max_usage} max)",
                        "severity": "LOW"
                    })

    def _perform_module1_analysis(self, df):
        """
        Perform Module 1 analysis: Periodicity, Jitter, and Deviations
        """
        results = {
            "summary": {
                "total_messages": len(df),
                "time_duration": f"{df['relative_time'].max():.2f} seconds",
                "unique_message_types": df['message_id'].nunique(),
                "analysis_timestamp": datetime.now().isoformat()
            },
            "periodicity_analysis": {},
            "jitter_analysis": {},
            "deviations_analysis": {},
            "visualizations": {}
        }
        
        # Group by message type (RT-SA combination) for analysis
        for message_id, group in df.groupby('message_id'):
            if len(group) < 3:  # Need at least 3 messages for meaningful analysis
                continue
                
            timestamps = group['relative_time'].values
            intervals = np.diff(timestamps)
            
            # Skip if no intervals
            if len(intervals) == 0:
                continue
            
            # 1. PERIODICITY ANALYSIS
            periodicity_stats = self._analyze_periodicity(timestamps, intervals, message_id)
            results["periodicity_analysis"][message_id] = periodicity_stats
            
            # 2. JITTER ANALYSIS  
            jitter_stats = self._analyze_jitter(intervals, message_id)
            results["jitter_analysis"][message_id] = jitter_stats
            
            # 3. DEVIATIONS ANALYSIS
            deviation_stats = self._analyze_deviations(group, intervals, message_id)
            results["deviations_analysis"][message_id] = deviation_stats
        
        # Generate overall system health assessment
        results["system_health"] = self._assess_system_health(results)
        
        return results

    def _analyze_periodicity(self, timestamps, intervals, message_id):
        """
        Analyze periodicity of messages
        Calculate average, min, max intervals and create time-series plots
        """
        stats = {
            "average_interval": round(float(np.mean(intervals)), 6),
            "min_interval": round(float(np.min(intervals)), 6),
            "max_interval": round(float(np.max(intervals)), 6),
            "expected_frequency": round(1.0 / np.mean(intervals), 4) if np.mean(intervals) > 0 else 0,
            "total_occurrences": len(timestamps),
            "time_series_plot": self._create_periodicity_plot(timestamps, intervals, message_id)
        }
        
        # Assess periodicity regularity
        cv = np.std(intervals) / np.mean(intervals) if np.mean(intervals) > 0 else float('inf')
        if cv < 0.1:
            stats["regularity"] = "HIGHLY_REGULAR"
        elif cv < 0.3:
            stats["regularity"] = "REGULAR"
        elif cv < 0.5:
            stats["regularity"] = "MODERATELY_IRREGULAR"
        else:
            stats["regularity"] = "HIGHLY_IRREGULAR"
            
        return stats

    def _analyze_jitter(self, intervals, message_id):
        """
        Analyze jitter (variability in time intervals)
        Calculate standard deviation and create histograms
        """
        jitter_std = np.std(intervals)
        mean_interval = np.mean(intervals)
        
        stats = {
            "jitter_std_dev": round(float(jitter_std), 6),
            "jitter_variance": round(float(np.var(intervals)), 6),
            "coefficient_of_variation": round(float(jitter_std / mean_interval), 4) if mean_interval > 0 else 0,
            "jitter_range": round(float(np.max(intervals) - np.min(intervals)), 6),
            "jitter_histogram": self._create_jitter_histogram(intervals, message_id)
        }
        
        # Classify jitter level
        jitter_percentage = (jitter_std / mean_interval * 100) if mean_interval > 0 else 0
        if jitter_percentage < 5:
            stats["jitter_level"] = "LOW"
        elif jitter_percentage < 15:
            stats["jitter_level"] = "MODERATE"
        elif jitter_percentage < 30:
            stats["jitter_level"] = "HIGH"
        else:
            stats["jitter_level"] = "CRITICAL"
            
        return stats

    def _analyze_deviations(self, group, intervals, message_id):
        """
        Analyze deviations from expected behavior
        Check for anomalies, status word errors, sequence issues
        """
        deviations = {
            "anomalies": [],
            "status_word_errors": 0,
            "sequence_issues": 0,
            "timing_outliers": [],
            "deviation_plot": None
        }
        
        # 1. Timing Outliers (using IQR method)
        if len(intervals) > 4:
            Q1 = np.percentile(intervals, 25)
            Q3 = np.percentile(intervals, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = []
            for i, interval in enumerate(intervals):
                if interval < lower_bound or interval > upper_bound:
                    outliers.append({
                        "occurrence": i + 1,
                        "interval": round(float(interval), 6),
                        "deviation_type": "TIMING_OUTLIER",
                        "severity": "HIGH" if interval > 2 * upper_bound or interval < 0.5 * lower_bound else "MODERATE"
                    })
            deviations["timing_outliers"] = outliers
        
    def _analyze_deviations(self, group, intervals, message_id):
        """
        Analyze deviations from expected behavior
        Check for anomalies, status word errors, sequence issues
        """
        deviations = {
            "anomalies": [],
            "status_word_analysis": {},
            "sequence_issues": 0,
            "timing_outliers": [],
            "deviation_plot": None
        }
        
        # 1. Timing Outliers (using IQR method)
        if len(intervals) > 4:
            Q1 = np.percentile(intervals, 25)
            Q3 = np.percentile(intervals, 75)
            IQR = Q3 - Q1
            lower_bound = Q1 - 1.5 * IQR
            upper_bound = Q3 + 1.5 * IQR
            
            outliers = []
            for i, interval in enumerate(intervals):
                if interval < lower_bound or interval > upper_bound:
                    outliers.append({
                        "occurrence": i + 1,
                        "interval": round(float(interval), 6),
                        "deviation_type": "TIMING_OUTLIER",
                        "severity": "HIGH" if interval > 2 * upper_bound or interval < 0.5 * lower_bound else "MODERATE"
                    })
            deviations["timing_outliers"] = outliers
        
        # 2. Status Word Analysis - Properly decode MIL-STD-1553B status words
        status_analysis = self._analyze_status_words(group)
        deviations["status_word_analysis"] = status_analysis
        
        # 2.1. Command Word Analysis - Decode command structure
        command_analysis = self._analyze_command_words(group)
        deviations["command_word_analysis"] = command_analysis
        
        # 2.2. Data Word Analysis - Analyze data patterns
        data_analysis = self._analyze_data_words(group)
        deviations["data_word_analysis"] = data_analysis
        
        # Add anomalies based on actual error conditions
        for error in status_analysis["errors"]:
            deviations["anomalies"].append({
                "timestamp": error["timestamp"],
                "type": "STATUS_WORD_ERROR",
                "description": error["description"],
                "severity": error["severity"]
            })
            
        # Add command word anomalies
        for error in command_analysis["anomalies"]:
            deviations["anomalies"].append(error)
            
        # Add data word anomalies  
        for error in data_analysis["anomalies"]:
            deviations["anomalies"].append(error)
        
        # 3. Sequence Issues (gaps in expected timing)
        expected_interval = np.median(intervals) if len(intervals) > 0 else 0
        if expected_interval > 0:
            tolerance = expected_interval * 0.5  # 50% tolerance
            sequence_issues = 0
            
            for i, interval in enumerate(intervals):
                if abs(interval - expected_interval) > tolerance:
                    sequence_issues += 1
                    if interval > expected_interval * 2:
                        deviations["anomalies"].append({
                            "occurrence": i + 1,
                            "type": "DELAYED_MESSAGE",
                            "description": f"Message delayed by {interval - expected_interval:.3f}s",
                            "severity": "MODERATE"
                        })
                    elif interval < expected_interval * 0.5:
                        deviations["anomalies"].append({
                            "occurrence": i + 1,
                            "type": "EARLY_MESSAGE", 
                            "description": f"Message arrived {expected_interval - interval:.3f}s early",
                            "severity": "LOW"
                        })
            
            deviations["sequence_issues"] = sequence_issues
        
        # 4. Create deviation visualization
        deviations["deviation_plot"] = self._create_deviation_plot(intervals, message_id)
        
        return deviations

    def _analyze_status_words(self, group):
        """
        Properly analyze MIL-STD-1553B status words
        Decode individual bits to understand actual system status
        """
        analysis = {
            "total_status_words": 0,
            "errors": [],
            "warnings": [],
            "normal_operations": 0,
            "bit_statistics": {
                "message_error": 0,
                "service_request": 0, 
                "busy": 0,
                "subsystem_flag": 0,
                "broadcast_received": 0,
                "terminal_flag": 0
            }
        }
        
        for _, row in group.iterrows():
            sw1_value = row.get('SW1')
            if pd.isna(sw1_value) or sw1_value is None:
                continue
                
            try:
                # Convert to integer for bit manipulation
                if isinstance(sw1_value, str):
                    if sw1_value.startswith('0x') or sw1_value.startswith('0X'):
                        status_word = int(sw1_value, 16)
                    else:
                        status_word = int(sw1_value)
                else:
                    status_word = int(sw1_value)
                
                analysis["total_status_words"] += 1
                
                # Decode status word bits according to MIL-STD-1553B
                rt_address = (status_word >> 11) & 0x1F  # Bits 15-11
                message_error = bool(status_word & 0x0400)  # Bit 10
                instrumentation = bool(status_word & 0x0200)  # Bit 9  
                service_request = bool(status_word & 0x0100)  # Bit 8
                broadcast_received = bool(status_word & 0x0010)  # Bit 4
                busy = bool(status_word & 0x0008)  # Bit 3
                subsystem_flag = bool(status_word & 0x0004)  # Bit 2
                dyn_bus_control = bool(status_word & 0x0002)  # Bit 1
                terminal_flag = bool(status_word & 0x0001)  # Bit 0
                
                # Update bit statistics
                if message_error:
                    analysis["bit_statistics"]["message_error"] += 1
                if service_request:
                    analysis["bit_statistics"]["service_request"] += 1
                if busy:
                    analysis["bit_statistics"]["busy"] += 1
                if subsystem_flag:
                    analysis["bit_statistics"]["subsystem_flag"] += 1
                if broadcast_received:
                    analysis["bit_statistics"]["broadcast_received"] += 1
                if terminal_flag:
                    analysis["bit_statistics"]["terminal_flag"] += 1
                
                # Classify based on actual error conditions
                if message_error:
                    analysis["errors"].append({
                        "timestamp": row['relative_time'],
                        "status_word": f"0x{status_word:04X}",
                        "rt_address": rt_address,
                        "description": f"RT-{rt_address}: Message Error detected",
                        "severity": "CRITICAL"
                    })
                elif busy:
                    analysis["warnings"].append({
                        "timestamp": row['relative_time'],
                        "status_word": f"0x{status_word:04X}", 
                        "rt_address": rt_address,
                        "description": f"RT-{rt_address}: Terminal Busy",
                        "severity": "MODERATE"
                    })
                elif service_request:
                    # Service request is often normal operation, not an error
                    analysis["warnings"].append({
                        "timestamp": row['relative_time'],
                        "status_word": f"0x{status_word:04X}",
                        "rt_address": rt_address, 
                        "description": f"RT-{rt_address}: Service Request",
                        "severity": "LOW"
                    })
                else:
                    analysis["normal_operations"] += 1
                    
            except (ValueError, TypeError) as e:
                # Skip malformed status words
                continue
        
        return analysis

    def _analyze_command_words(self, group):
        """
        Analyze MIL-STD-1553B Command Words (CW1, CW2)
        Decode RT address, T/R bit, subaddress, and word count
        """
        analysis = {
            "total_commands": 0,
            "anomalies": [],
            "command_statistics": {
                "receive_commands": 0,
                "transmit_commands": 0,
                "mode_commands": 0,
                "unique_subaddresses": set(),
                "rt_addresses": set()
            },
            "protocol_violations": []
        }
        
        for _, row in group.iterrows():
            # Analyze CW1 (primary command word)
            cw1_value = row.get('CW1')
            if pd.notna(cw1_value) and cw1_value is not None:
                cw_analysis = self._decode_command_word(cw1_value, row['relative_time'], "CW1")
                if cw_analysis:
                    analysis["total_commands"] += 1
                    
                    # Update statistics
                    if cw_analysis["is_transmit"]:
                        analysis["command_statistics"]["transmit_commands"] += 1
                    else:
                        analysis["command_statistics"]["receive_commands"] += 1
                    
                    if cw_analysis["is_mode_command"]:
                        analysis["command_statistics"]["mode_commands"] += 1
                    
                    analysis["command_statistics"]["unique_subaddresses"].add(cw_analysis["subaddress"])
                    analysis["command_statistics"]["rt_addresses"].add(cw_analysis["rt_address"])
                    
                    # Check for anomalies
                    if cw_analysis["anomalies"]:
                        analysis["anomalies"].extend(cw_analysis["anomalies"])
            
            # Analyze CW2 if present (for RT-RT transfers)
            cw2_value = row.get('CW2')
            if pd.notna(cw2_value) and cw2_value is not None:
                cw_analysis = self._decode_command_word(cw2_value, row['relative_time'], "CW2")
                if cw_analysis and cw_analysis["anomalies"]:
                    analysis["anomalies"].extend(cw_analysis["anomalies"])
        
        # Convert sets to lists for JSON serialization
        analysis["command_statistics"]["unique_subaddresses"] = list(analysis["command_statistics"]["unique_subaddresses"])
        analysis["command_statistics"]["rt_addresses"] = list(analysis["command_statistics"]["rt_addresses"])
        
        return analysis

    def _decode_command_word(self, cw_value, timestamp, cw_type):
        """
        Decode individual command word according to MIL-STD-1553B
        """
        try:
            # Convert to integer
            if isinstance(cw_value, str):
                if cw_value.startswith('0x') or cw_value.startswith('0X'):
                    command_word = int(cw_value, 16)
                else:
                    command_word = int(cw_value)
            else:
                command_word = int(cw_value)
            
            # Decode command word structure
            rt_address = (command_word >> 11) & 0x1F  # Bits 15-11
            tr_bit = bool(command_word & 0x0400)      # Bit 10 (T/R)
            subaddress = (command_word >> 5) & 0x1F   # Bits 9-5
            word_count = command_word & 0x1F          # Bits 4-0
            
            # Determine if it's a mode command
            is_mode_command = (subaddress == 0x00 or subaddress == 0x1F)
            
            analysis = {
                "command_word": f"0x{command_word:04X}",
                "rt_address": rt_address,
                "is_transmit": tr_bit,
                "subaddress": subaddress,
                "word_count": word_count,
                "is_mode_command": is_mode_command,
                "anomalies": []
            }
            
            # Check for protocol violations
            if rt_address == 0x1F:  # RT address 31 is reserved for broadcast
                if not tr_bit:  # Broadcast commands should be receive commands
                    analysis["anomalies"].append({
                        "timestamp": timestamp,
                        "type": "COMMAND_WORD_ERROR",
                        "description": f"{cw_type}: Invalid broadcast transmit command",
                        "severity": "HIGH"
                    })
            
            if is_mode_command:
                # Mode commands have specific rules
                if word_count > 0x1F:
                    analysis["anomalies"].append({
                        "timestamp": timestamp,
                        "type": "COMMAND_WORD_ERROR", 
                        "description": f"{cw_type}: Invalid mode command code {word_count}",
                        "severity": "MODERATE"
                    })
            else:
                # Data commands - word count should be 1-32 (0 means 32)
                if word_count == 0:
                    word_count = 32  # 0 means 32 words
                
                if word_count > 32:
                    analysis["anomalies"].append({
                        "timestamp": timestamp,
                        "type": "COMMAND_WORD_ERROR",
                        "description": f"{cw_type}: Invalid word count {word_count}",
                        "severity": "HIGH"
                    })
            
            return analysis
            
        except (ValueError, TypeError):
            return None
        
        # 3. Sequence Issues (gaps in expected timing)
        expected_interval = np.median(intervals) if len(intervals) > 0 else 0
        if expected_interval > 0:
            tolerance = expected_interval * 0.5  # 50% tolerance
            sequence_issues = 0
            
            for i, interval in enumerate(intervals):
                if abs(interval - expected_interval) > tolerance:
                    sequence_issues += 1
                    if interval > expected_interval * 2:
                        deviations["anomalies"].append({
                            "occurrence": i + 1,
                            "type": "DELAYED_MESSAGE",
                            "description": f"Message delayed by {interval - expected_interval:.3f}s",
                            "severity": "MODERATE"
                        })
                    elif interval < expected_interval * 0.5:
                        deviations["anomalies"].append({
                            "occurrence": i + 1,
                            "type": "EARLY_MESSAGE", 
                            "description": f"Message arrived {expected_interval - interval:.3f}s early",
                            "severity": "LOW"
                        })
            
            deviations["sequence_issues"] = sequence_issues
        
        # 4. Create deviation visualization
        deviations["deviation_plot"] = self._create_deviation_plot(intervals, message_id)
        
        return deviations

    def _assess_system_health(self, results):
        """
        Assess overall system health based on analysis results
        """
        health_score = 100
        issues = []
        
        # Check periodicity issues
        irregular_messages = 0
        for msg_id, periodicity in results["periodicity_analysis"].items():
            if periodicity["regularity"] in ["MODERATELY_IRREGULAR", "HIGHLY_IRREGULAR"]:
                irregular_messages += 1
                health_score -= 10
        
        # Check jitter issues  
        high_jitter_messages = 0
        for msg_id, jitter in results["jitter_analysis"].items():
            if jitter["jitter_level"] in ["HIGH", "CRITICAL"]:
                high_jitter_messages += 1
                health_score -= 15
        
        # Check deviation issues - now properly accounting for all word types
        total_anomalies = 0
        critical_issues = 0
        message_errors = 0
        busy_conditions = 0
        command_violations = 0
        data_integrity_issues = 0
        
        for msg_id, deviations in results["deviations_analysis"].items():
            total_anomalies += len(deviations["anomalies"])
            critical_issues += len([a for a in deviations["anomalies"] if a["severity"] == "CRITICAL"])
            
            # Count specific MIL-STD-1553B status conditions
            status_analysis = deviations.get("status_word_analysis", {})
            message_errors += status_analysis.get("bit_statistics", {}).get("message_error", 0)
            busy_conditions += status_analysis.get("bit_statistics", {}).get("busy", 0)
            
            # Count command word violations
            command_analysis = deviations.get("command_word_analysis", {})
            command_violations += len([a for a in command_analysis.get("anomalies", []) if "COMMAND_WORD_ERROR" in a.get("type", "")])
            
            # Count data integrity issues
            data_analysis = deviations.get("data_word_analysis", {})
            data_integrity_issues += len([a for a in data_analysis.get("anomalies", []) if "DATA" in a.get("type", "")])
        
        health_score -= (total_anomalies * 5)
        health_score -= (critical_issues * 10)
        health_score -= (message_errors * 20)    # Message errors are serious
        health_score -= (busy_conditions * 5)    # Busy conditions impact performance
        health_score -= (command_violations * 15) # Protocol violations are serious
        health_score -= (data_integrity_issues * 8) # Data issues affect reliability
        
        # Determine health status
        health_score = max(0, health_score)
        if health_score >= 90:
            status = "EXCELLENT"
        elif health_score >= 75:
            status = "GOOD"  
        elif health_score >= 60:
            status = "FAIR"
        elif health_score >= 40:
            status = "POOR"
        else:
            status = "CRITICAL"
            
        return {
            "overall_score": health_score,
            "health_status": status,
            "irregular_messages": irregular_messages,
            "high_jitter_messages": high_jitter_messages,
            "total_anomalies": total_anomalies,
            "critical_issues": critical_issues,
            "message_errors": message_errors,
            "busy_conditions": busy_conditions,
            "command_violations": command_violations,
            "data_integrity_issues": data_integrity_issues,
            "recommendations": self._generate_recommendations(health_score, irregular_messages, high_jitter_messages, critical_issues, message_errors, command_violations, data_integrity_issues)
        }

    def _generate_recommendations(self, health_score, irregular_messages, high_jitter_messages, critical_issues, message_errors, command_violations=0, data_integrity_issues=0):
        """Generate recommendations based on comprehensive analysis"""
        recommendations = []
        
        if health_score < 60:
            recommendations.append("System requires immediate attention due to low health score")
        
        if message_errors > 0:
            recommendations.append(f"CRITICAL: {message_errors} message errors detected - check RT hardware/connections")
        
        if command_violations > 0:
            recommendations.append(f"Protocol violations detected: {command_violations} invalid command words - verify BC programming")
            
        if data_integrity_issues > 0:
            recommendations.append(f"Data integrity concerns: {data_integrity_issues} data word anomalies - check subsystem outputs")
        
        if irregular_messages > 0:
            recommendations.append(f"Review BC scheduling for {irregular_messages} message types with irregular periodicity")
            
        if high_jitter_messages > 0:
            recommendations.append(f"Investigate timing stability for {high_jitter_messages} message types with high jitter")
            
        if critical_issues > 0:
            recommendations.append(f"Address {critical_issues} critical timing/protocol issues immediately")
        
        if not recommendations:
            recommendations.append("System is operating within normal parameters")
            
        return recommendations

    def _create_periodicity_plot(self, timestamps, intervals, message_id):
        """Create time-series plot for periodicity analysis"""
        plt.figure(figsize=(10, 6))
        plt.plot(range(len(intervals)), intervals, marker='o', linewidth=1, markersize=3)
        plt.title(f"Periodicity Analysis: {message_id}")
        plt.xlabel("Message Occurrence")
        plt.ylabel("Time Interval (seconds)")
        plt.grid(True, alpha=0.3)
        
        # Add mean line
        mean_interval = np.mean(intervals)
        plt.axhline(y=mean_interval, color='r', linestyle='--', alpha=0.7, label=f'Mean: {mean_interval:.3f}s')
        plt.legend()
        
        return self._encode_plot()

    def _create_jitter_histogram(self, intervals, message_id):
        """Create histogram for jitter analysis"""
        plt.figure(figsize=(10, 6))
        plt.hist(intervals, bins=min(20, len(intervals)//2), edgecolor='black', alpha=0.7)
        plt.title(f"Jitter Distribution: {message_id}")
        plt.xlabel("Time Interval (seconds)")
        plt.ylabel("Frequency")
        plt.grid(True, alpha=0.3)
        
        # Add statistics
        mean_val = np.mean(intervals)
        std_val = np.std(intervals)
        plt.axvline(mean_val, color='red', linestyle='--', label=f'Mean: {mean_val:.3f}s')
        plt.axvline(mean_val + std_val, color='orange', linestyle='--', label=f'+1σ: {mean_val + std_val:.3f}s')
        plt.axvline(mean_val - std_val, color='orange', linestyle='--', label=f'-1σ: {mean_val - std_val:.3f}s')
        plt.legend()
        
        return self._encode_plot()

    def _create_deviation_plot(self, intervals, message_id):
        """Create plot showing deviations from expected behavior"""
        if len(intervals) < 2:
            return None
            
        plt.figure(figsize=(10, 6))
        expected = np.median(intervals)
        deviations = intervals - expected
        
        colors = ['red' if abs(d) > expected * 0.5 else 'blue' for d in deviations]
        plt.scatter(range(len(deviations)), deviations, c=colors, alpha=0.6)
        plt.title(f"Timing Deviations: {message_id}")
        plt.xlabel("Message Occurrence")
        plt.ylabel("Deviation from Expected (seconds)")
        plt.axhline(y=0, color='black', linestyle='-', alpha=0.5)
        plt.grid(True, alpha=0.3)
        
        # Add tolerance lines
        tolerance = expected * 0.5
        plt.axhline(y=tolerance, color='orange', linestyle='--', alpha=0.7, label='Tolerance')
        plt.axhline(y=-tolerance, color='orange', linestyle='--', alpha=0.7)
        plt.legend()
        
        return self._encode_plot()

    def _encode_plot(self):
        """Encode matplotlib plot to base64 string"""
        buffer = io.BytesIO()
        plt.savefig(buffer, format='png', dpi=100, bbox_inches='tight')
        buffer.seek(0)
        encoded = base64.b64encode(buffer.read()).decode('utf-8')
        plt.close()
        return f"data:image/png;base64,{encoded}"
