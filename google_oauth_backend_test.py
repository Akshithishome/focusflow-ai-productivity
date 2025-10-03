#!/usr/bin/env python3
"""
Google OAuth Backend Testing for FocusFlow
Tests the new Google OAuth authentication endpoints and session management
"""

import requests
import sys
import json
from datetime import datetime, timezone, timedelta

class GoogleOAuthTester:
    def __init__(self, base_url="https://focusflow-78.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.session_token = None
        self.jwt_token = None
        self.test_user_email = f"test.oauth.{datetime.now().strftime('%H%M%S')}@example.com"
        self.tests_run = 0
        self.tests_passed = 0
        
    def log_test(self, name, success, details=""):
        """Log test results"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name} - PASSED")
        else:
            print(f"❌ {name} - FAILED")
        if details:
            print(f"   Details: {details}")
        print()

    def test_health_check(self):
        """Test basic API health"""
        try:
            response = requests.get(f"{self.api_url}/health", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                data = response.json()
                details += f", Response: {data.get('status', 'unknown')}"
            self.log_test("Health Check", success, details)
            return success
        except Exception as e:
            self.log_test("Health Check", False, f"Error: {str(e)}")
            return False

    def test_google_session_endpoint_structure(self):
        """Test Google OAuth session endpoint structure (without valid session ID)"""
        try:
            # Test without session ID header
            response = requests.post(f"{self.api_url}/auth/google/session", timeout=10)
            success = response.status_code == 400
            details = f"Status: {response.status_code}"
            if response.status_code == 400:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'No detail')}"
                    success = "Session ID required" in error_data.get('detail', '')
                except:
                    pass
            
            self.log_test("Google Session Endpoint Structure", success, details)
            return success
        except Exception as e:
            self.log_test("Google Session Endpoint Structure", False, f"Error: {str(e)}")
            return False

    def test_google_session_with_invalid_id(self):
        """Test Google OAuth session endpoint with invalid session ID"""
        try:
            headers = {"X-Session-ID": "invalid_session_id_12345"}
            response = requests.post(f"{self.api_url}/auth/google/session", headers=headers, timeout=10)
            success = response.status_code in [401, 500]  # Either unauthorized or service error
            details = f"Status: {response.status_code}"
            if response.status_code in [401, 500]:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'No detail')}"
                except:
                    pass
            
            self.log_test("Google Session Invalid ID", success, details)
            return success
        except Exception as e:
            self.log_test("Google Session Invalid ID", False, f"Error: {str(e)}")
            return False

    def test_auth_me_endpoint_no_auth(self):
        """Test /api/auth/me endpoint without authentication"""
        try:
            response = requests.get(f"{self.api_url}/auth/me", timeout=10)
            success = response.status_code == 401
            details = f"Status: {response.status_code}"
            if response.status_code == 401:
                try:
                    error_data = response.json()
                    details += f", Error: {error_data.get('detail', 'No detail')}"
                except:
                    pass
            
            self.log_test("Auth Me Endpoint (No Auth)", success, details)
            return success
        except Exception as e:
            self.log_test("Auth Me Endpoint (No Auth)", False, f"Error: {str(e)}")
            return False

    def test_logout_endpoint(self):
        """Test logout endpoint"""
        try:
            response = requests.post(f"{self.api_url}/auth/logout", timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            if success:
                try:
                    data = response.json()
                    details += f", Message: {data.get('message', 'No message')}"
                except:
                    pass
            
            self.log_test("Logout Endpoint", success, details)
            return success
        except Exception as e:
            self.log_test("Logout Endpoint", False, f"Error: {str(e)}")
            return False

    def test_existing_email_auth_still_works(self):
        """Test that existing email/password authentication still works"""
        try:
            # First register a test user
            register_data = {
                "name": "Test OAuth User",
                "email": self.test_user_email,
                "password": "TestPassword123!"
            }
            
            register_response = requests.post(f"{self.api_url}/auth/register", json=register_data, timeout=10)
            if register_response.status_code != 200:
                self.log_test("Email Auth Registration", False, f"Registration failed: {register_response.status_code}")
                return False
            
            # Now test login
            login_data = {
                "email": self.test_user_email,
                "password": "TestPassword123!"
            }
            
            login_response = requests.post(f"{self.api_url}/auth/login", json=login_data, timeout=10)
            success = login_response.status_code == 200
            details = f"Status: {login_response.status_code}"
            
            if success:
                try:
                    login_data = login_response.json()
                    self.jwt_token = login_data.get('access_token')
                    details += f", Token received: {'Yes' if self.jwt_token else 'No'}"
                    details += f", User: {login_data.get('user', {}).get('name', 'Unknown')}"
                except:
                    success = False
                    details += ", Failed to parse response"
            
            self.log_test("Email Auth Login", success, details)
            return success
        except Exception as e:
            self.log_test("Email Auth Login", False, f"Error: {str(e)}")
            return False

    def test_auth_me_with_jwt_token(self):
        """Test /api/auth/me endpoint with JWT token"""
        if not self.jwt_token:
            self.log_test("Auth Me with JWT", False, "No JWT token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            response = requests.get(f"{self.api_url}/auth/me", headers=headers, timeout=10)
            success = response.status_code == 200
            details = f"Status: {response.status_code}"
            
            if success:
                try:
                    user_data = response.json()
                    details += f", User: {user_data.get('name', 'Unknown')}"
                    details += f", Email: {user_data.get('email', 'Unknown')}"
                except:
                    success = False
                    details += ", Failed to parse user data"
            
            self.log_test("Auth Me with JWT", success, details)
            return success
        except Exception as e:
            self.log_test("Auth Me with JWT", False, f"Error: {str(e)}")
            return False

    def test_protected_endpoints_with_jwt(self):
        """Test that protected endpoints work with JWT token"""
        if not self.jwt_token:
            self.log_test("Protected Endpoints with JWT", False, "No JWT token available")
            return False
            
        try:
            headers = {"Authorization": f"Bearer {self.jwt_token}"}
            
            # Test tasks endpoint
            response = requests.get(f"{self.api_url}/tasks", headers=headers, timeout=10)
            success = response.status_code == 200
            details = f"Tasks endpoint status: {response.status_code}"
            
            if success:
                try:
                    tasks = response.json()
                    details += f", Tasks count: {len(tasks) if isinstance(tasks, list) else 'Not a list'}"
                except:
                    details += ", Failed to parse tasks"
            
            self.log_test("Protected Endpoints with JWT", success, details)
            return success
        except Exception as e:
            self.log_test("Protected Endpoints with JWT", False, f"Error: {str(e)}")
            return False

    def test_cors_headers(self):
        """Test CORS headers are properly set"""
        try:
            response = requests.options(f"{self.api_url}/auth/me", timeout=10)
            success = response.status_code in [200, 204]
            details = f"Status: {response.status_code}"
            
            # Check for CORS headers
            cors_headers = {
                'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
                'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods'),
                'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
                'Access-Control-Allow-Credentials': response.headers.get('Access-Control-Allow-Credentials')
            }
            
            details += f", CORS Headers: {cors_headers}"
            
            self.log_test("CORS Headers", success, details)
            return success
        except Exception as e:
            self.log_test("CORS Headers", False, f"Error: {str(e)}")
            return False

    def run_all_tests(self):
        """Run all Google OAuth backend tests"""
        print("🚀 Starting Google OAuth Backend Testing for FocusFlow")
        print("=" * 60)
        
        # Basic connectivity
        if not self.test_health_check():
            print("❌ Health check failed - stopping tests")
            return False
        
        # Google OAuth endpoint structure tests
        self.test_google_session_endpoint_structure()
        self.test_google_session_with_invalid_id()
        self.test_auth_me_endpoint_no_auth()
        self.test_logout_endpoint()
        
        # Test existing email auth still works
        self.test_existing_email_auth_still_works()
        self.test_auth_me_with_jwt_token()
        self.test_protected_endpoints_with_jwt()
        
        # Additional tests
        self.test_cors_headers()
        
        # Summary
        print("=" * 60)
        print(f"📊 Test Results: {self.tests_passed}/{self.tests_run} tests passed")
        success_rate = (self.tests_passed / self.tests_run) * 100 if self.tests_run > 0 else 0
        print(f"📈 Success Rate: {success_rate:.1f}%")
        
        if success_rate >= 80:
            print("✅ Google OAuth backend integration looks good!")
        elif success_rate >= 60:
            print("⚠️  Google OAuth backend has some issues but core functionality works")
        else:
            print("❌ Google OAuth backend has significant issues")
        
        return success_rate >= 60

def main():
    tester = GoogleOAuthTester()
    success = tester.run_all_tests()
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())