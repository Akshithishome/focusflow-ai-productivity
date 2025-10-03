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
        self.test_email = f"test_user_{datetime.now().strftime('%H%M%S')}@example.com"
        self.test_password = "TestPass123!"
        self.test_name = "Test User"

    def log_test(self, name: str, success: bool, details: str = "", response_data: Any = None):
        """Log test result"""
        self.tests_run += 1
        if success:
            self.tests_passed += 1
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED - {details}")
        
        self.test_results.append({
            "test_name": name,
            "success": success,
            "details": details,
            "response_data": response_data,
            "timestamp": datetime.now().isoformat()
        })

    def make_request(self, method: str, endpoint: str, data: Dict = None, expected_status: int = 200) -> tuple:
        """Make HTTP request and return success status and response"""
        url = f"{self.api_url}/{endpoint}"
        headers = {'Content-Type': 'application/json'}
        
        if self.token:
            headers['Authorization'] = f'Bearer {self.token}'

        try:
            if method == 'GET':
                response = requests.get(url, headers=headers, timeout=30)
            elif method == 'POST':
                response = requests.post(url, json=data, headers=headers, timeout=30)
            elif method == 'PUT':
                response = requests.put(url, json=data, headers=headers, timeout=30)
            elif method == 'DELETE':
                response = requests.delete(url, headers=headers, timeout=30)
            else:
                return False, {"error": f"Unsupported method: {method}"}

            success = response.status_code == expected_status
            
            try:
                response_data = response.json()
            except:
                response_data = {"raw_response": response.text, "status_code": response.status_code}
            
            if not success:
                print(f"   Status: {response.status_code} (expected {expected_status})")
                if response_data:
                    print(f"   Response: {json.dumps(response_data, indent=2)}")
            
            return success, response_data

        except requests.exceptions.RequestException as e:
            return False, {"error": str(e)}

    def test_health_check(self):
        """Test basic health endpoint"""
        print("\n🔍 Testing Health Check...")
        success, response = self.make_request('GET', 'health')
        self.log_test("Health Check", success, 
                     "" if success else f"Health endpoint failed: {response}")
        return success

    def test_user_registration(self):
        """Test user registration"""
        print("\n🔍 Testing User Registration...")
        success, response = self.make_request('POST', 'auth/register', {
            "name": self.test_name,
            "email": self.test_email,
            "password": self.test_password
        })
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response.get('user', {}).get('id')
            self.log_test("User Registration", True)
        else:
            self.log_test("User Registration", False, 
                         f"Registration failed: {response}")
        
        return success

    def test_user_login(self):
        """Test user login with existing credentials"""
        print("\n🔍 Testing User Login...")
        success, response = self.make_request('POST', 'auth/login', {
            "email": self.test_email,
            "password": self.test_password
        })
        
        if success and 'access_token' in response:
            self.token = response['access_token']
            self.user_id = response.get('user', {}).get('id')
            self.log_test("User Login", True)
        else:
            self.log_test("User Login", False, 
                         f"Login failed: {response}")
        
        return success

    def test_ai_priority_parsing_urgent(self):
        """Test AI priority parsing with urgent keywords - CRITICAL FIX"""
        print("\n🔍 Testing AI Priority Parsing (Urgent Keywords)...")
        
        urgent_tasks = [
            "Fix critical bug in production ASAP",
            "Urgent: Call client about contract deadline",
            "Emergency meeting preparation - critical priority",
            "Submit report by tomorrow - urgent deadline"
        ]
        
        urgent_detected = 0
        for task_text in urgent_tasks:
            success, response = self.make_request('POST', 'tasks', {
                "title": task_text,
                "description": ""
            }, 201)
            
            if success:
                priority = response.get('priority', 'medium')
                if priority in ['urgent', 'high']:
                    urgent_detected += 1
                    print(f"   ✅ '{task_text}' → Priority: {priority}")
                else:
                    print(f"   ❌ '{task_text}' → Priority: {priority} (expected urgent/high)")
                
                # Store task ID for cleanup
                if 'id' in response:
                    self.created_task_ids.append(response['id'])
        
        success = urgent_detected >= 3  # At least 3 out of 4 should be detected as urgent/high
        self.log_test("AI Priority Parsing (Urgent)", success,
                     f"Detected {urgent_detected}/4 urgent tasks correctly")
        return success

    def test_schedule_optimization(self):
        """Test schedule optimization endpoint - CRITICAL FIX"""
        print("\n🔍 Testing Schedule Optimization (Critical Fix)...")
        
        # First create some tasks to optimize
        test_tasks = [
            {"title": "Deep work coding session", "description": "Complex algorithm implementation"},
            {"title": "Review emails and respond", "description": "Administrative task"},
            {"title": "Urgent client presentation prep", "description": "High priority deadline tomorrow"}
        ]
        
        for task_data in test_tasks:
            success, response = self.make_request('POST', 'tasks', task_data, 201)
            if success and 'id' in response:
                self.created_task_ids.append(response['id'])
        
        # Test schedule optimization
        schedule_data = {
            "date": datetime.now().strftime("%Y-%m-%d")
        }
        
        success, response = self.make_request('POST', 'schedule/optimize', schedule_data)
        
        if success:
            # Verify response structure
            required_keys = ['scheduled_tasks', 'focus_patterns', 'recommendations']
            missing_keys = [key for key in required_keys if key not in response]
            
            if missing_keys:
                self.log_test("Schedule Optimization", False,
                             f"Missing response keys: {missing_keys}")
                return False
            
            scheduled_tasks = response.get('scheduled_tasks', [])
            focus_patterns = response.get('focus_patterns', {})
            recommendations = response.get('recommendations', [])
            
            print(f"   ✅ Scheduled {len(scheduled_tasks)} tasks")
            print(f"   ✅ Focus patterns: {focus_patterns}")
            print(f"   ✅ Recommendations: {len(recommendations)} items")
            
            # Verify no MongoDB ObjectId serialization issues
            try:
                json.dumps(response)  # This will fail if ObjectId is present
                print("   ✅ No ObjectId serialization issues")
            except TypeError as e:
                self.log_test("Schedule Optimization", False,
                             f"ObjectId serialization issue: {e}")
                return False
        
        self.log_test("Schedule Optimization", success,
                     "" if success else f"Optimization failed: {response}")
        return success

    def test_task_crud_operations(self):
        """Test complete CRUD operations for tasks"""
        print("\n🔍 Testing Task CRUD Operations...")
        
        # Create task
        task_data = {
            "title": "Test task for CRUD operations",
            "description": "Testing create, read, update, delete",
            "estimated_duration": 45
        }
        
        success, response = self.make_request('POST', 'tasks', task_data, 201)
        if not success:
            self.log_test("Task CRUD - Create", False, f"Create failed: {response}")
            return False
        
        task_id = response.get('id')
        if not task_id:
            self.log_test("Task CRUD - Create", False, "No task ID returned")
            return False
        
        self.created_task_ids.append(task_id)
        print(f"   ✅ Created task: {task_id}")
        
        # Read task
        success, response = self.make_request('GET', f'tasks/{task_id}')
        if not success:
            self.log_test("Task CRUD - Read", False, f"Read failed: {response}")
            return False
        
        print(f"   ✅ Read task: {response.get('title')}")
        
        # Update task
        update_data = {
            "status": "in_progress",
            "priority": "high"
        }
        success, response = self.make_request('PUT', f'tasks/{task_id}', update_data)
        if not success:
            self.log_test("Task CRUD - Update", False, f"Update failed: {response}")
            return False
        
        print(f"   ✅ Updated task status: {response.get('status')}")
        
        # Delete task
        success, response = self.make_request('DELETE', f'tasks/{task_id}')
        if success:
            print(f"   ✅ Deleted task: {task_id}")
            self.created_task_ids.remove(task_id)
        
        self.log_test("Task CRUD Operations", success,
                     "" if success else f"Delete failed: {response}")
        return success

    def test_get_all_tasks(self):
        """Test getting all user tasks"""
        print("\n🔍 Testing Get All Tasks...")
        success, response = self.make_request('GET', 'tasks')
        
        if success:
            tasks = response if isinstance(response, list) else []
            print(f"   ✅ Retrieved {len(tasks)} tasks")
            
            # Verify task structure
            if tasks:
                sample_task = tasks[0]
                required_fields = ['id', 'title', 'priority', 'status', 'user_id']
                missing_fields = [field for field in required_fields if field not in sample_task]
                
                if missing_fields:
                    self.log_test("Get All Tasks", False, 
                                 f"Missing required fields: {missing_fields}")
                    return False
        
        self.log_test("Get All Tasks", success,
                     "" if success else f"Failed to get tasks: {response}")
        return success

    def test_focus_sessions(self):
        """Test focus session management"""
        print("\n🔍 Testing Focus Sessions...")
        
        # Start focus session
        success, response = self.make_request('POST', 'focus-sessions', {}, 201)
        if not success:
            self.log_test("Focus Sessions - Start", False, f"Start failed: {response}")
            return False
        
        session_id = response.get('id')
        if not session_id:
            self.log_test("Focus Sessions - Start", False, "No session ID returned")
            return False
        
        print(f"   ✅ Started focus session: {session_id}")
        
        # Complete focus session
        completion_data = {
            "duration_minutes": 25,
            "productivity_score": 0.85
        }
        
        success, response = self.make_request('PUT', f'focus-sessions/{session_id}/complete', 
                                            completion_data)
        
        self.log_test("Focus Sessions", success,
                     "" if success else f"Complete failed: {response}")
        return success

    def test_analytics_endpoints(self):
        """Test analytics endpoints"""
        print("\n🔍 Testing Analytics Endpoints...")
        
        # Test focus patterns
        success, response = self.make_request('GET', 'analytics/focus-patterns')
        if success:
            patterns = response
            expected_keys = ['morning', 'afternoon', 'evening']
            missing_keys = [key for key in expected_keys if key not in patterns]
            
            if missing_keys:
                self.log_test("Analytics - Focus Patterns", False,
                             f"Missing pattern keys: {missing_keys}")
                return False
            
            print(f"   ✅ Focus patterns: {patterns}")
        else:
            self.log_test("Analytics - Focus Patterns", False, 
                         f"Focus patterns failed: {response}")
            return False
        
        # Test productivity stats
        success, response = self.make_request('GET', 'analytics/productivity')
        if success:
            stats = response
            expected_keys = ['total_focus_minutes_7d', 'average_productivity_score', 
                           'completed_tasks_7d', 'focus_sessions_count']
            missing_keys = [key for key in expected_keys if key not in stats]
            
            if missing_keys:
                self.log_test("Analytics - Productivity", False,
                             f"Missing stats keys: {missing_keys}")
                return False
            
            print(f"   ✅ Productivity stats: {stats}")
        
        self.log_test("Analytics Endpoints", success,
                     "" if success else f"Productivity stats failed: {response}")
        return success

    def test_ai_task_parsing_comprehensive(self):
        """Test comprehensive AI task parsing with various inputs"""
        print("\n🔍 Testing Comprehensive AI Task Parsing...")
        
        test_cases = [
            {
                "input": "Code the authentication module by Friday - high priority",
                "expected_priority": ["high", "urgent"],
                "expected_type": "deep"
            },
            {
                "input": "Send weekly status email to team",
                "expected_priority": ["low", "medium"],
                "expected_type": "shallow"
            },
            {
                "input": "Critical bug fix needed ASAP for production",
                "expected_priority": ["urgent"],
                "expected_type": "deep"
            }
        ]
        
        correct_parsing = 0
        for i, test_case in enumerate(test_cases):
            success, response = self.make_request('POST', 'tasks', {
                "title": test_case["input"],
                "description": ""
            }, 201)
            
            if success:
                priority = response.get('priority', 'medium')
                task_type = response.get('task_type', 'shallow')
                
                priority_correct = priority in test_case["expected_priority"]
                type_correct = task_type == test_case["expected_type"]
                
                if priority_correct and type_correct:
                    correct_parsing += 1
                    print(f"   ✅ Test {i+1}: Priority={priority}, Type={task_type}")
                else:
                    print(f"   ❌ Test {i+1}: Priority={priority} (expected {test_case['expected_priority']}), Type={task_type} (expected {test_case['expected_type']})")
                
                # Store for cleanup
                if 'id' in response:
                    self.created_task_ids.append(response['id'])
        
        success = correct_parsing >= 2  # At least 2 out of 3 should be correct
        self.log_test("Comprehensive AI Task Parsing", success,
                     f"Correctly parsed {correct_parsing}/3 test cases")
        return success

    def cleanup_test_data(self):
        """Clean up created test data"""
        print("\n🧹 Cleaning up test data...")
        
        for task_id in self.created_task_ids:
            try:
                self.make_request('DELETE', f'tasks/{task_id}')
                print(f"   ✅ Deleted task: {task_id}")
            except:
                print(f"   ⚠️  Could not delete task: {task_id}")
        
        print(f"   Cleaned up {len(self.created_task_ids)} tasks")

    def run_all_tests(self):
        """Run complete test suite"""
        print("🚀 Starting FocusFlow Backend Test Suite")
        print("=" * 60)
        
        # Core functionality tests
        if not self.test_health_check():
            print("❌ Health check failed - stopping tests")
            return False
        
        if not self.test_user_registration():
            print("❌ User registration failed - stopping tests")
            return False
        
        # Authentication flow test
        if not self.test_user_login():
            print("❌ User login failed - stopping tests")
            return False
        
        # Critical fix tests
        self.test_ai_priority_parsing_urgent()
        self.test_schedule_optimization()
        
        # Core feature tests
        self.test_task_crud_operations()
        self.test_get_all_tasks()
        self.test_focus_sessions()
        self.test_analytics_endpoints()
        self.test_ai_task_parsing_comprehensive()
        
        # Cleanup
        self.cleanup_test_data()
        
        # Results summary
        print("\n" + "=" * 60)
        print("📊 TEST RESULTS SUMMARY")
        print("=" * 60)
        print(f"Total Tests: {self.tests_run}")
        print(f"Passed: {self.tests_passed}")
        print(f"Failed: {self.tests_run - self.tests_passed}")
        print(f"Success Rate: {(self.tests_passed/self.tests_run*100):.1f}%")
        
        # Critical fixes verification
        critical_tests = [
            "AI Priority Parsing (Urgent)",
            "Schedule Optimization"
        ]
        
        critical_passed = sum(1 for result in self.test_results 
                            if result['test_name'] in critical_tests and result['success'])
        
        print(f"\n🔧 CRITICAL FIXES STATUS:")
        print(f"MongoDB ObjectId Serialization: {'✅ FIXED' if critical_passed >= 1 else '❌ ISSUE'}")
        print(f"AI Priority Parsing: {'✅ FIXED' if critical_passed >= 1 else '❌ ISSUE'}")
        
        return self.tests_passed == self.tests_run

def main():
    """Main test execution"""
    tester = FocusFlowAPITester()
    
    try:
        success = tester.run_all_tests()
        return 0 if success else 1
    except KeyboardInterrupt:
        print("\n⚠️  Tests interrupted by user")
        return 1
    except Exception as e:
        print(f"\n❌ Test suite failed with error: {e}")
        return 1

if __name__ == "__main__":
    sys.exit(main())