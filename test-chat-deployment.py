#!/usr/bin/env python3
"""
Trae AI Chat Assistant Deployment Test Script
Tests the functionality of the deployed chat assistant on Saturn Cloud H100
"""

import requests
import json
import time
import sys
import base64
from io import BytesIO
from PIL import Image, ImageDraw

class ChatDeploymentTester:
    def __init__(self, base_url="http://localhost:8000"):
        self.base_url = base_url.rstrip('/')
        self.session = requests.Session()
        self.test_results = []
        
    def log_test(self, test_name, success, message=""):
        """Log test results"""
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{status} {test_name}: {message}")
        self.test_results.append({
            'test': test_name,
            'success': success,
            'message': message
        })
    
    def test_health_check(self):
        """Test basic health endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/health", timeout=10)
            if response.status_code == 200:
                data = response.json()
                self.log_test("Health Check", True, f"Status: {data.get('status', 'unknown')}")
                return True
            else:
                self.log_test("Health Check", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Health Check", False, str(e))
            return False
    
    def test_chat_endpoint(self):
        """Test basic chat functionality"""
        try:
            payload = {
                "message": "Hello! Can you help me write a Python function?",
                "conversation_id": "test_conversation"
            }
            
            response = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'response' in data and len(data['response']) > 0:
                    self.log_test("Chat Endpoint", True, f"Response length: {len(data['response'])} chars")
                    return True
                else:
                    self.log_test("Chat Endpoint", False, "Empty response")
                    return False
            else:
                self.log_test("Chat Endpoint", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Chat Endpoint", False, str(e))
            return False
    
    def test_coding_assistance(self):
        """Test coding-specific functionality"""
        try:
            payload = {
                "message": "Write a Python function to calculate fibonacci numbers",
                "conversation_id": "test_coding"
            }
            
            response = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=45
            )
            
            if response.status_code == 200:
                data = response.json()
                response_text = data.get('response', '').lower()
                
                # Check if response contains coding-related keywords
                coding_keywords = ['def', 'function', 'python', 'fibonacci', 'return']
                found_keywords = [kw for kw in coding_keywords if kw in response_text]
                
                if len(found_keywords) >= 2:
                    self.log_test("Coding Assistance", True, f"Found keywords: {found_keywords}")
                    return True
                else:
                    self.log_test("Coding Assistance", False, "Response doesn't seem coding-related")
                    return False
            else:
                self.log_test("Coding Assistance", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Coding Assistance", False, str(e))
            return False
    
    def test_conversation_context(self):
        """Test conversation context maintenance"""
        try:
            conversation_id = "test_context"
            
            # First message
            payload1 = {
                "message": "My name is Alice and I'm learning Python",
                "conversation_id": conversation_id
            }
            
            response1 = self.session.post(
                f"{self.base_url}/chat",
                json=payload1,
                timeout=30
            )
            
            if response1.status_code != 200:
                self.log_test("Conversation Context", False, "First message failed")
                return False
            
            time.sleep(1)  # Brief pause
            
            # Second message referencing context
            payload2 = {
                "message": "What's my name?",
                "conversation_id": conversation_id
            }
            
            response2 = self.session.post(
                f"{self.base_url}/chat",
                json=payload2,
                timeout=30
            )
            
            if response2.status_code == 200:
                data = response2.json()
                response_text = data.get('response', '').lower()
                
                if 'alice' in response_text:
                    self.log_test("Conversation Context", True, "Context maintained correctly")
                    return True
                else:
                    self.log_test("Conversation Context", False, "Context not maintained")
                    return False
            else:
                self.log_test("Conversation Context", False, f"Second message failed: HTTP {response2.status_code}")
                return False
        except Exception as e:
            self.log_test("Conversation Context", False, str(e))
            return False
    
    def create_test_image(self):
        """Create a simple test image"""
        img = Image.new('RGB', (200, 100), color='white')
        draw = ImageDraw.Draw(img)
        draw.text((10, 10), "Test Image", fill='black')
        draw.rectangle([50, 30, 150, 80], outline='blue', width=2)
        
        buffer = BytesIO()
        img.save(buffer, format='PNG')
        buffer.seek(0)
        return buffer
    
    def test_image_upload(self):
        """Test image upload functionality"""
        try:
            # Create test image
            image_buffer = self.create_test_image()
            
            files = {
                'file': ('test_image.png', image_buffer, 'image/png')
            }
            data = {
                'conversation_id': 'test_image'
            }
            
            response = self.session.post(
                f"{self.base_url}/upload-image",
                files=files,
                data=data,
                timeout=30
            )
            
            if response.status_code == 200:
                data = response.json()
                if 'image_data' in data:
                    self.log_test("Image Upload", True, "Image processed successfully")
                    return True
                else:
                    self.log_test("Image Upload", False, "No image data in response")
                    return False
            else:
                self.log_test("Image Upload", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Image Upload", False, str(e))
            return False
    
    def test_api_documentation(self):
        """Test API documentation endpoint"""
        try:
            response = self.session.get(f"{self.base_url}/docs", timeout=10)
            if response.status_code == 200:
                self.log_test("API Documentation", True, "Docs accessible")
                return True
            else:
                self.log_test("API Documentation", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("API Documentation", False, str(e))
            return False
    
    def test_static_files(self):
        """Test static file serving"""
        try:
            response = self.session.get(f"{self.base_url}/", timeout=10)
            if response.status_code == 200:
                content = response.text.lower()
                if 'trae ai' in content or 'chat' in content:
                    self.log_test("Static Files", True, "Chat interface accessible")
                    return True
                else:
                    self.log_test("Static Files", False, "Unexpected content")
                    return False
            else:
                self.log_test("Static Files", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Static Files", False, str(e))
            return False
    
    def test_performance(self):
        """Test response time performance"""
        try:
            payload = {
                "message": "What is Python?",
                "conversation_id": "test_performance"
            }
            
            start_time = time.time()
            response = self.session.post(
                f"{self.base_url}/chat",
                json=payload,
                timeout=60
            )
            end_time = time.time()
            
            response_time = end_time - start_time
            
            if response.status_code == 200:
                if response_time < 30:  # Should respond within 30 seconds
                    self.log_test("Performance", True, f"Response time: {response_time:.2f}s")
                    return True
                else:
                    self.log_test("Performance", False, f"Slow response: {response_time:.2f}s")
                    return False
            else:
                self.log_test("Performance", False, f"HTTP {response.status_code}")
                return False
        except Exception as e:
            self.log_test("Performance", False, str(e))
            return False
    
    def run_all_tests(self):
        """Run all tests and return summary"""
        print("🧪 Starting Trae AI Chat Assistant Deployment Tests...\n")
        
        tests = [
            self.test_health_check,
            self.test_api_documentation,
            self.test_static_files,
            self.test_chat_endpoint,
            self.test_coding_assistance,
            self.test_conversation_context,
            self.test_image_upload,
            self.test_performance
        ]
        
        for test in tests:
            try:
                test()
            except Exception as e:
                self.log_test(test.__name__, False, f"Test error: {str(e)}")
            print()  # Add spacing between tests
        
        # Summary
        total_tests = len(self.test_results)
        passed_tests = sum(1 for result in self.test_results if result['success'])
        failed_tests = total_tests - passed_tests
        
        print("\n" + "="*50)
        print("📊 TEST SUMMARY")
        print("="*50)
        print(f"Total Tests: {total_tests}")
        print(f"✅ Passed: {passed_tests}")
        print(f"❌ Failed: {failed_tests}")
        print(f"Success Rate: {(passed_tests/total_tests)*100:.1f}%")
        
        if failed_tests > 0:
            print("\n🔍 Failed Tests:")
            for result in self.test_results:
                if not result['success']:
                    print(f"  - {result['test']}: {result['message']}")
        
        print("\n" + "="*50)
        
        return passed_tests == total_tests

def main():
    """Main test function"""
    import argparse
    
    parser = argparse.ArgumentParser(description='Test Trae AI Chat Assistant deployment')
    parser.add_argument('--url', default='http://localhost:8000', 
                       help='Base URL of the deployed application')
    parser.add_argument('--quick', action='store_true',
                       help='Run only basic tests (faster)')
    
    args = parser.parse_args()
    
    tester = ChatDeploymentTester(args.url)
    
    if args.quick:
        print("🚀 Running quick tests...\n")
        success = (tester.test_health_check() and 
                  tester.test_chat_endpoint() and 
                  tester.test_static_files())
        
        if success:
            print("\n✅ Quick tests passed! Deployment appears to be working.")
        else:
            print("\n❌ Quick tests failed. Check the deployment.")
            sys.exit(1)
    else:
        success = tester.run_all_tests()
        
        if success:
            print("\n🎉 All tests passed! Deployment is ready for use.")
        else:
            print("\n⚠️  Some tests failed. Review the issues above.")
            sys.exit(1)

if __name__ == "__main__":
    main()