#!/usr/bin/env python3
"""
FocusFlow Critical Fixes Verification
Testing: 1) MongoDB ObjectId serialization, 2) AI priority parsing accuracy
"""

import requests
import json
import time
from datetime import datetime

class CriticalFixesTester:
    def __init__(self):
        self.base_url = "https://focusflow-78.preview.emergentagent.com"
        self.api_url = f"{self.base_url}/api"
        self.token = None
        self.test_email = f"critical_test_{datetime.now().strftime('%H%M%S')}@example.com"
        self.test_password = "TestPass123!"
        self.created_task_ids = []

    def setup_auth(self):
        """Setup authentication"""
        print("🔐 Setting up authentication...")
        
        # Register user
        response = requests.post(f"{self.api_url}/auth/register", json={
            "name": "Critical Test User",
            "email": self.test_email,
            "password": self.test_password
        })
        
        if response.status_code == 200:
            self.token = response.json()['access_token']
            print("✅ Authentication setup successful")
            return True
        else:
            print(f"❌ Authentication failed: {response.text}")
            return False

    def test_mongodb_objectid_serialization(self):
        """Test MongoDB ObjectId serialization fix in schedule optimization"""
        print("\n🔧 Testing MongoDB ObjectId Serialization Fix...")
        
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        # Create some test tasks first
        test_tasks = [
            {"title": "Deep work task", "description": "Complex coding task"},
            {"title": "Urgent client call", "description": "High priority call"},
            {"title": "Email review", "description": "Administrative task"}
        ]
        
        for task in test_tasks:
            response = requests.post(f"{self.api_url}/tasks", json=task, headers=headers)
            if response.status_code == 200:
                task_id = response.json().get('id')
                if task_id:
                    self.created_task_ids.append(task_id)
        
        print(f"   Created {len(self.created_task_ids)} test tasks")
        
        # Test schedule optimization
        schedule_data = {"date": datetime.now().strftime("%Y-%m-%d")}
        response = requests.post(f"{self.api_url}/schedule/optimize", json=schedule_data, headers=headers)
        
        if response.status_code == 200:
            try:
                data = response.json()
                
                # Verify response structure
                required_keys = ['scheduled_tasks', 'focus_patterns', 'recommendations']
                missing_keys = [key for key in required_keys if key not in data]
                
                if missing_keys:
                    print(f"   ❌ Missing response keys: {missing_keys}")
                    return False
                
                # Test JSON serialization (this would fail if ObjectId is present)
                json_str = json.dumps(data)
                print(f"   ✅ JSON serialization successful ({len(json_str)} chars)")
                
                scheduled_tasks = data.get('scheduled_tasks', [])
                print(f"   ✅ Scheduled {len(scheduled_tasks)} tasks without ObjectId issues")
                
                # Verify task structure
                if scheduled_tasks:
                    sample_task = scheduled_tasks[0]
                    if '_id' in sample_task:
                        print("   ❌ Found MongoDB _id field in response")
                        return False
                    else:
                        print("   ✅ No MongoDB _id fields found in response")
                
                print("   ✅ MongoDB ObjectId serialization fix VERIFIED")
                return True
                
            except json.JSONDecodeError as e:
                print(f"   ❌ JSON serialization failed: {e}")
                return False
            except Exception as e:
                print(f"   ❌ Unexpected error: {e}")
                return False
        else:
            print(f"   ❌ Schedule optimization failed: {response.status_code} - {response.text}")
            return False

    def test_ai_priority_parsing_accuracy(self):
        """Test AI priority parsing accuracy improvements"""
        print("\n🧠 Testing AI Priority Parsing Accuracy...")
        
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        # Test cases with expected priorities
        test_cases = [
            {
                "input": "Fix critical production bug ASAP",
                "expected_priorities": ["urgent", "high"],
                "description": "Critical/ASAP keywords"
            },
            {
                "input": "Emergency meeting preparation needed urgently",
                "expected_priorities": ["urgent"],
                "description": "Emergency/urgent keywords"
            },
            {
                "input": "Important client presentation by tomorrow deadline",
                "expected_priorities": ["high", "urgent"],
                "description": "Important/deadline keywords"
            },
            {
                "input": "Review weekly reports when possible",
                "expected_priorities": ["low", "medium"],
                "description": "Low priority indicator"
            }
        ]
        
        correct_parsing = 0
        total_tests = len(test_cases)
        
        for i, test_case in enumerate(test_cases, 1):
            print(f"\n   Test {i}: {test_case['description']}")
            print(f"   Input: '{test_case['input']}'")
            
            response = requests.post(f"{self.api_url}/tasks", 
                                   json={"title": test_case["input"], "description": ""}, 
                                   headers=headers)
            
            if response.status_code == 200:
                task_data = response.json()
                actual_priority = task_data.get('priority', 'medium')
                task_type = task_data.get('task_type', 'shallow')
                focus_score = task_data.get('focus_score', 0.5)
                
                print(f"   Result: Priority={actual_priority}, Type={task_type}, Focus={focus_score}")
                
                if actual_priority in test_case["expected_priorities"]:
                    print(f"   ✅ Priority parsing CORRECT")
                    correct_parsing += 1
                else:
                    print(f"   ❌ Priority parsing INCORRECT (expected {test_case['expected_priorities']})")
                
                # Store for cleanup
                if 'id' in task_data:
                    self.created_task_ids.append(task_data['id'])
                    
            elif response.status_code == 500:
                print(f"   ⚠️  Server error (500) - AI service may be temporarily unavailable")
            else:
                print(f"   ❌ Request failed: {response.status_code} - {response.text}")
        
        accuracy = (correct_parsing / total_tests) * 100
        print(f"\n   📊 AI Priority Parsing Accuracy: {correct_parsing}/{total_tests} ({accuracy:.1f}%)")
        
        if accuracy >= 75:  # 75% accuracy threshold
            print("   ✅ AI Priority Parsing accuracy fix VERIFIED")
            return True
        else:
            print("   ❌ AI Priority Parsing accuracy needs improvement")
            return False

    def test_task_creation_basic(self):
        """Test basic task creation to ensure API is working"""
        print("\n📝 Testing Basic Task Creation...")
        
        headers = {'Authorization': f'Bearer {self.token}', 'Content-Type': 'application/json'}
        
        simple_task = {
            "title": "Simple test task",
            "description": "Basic functionality test",
            "estimated_duration": 30
        }
        
        response = requests.post(f"{self.api_url}/tasks", json=simple_task, headers=headers)
        
        if response.status_code == 200:
            task_data = response.json()
            print(f"   ✅ Task created: {task_data.get('title')}")
            print(f"   ✅ Task ID: {task_data.get('id')}")
            
            if 'id' in task_data:
                self.created_task_ids.append(task_data['id'])
            
            return True
        else:
            print(f"   ❌ Task creation failed: {response.status_code} - {response.text}")
            return False

    def cleanup(self):
        """Clean up test data"""
        print(f"\n🧹 Cleaning up {len(self.created_task_ids)} test tasks...")
        
        headers = {'Authorization': f'Bearer {self.token}'}
        
        for task_id in self.created_task_ids:
            try:
                response = requests.delete(f"{self.api_url}/tasks/{task_id}", headers=headers)
                if response.status_code == 200:
                    print(f"   ✅ Deleted task: {task_id}")
                else:
                    print(f"   ⚠️  Could not delete task: {task_id}")
            except:
                print(f"   ⚠️  Error deleting task: {task_id}")

    def run_tests(self):
        """Run all critical fix tests"""
        print("🚀 FocusFlow Critical Fixes Verification")
        print("=" * 60)
        
        if not self.setup_auth():
            return False
        
        # Test basic functionality first
        basic_test = self.test_task_creation_basic()
        
        # Test critical fixes
        objectid_fix = self.test_mongodb_objectid_serialization()
        ai_parsing_fix = self.test_ai_priority_parsing_accuracy()
        
        # Cleanup
        self.cleanup()
        
        # Results
        print("\n" + "=" * 60)
        print("🔧 CRITICAL FIXES VERIFICATION RESULTS")
        print("=" * 60)
        
        print(f"Basic Task Creation: {'✅ PASS' if basic_test else '❌ FAIL'}")
        print(f"MongoDB ObjectId Serialization Fix: {'✅ VERIFIED' if objectid_fix else '❌ ISSUE'}")
        print(f"AI Priority Parsing Accuracy Fix: {'✅ VERIFIED' if ai_parsing_fix else '❌ ISSUE'}")
        
        all_passed = basic_test and objectid_fix and ai_parsing_fix
        
        if all_passed:
            print("\n🎉 ALL CRITICAL FIXES VERIFIED SUCCESSFULLY!")
        else:
            print("\n⚠️  Some critical fixes need attention")
        
        return all_passed

def main():
    tester = CriticalFixesTester()
    success = tester.run_tests()
    return 0 if success else 1

if __name__ == "__main__":
    exit(main())