#!/usr/bin/env python3
"""
FocusFlow MVP Backend Testing Suite
Testing critical fixes: MongoDB ObjectId serialization and AI priority parsing
"""

import requests
import sys
import json
import time
from datetime import datetime, timezone
from typing import Dict, Any, List

class FocusFlowAPITester:
    def __init__(self, base_url="https://focusflow-78.preview.emergentagent.com"):
        self.base_url = base_url
        self.api_url = f"{base_url}/api"
        self.token = None
        self.user_id = None
        self.tests_run = 0
        self.tests_passed = 0
        self.test_results = []
        self.created_task_ids = []
        
        # Test user credentials
        self.test_email = f"test_user_{datetime.now().strftime('%H%M%S')}@focusflow.test"
        self.test_password = "TestPass123!"
        self.test_name = "Test User"

    def log_test(self, name, success, details="", response_data=None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            status = "✅ PASS"
        else:
            status = "❌ FAIL"
        
        result = {
            "test_name": name,
            "status": "PASS" if success else "FAIL",
            "details": details,
            "response_data": response_data
        }
        self.test_results.append(result)
        print(f"{status} - {name}: {details}")

    def run_test(self, name, method, endpoint, expected_status, data=None, headers=None):
        """Run a single API test"""
        url = f"{self.api_url}/{endpoint}"
        test_headers = {'Content-Type': 'application/json'}
        
        if self.token:
            test_headers['Authorization'] = f'Bearer {self.token}'
        
        if headers:
            test_headers.update(headers)

        try:
            if method == 'GET':
                response = requests.get(url, headers=test_headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=test_headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=test_headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=test_headers, timeout=30)

            success = response.status_code == expected_status
            
            try:
                response_json = response.json()
            except:
                response_json = {"raw_response": response.text}

            details = f"Status: {response.status_code} (expected {expected_status})"
            if not success:
                details += f" | Response: {response.text[:200]}"

            self.log_test(name, success, details, response_json)
            return success, response_json

        except Exception as e:
            self.log_test(name, False, f"Error: {str(e)}")
            return False, {}

    def test_health_check(self):
        """Test health endpoint"""
        print("\n🔍 Testing Health Check...")
        success, response = self.run_test(
            "Health Check",
            "GET",
            "health",
            200
        )
        return success

    def test_user_registration(self):
        """Test user registration"""
        print("\n🔍 Testing User Registration...")
        timestamp = int(datetime.now().timestamp())
        test_user_data = {
            "name": f"Test User {timestamp}",
            "email": f"test{timestamp}@focusflow.com",
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Registration",
            "POST",
            "auth/register",
            200,
            data=test_user_data
        )
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            if 'user' in response:
                self.user_id = response['user'].get('id')
            self.log_test("Token Extraction", True, f"Token received and stored")
        else:
            self.log_test("Token Extraction", False, "No token in registration response")
        
        return success

    def test_user_login(self):
        """Test user login with existing credentials"""
        print("\n🔍 Testing User Login...")
        # Try to login with the same credentials used in registration
        timestamp = int(datetime.now().timestamp())
        login_data = {
            "email": f"test{timestamp}@focusflow.com",
            "password": "TestPass123!"
        }
        
        success, response = self.run_test(
            "User Login",
            "POST",
            "auth/login",
            200,
            data=login_data
        )
        return success

    def test_ai_task_creation(self):
        """Test AI-powered task creation with natural language"""
        print("\n🔍 Testing AI Task Creation...")
        
        # Test natural language task parsing
        ai_task_data = {
            "title": "Finish the quarterly report by tomorrow 2pm - urgent priority",
            "description": "Complete analysis and recommendations"
        }
        
        success, response = self.run_test(
            "AI Task Creation",
            "POST",
            "tasks",
            200,
            data=ai_task_data
        )
        
        if success and 'id' in response:
            self.created_task_ids.append(response['id'])
            # Verify AI parsing worked
            if response.get('priority') == 'urgent':
                self.log_test("AI Priority Parsing", True, "AI correctly identified urgent priority")
            else:
                self.log_test("AI Priority Parsing", False, f"Expected urgent, got {response.get('priority')}")
        
        return success

    def test_simple_task_creation(self):
        """Test simple task creation"""
        print("\n🔍 Testing Simple Task Creation...")
        
        simple_task_data = {
            "title": "Review emails",
            "description": "Check and respond to important emails",
            "estimated_duration": 30
        }
        
        success, response = self.run_test(
            "Simple Task Creation",
            "POST",
            "tasks",
            200,
            data=simple_task_data
        )
        
        if success and 'id' in response:
            self.created_task_ids.append(response['id'])
        
        return success

    def test_get_tasks(self):
        """Test retrieving tasks (with smart scheduling)"""
        print("\n🔍 Testing Get Tasks...")
        
        success, response = self.run_test(
            "Get Tasks",
            "GET",
            "tasks",
            200
        )
        
        if success:
            tasks = response if isinstance(response, list) else []
            self.log_test("Task List Retrieval", True, f"Retrieved {len(tasks)} tasks")
            
            # Verify smart scheduling worked
            if tasks:
                first_task = tasks[0]
                if 'priority' in first_task and 'focus_score' in first_task:
                    self.log_test("Smart Scheduling Data", True, "Tasks contain priority and focus_score")
                else:
                    self.log_test("Smart Scheduling Data", False, "Missing priority or focus_score")
        
        return success

    def test_get_single_task(self):
        """Test retrieving a single task"""
        print("\n🔍 Testing Get Single Task...")
        
        if not self.created_task_ids:
            self.log_test("Get Single Task", False, "No task IDs available for testing")
            return False
        
        task_id = self.created_task_ids[0]
        success, response = self.run_test(
            "Get Single Task",
            "GET",
            f"tasks/{task_id}",
            200
        )
        
        return success

    def test_update_task(self):
        """Test updating a task"""
        print("\n🔍 Testing Task Update...")
        
        if not self.created_task_ids:
            self.log_test("Update Task", False, "No task IDs available for testing")
            return False
        
        task_id = self.created_task_ids[0]
        update_data = {
            "status": "in_progress",
            "priority": "high"
        }
        
        success, response = self.run_test(
            "Update Task",
            "PUT",
            f"tasks/{task_id}",
            200,
            data=update_data
        )
        
        if success:
            if response.get('status') == 'in_progress':
                self.log_test("Task Status Update", True, "Status updated correctly")
            else:
                self.log_test("Task Status Update", False, f"Expected in_progress, got {response.get('status')}")
        
        return success

    def test_focus_session_creation(self):
        """Test creating a focus session"""
        print("\n🔍 Testing Focus Session Creation...")
        
        task_id = self.created_task_ids[0] if self.created_task_ids else None
        
        success, response = self.run_test(
            "Create Focus Session",
            "POST",
            "focus-sessions",
            200,
            data={"task_id": task_id} if task_id else {}
        )
        
        if success and 'id' in response:
            self.created_session_ids.append(response['id'])
            self.log_test("Focus Session ID", True, f"Session created with ID: {response['id']}")
        
        return success

    def test_complete_focus_session(self):
        """Test completing a focus session"""
        print("\n🔍 Testing Focus Session Completion...")
        
        if not self.created_session_ids:
            self.log_test("Complete Focus Session", False, "No session IDs available for testing")
            return False
        
        session_id = self.created_session_ids[0]
        completion_data = {
            "duration_minutes": 25,
            "productivity_score": 0.85
        }
        
        success, response = self.run_test(
            "Complete Focus Session",
            "PUT",
            f"focus-sessions/{session_id}/complete?duration_minutes=25&productivity_score=0.85",
            200
        )
        
        return success

    def test_analytics_focus_patterns(self):
        """Test focus patterns analytics"""
        print("\n🔍 Testing Focus Patterns Analytics...")
        
        success, response = self.run_test(
            "Focus Patterns Analytics",
            "GET",
            "analytics/focus-patterns",
            200
        )
        
        if success:
            expected_keys = ['morning', 'afternoon', 'evening']
            if all(key in response for key in expected_keys):
                self.log_test("Focus Patterns Structure", True, "All time periods present")
            else:
                self.log_test("Focus Patterns Structure", False, f"Missing keys in response: {response}")
        
        return success

    def test_analytics_productivity(self):
        """Test productivity analytics"""
        print("\n🔍 Testing Productivity Analytics...")
        
        success, response = self.run_test(
            "Productivity Analytics",
            "GET",
            "analytics/productivity",
            200
        )
        
        if success:
            expected_keys = ['total_focus_minutes_7d', 'average_productivity_score', 'completed_tasks_7d', 'focus_sessions_count']
            if all(key in response for key in expected_keys):
                self.log_test("Productivity Stats Structure", True, "All required metrics present")
            else:
                self.log_test("Productivity Stats Structure", False, f"Missing keys in response: {response}")
        
        return success

    def test_schedule_optimization(self):
        """Test schedule optimization"""
        print("\n🔍 Testing Schedule Optimization...")
        
        schedule_data = {
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        success, response = self.run_test(
            "Schedule Optimization",
            "POST",
            "schedule/optimize",
            200,
            data=schedule_data
        )
        
        if success:
            expected_keys = ['scheduled_tasks', 'focus_patterns', 'recommendations']
            if all(key in response for key in expected_keys):
                self.log_test("Schedule Optimization Structure", True, "All required fields present")
            else:
                self.log_test("Schedule Optimization Structure", False, f"Missing keys in response: {response}")
        
        return success

    def test_task_deletion(self):
        """Test deleting a task"""
        print("\n🔍 Testing Task Deletion...")
        
        if not self.created_task_ids:
            self.log_test("Delete Task", False, "No task IDs available for testing")
            return False
        
        task_id = self.created_task_ids[-1]  # Delete the last created task
        success, response = self.run_test(
            "Delete Task",
            "DELETE",
            f"tasks/{task_id}",
            200
        )
        
        if success:
            self.created_task_ids.remove(task_id)
        
        return success

    def test_invalid_endpoints(self):
        """Test error handling for invalid endpoints"""
        print("\n🔍 Testing Error Handling...")
        
        # Test invalid task ID
        success, response = self.run_test(
            "Invalid Task ID",
            "GET",
            "tasks/invalid-id-123",
            404
        )
        
        # Test unauthorized access (without token)
        old_token = self.token
        self.token = None
        success2, response2 = self.run_test(
            "Unauthorized Access",
            "GET",
            "tasks",
            401
        )
        self.token = old_token  # Restore token
        
        return success and success2

    def run_all_tests(self):
        """Run all tests in sequence"""
        print("🚀 Starting FocusFlow Backend API Tests...")
        print(f"Testing against: {self.base_url}")
        print("=" * 60)
        
        # Core functionality tests
        tests = [
            self.test_health_check,
            self.test_user_registration,
            self.test_ai_task_creation,
            self.test_simple_task_creation,
            self.test_get_tasks,
            self.test_get_single_task,
            self.test_update_task,
            self.test_focus_session_creation,
            self.test_complete_focus_session,
            self.test_analytics_focus_patterns,
            self.test_analytics_productivity,
            self.test_schedule_optimization,
            self.test_task_deletion,
            self.test_invalid_endpoints
        ]
        
        for test in tests:
            try:
                test()
                time.sleep(0.5)  # Small delay between tests
            except Exception as e:
                self.log_test(test.__name__, False, f"Test execution error: {str(e)}")
        
        self.print_summary()
        return self.tests_passed == self.tests_run

    def print_summary(self):
        """Print test summary"""
        print("\n" + "=" * 60)
        print("📊 TEST SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%" if self.tests_run > 0 else "0%")
        
        # Show failed tests
        failed_tests = [test for test in self.test_results if test['status'] == 'FAIL']
        if failed_tests:
            print(f"\n❌ FAILED TESTS ({len(failed_tests)}):")
            for test in failed_tests:
                print(f"  - {test['test_name']}: {test['details']}")
        
        print("\n✅ PASSED TESTS:")
        passed_tests = [test for test in self.test_results if test['status'] == 'PASS']
        for test in passed_tests:
            print(f"  - {test['test_name']}")

def main():
    """Main test execution"""
    tester = FocusFlowAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n\n💥 Unexpected error: {str(e)}")
        return 1

if __name__ == "__main__":
    sys.exit(main())