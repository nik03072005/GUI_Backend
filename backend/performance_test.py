#!/usr/bin/env python
"""
🚀 ISRO Backend Performance Test Suite
Clean performance monitoring and analysis
"""

import os
import sys
import time
import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from statistics import mean, median

# Django setup
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'backend.settings')
import django
django.setup()

from django.test import TestCase, Client
from django.contrib.auth import get_user_model
from analyzer.models import UploadedLog

User = get_user_model()


class PerformanceMonitor:
    """Clean performance monitoring utility"""
    
    def __init__(self):
        self.results = []
        self.client = Client()
    
    def time_function(self, func, *args, **kwargs):
        """Time a function execution cleanly"""
        start_time = time.perf_counter()
        result = func(*args, **kwargs)
        end_time = time.perf_counter()
        execution_time = (end_time - start_time) * 1000  # Convert to ms
        
        self.results.append({
            'function': func.__name__,
            'time_ms': execution_time,
            'timestamp': time.time()
        })
        
        return result, execution_time
    
    def concurrent_test(self, func, args_list, max_workers=5):
        """Run concurrent performance tests"""
        times = []
        
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            start_time = time.perf_counter()
            
            # Submit all tasks
            futures = [executor.submit(func, *args) for args in args_list]
            
            # Collect results
            for future in as_completed(futures):
                try:
                    result = future.result()
                    times.append(time.perf_counter() - start_time)
                except Exception as e:
                    print(f"❌ Concurrent test failed: {e}")
        
        return {
            'total_requests': len(args_list),
            'mean_time_ms': mean(times) * 1000 if times else 0,
            'median_time_ms': median(times) * 1000 if times else 0,
            'max_time_ms': max(times) * 1000 if times else 0,
            'min_time_ms': min(times) * 1000 if times else 0
        }
    
    def generate_report(self):
        """Generate clean performance report"""
        if not self.results:
            return "No performance data collected"
        
        report = "🎯 PERFORMANCE ANALYSIS REPORT\n"
        report += "=" * 50 + "\n\n"
        
        # Group by function
        functions = {}
        for result in self.results:
            func_name = result['function']
            if func_name not in functions:
                functions[func_name] = []
            functions[func_name].append(result['time_ms'])
        
        # Analyze each function
        for func_name, times in functions.items():
            report += f"📊 {func_name.upper()}\n"
            report += f"   Average: {mean(times):.2f}ms\n"
            report += f"   Median:  {median(times):.2f}ms\n"
            report += f"   Min:     {min(times):.2f}ms\n"
            report += f"   Max:     {max(times):.2f}ms\n"
            report += f"   Calls:   {len(times)}\n\n"
        
        return report


def test_database_performance():
    """Test database query performance"""
    monitor = PerformanceMonitor()
    
    print("🔍 Testing Database Performance...")
    
    # Test user creation
    def create_user():
        return User.objects.create_user(
            username=f"test_{time.time()}",
            email=f"test_{time.time()}@example.com",
            password="testpass123",
            full_name="Test User"
        )
    
    # Test user queries
    def query_users():
        return list(User.objects.filter(is_active=True)[:10])
    
    # Test file upload records
    def query_uploads():
        return list(UploadedLog.objects.select_related('user')[:10])
    
    # Run tests
    _, time1 = monitor.time_function(create_user)
    _, time2 = monitor.time_function(query_users)
    _, time3 = monitor.time_function(query_uploads)
    
    print(f"✅ User Creation: {time1:.2f}ms")
    print(f"✅ User Query: {time2:.2f}ms")
    print(f"✅ Upload Query: {time3:.2f}ms")
    
    return monitor


def test_api_performance():
    """Test API endpoint performance"""
    monitor = PerformanceMonitor()
    
    print("🌐 Testing API Performance...")
    
    # Test home endpoint
    def test_home():
        return monitor.client.get('/')
    
    # Test login endpoint
    def test_login():
        return monitor.client.post('/api/login/', {
            'email': 'test@example.com',
            'password': 'wrongpass'
        })
    
    # Run tests
    _, time1 = monitor.time_function(test_home)
    _, time2 = monitor.time_function(test_login)
    
    print(f"✅ Home Endpoint: {time1:.2f}ms")
    print(f"✅ Login Endpoint: {time2:.2f}ms")
    
    return monitor


def test_concurrent_load():
    """Test concurrent request handling"""
    monitor = PerformanceMonitor()
    
    print("⚡ Testing Concurrent Load...")
    
    def make_request():
        return monitor.client.get('/')
        
    # Test with different concurrency levels
    for workers in [1, 5, 10]:
        args_list = [() for _ in range(20)]  # 20 requests
        results = monitor.concurrent_test(make_request, args_list, workers)
        
        print(f"✅ {workers} workers: {results['mean_time_ms']:.2f}ms avg")
    
    return monitor


def benchmark_vs_baseline():
    """Compare performance against baseline"""
    print("📈 Performance Benchmark")
    print("=" * 30)
    
    # Baseline expectations (ms)
    baselines = {
        'database_query': 50,
        'api_request': 100,
        'file_upload': 500,
        'login_request': 200
    }
    
    # Run actual tests
    db_monitor = test_database_performance()
    api_monitor = test_api_performance()
    
    print("\n📊 PERFORMANCE SUMMARY")
    print("=" * 30)
    
    all_results = db_monitor.results + api_monitor.results
    
    if all_results:
        avg_time = mean([r['time_ms'] for r in all_results])
        print(f"Overall Average: {avg_time:.2f}ms")
        
        if avg_time < 100:
            print("🎯 EXCELLENT - High Performance")
        elif avg_time < 300:
            print("✅ GOOD - Acceptable Performance")
        else:
            print("⚠️  NEEDS OPTIMIZATION")
    
    return all_results


def run_full_performance_suite():
    """Run complete performance test suite"""
    print("🚀 ISRO Backend Performance Test Suite")
    print("=" * 50)
    
    start_time = time.time()
    
    try:
        # Run all performance tests
        results = benchmark_vs_baseline()
        
        # Generate detailed report
        monitor = PerformanceMonitor()
        monitor.results = results
        report = monitor.generate_report()
        
        print("\n" + report)
        
        # Save results to file
        with open('performance_results.json', 'w') as f:
            json.dump({
                'timestamp': time.time(),
                'results': results,
                'summary': {
                    'total_tests': len(results),
                    'duration_seconds': time.time() - start_time
                }
            }, f, indent=2)
        
        print("📁 Results saved to performance_results.json")
        
    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return False
    
    print(f"\n⏱️  Total test time: {time.time() - start_time:.2f}s")
    return True


if __name__ == "__main__":
    success = run_full_performance_suite()
    sys.exit(0 if success else 1)
