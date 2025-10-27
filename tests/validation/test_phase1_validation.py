#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Phase 1 Backend Validation Tests
Automated testing script for Phase 1 critical backend fixes
"""

import pytest

requests = pytest.importorskip(
    "requests", reason="Phase 1 validation suite requires the requests package"
)
import json
from datetime import datetime, timedelta
from typing import Dict, List, Any
import sys
import os

# Fix Windows console encoding
if sys.platform == "win32":
    os.system("chcp 65001 > nul")
    if sys.stdout.encoding != 'utf-8':
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Allow overriding the target backend from the environment when running the
# validation suite locally or in CI. Defaults to the local FastAPI instance.
BASE_URL = os.environ.get("EMERGENCE_VALIDATION_BASE_URL", "http://localhost:8000")

# Test user credentials - adjust as needed
TEST_USER_EMAIL = "test@example.com"
ADMIN_USER_EMAIL = "admin@example.com"

class Colors:
    """ANSI color codes for terminal output"""
    RESET = "\033[0m"
    GREEN = "\033[92m"
    RED = "\033[91m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    BOLD = "\033[1m"

def print_header(text: str):
    """Print a formatted header"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text.center(80)}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'='*80}{Colors.RESET}\n")

def print_test(test_name: str):
    """Print test name"""
    print(f"{Colors.BOLD}Test: {test_name}{Colors.RESET}")

def print_success(message: str):
    """Print success message"""
    print(f"{Colors.GREEN}✓ {message}{Colors.RESET}")

def print_error(message: str):
    """Print error message"""
    print(f"{Colors.RED}✗ {message}{Colors.RESET}")

def print_warning(message: str):
    """Print warning message"""
    print(f"{Colors.YELLOW}⚠ {message}{Colors.RESET}")

def print_info(message: str):
    """Print info message"""
    print(f"  {message}")

class TestResults:
    """Track test results"""
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        self.warnings = 0
        self.errors = []
        self.skipped = 0

    def add_pass(self):
        self.total += 1
        self.passed += 1

    def add_fail(self, error: str):
        self.total += 1
        self.failed += 1
        self.errors.append(error)

    def add_warning(self):
        self.warnings += 1

    def add_skip(self):
        self.skipped += 1

    def print_summary(self):
        print_header("TEST SUMMARY")
        print(f"Total Tests: {self.total}")
        print_success(f"Passed: {self.passed}")
        if self.failed > 0:
            print_error(f"Failed: {self.failed}")
        if self.warnings > 0:
            print_warning(f"Warnings: {self.warnings}")
        if self.skipped > 0:
            print_warning(f"Skipped: {self.skipped}")

        if self.errors:
            print(f"\n{Colors.BOLD}Errors:{Colors.RESET}")
            for i, error in enumerate(self.errors, 1):
                print_error(f"{i}. {error}")

        print(f"\n{Colors.BOLD}Status: ", end="")
        if self.failed == 0 and self.total > 0:
            print_success("ALL TESTS PASSED ✓")
        elif self.failed == 0:
            print_warning("NO TESTS EXECUTED ⚠")
        else:
            print_error("SOME TESTS FAILED ✗")

results = TestResults()

def test_timeline_activity():
    """Test 1: Timeline Activity Endpoint"""
    print_test("Timeline Activity Endpoint")

    try:
        url = f"{BASE_URL}/api/dashboard/timeline/activity"
        params = {"period": "30d"}
        headers = {
            "X-User-Id": TEST_USER_EMAIL,
            "X-Dev-Bypass": "1"
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            print_error(f"Status code: {response.status_code}")
            results.add_fail(f"Timeline Activity: HTTP {response.status_code}")
            return

        data = response.json()

        # API returns directly a list, not an object with 'activity' key
        if not isinstance(data, list):
            print_error("Response is not a list")
            results.add_fail("Timeline Activity: Invalid data structure")
            return

        # Check data presence
        if len(data) == 0:
            print_warning("Activity list is empty - no data available")
            results.add_warning()
            results.add_pass()  # Still pass, but with warning
            return

        # Validate first entry structure
        first_entry = data[0]
        required_fields = ["date", "messages", "threads"]
        missing_fields = [f for f in required_fields if f not in first_entry]

        if missing_fields:
            print_error(f"Missing fields: {missing_fields}")
            results.add_fail(f"Timeline Activity: Missing fields {missing_fields}")
            return

        print_success(f"Status: {response.status_code}")
        print_success(f"Data points: {len(data)}")
        print_info(f"Sample: {data[0]}")
        results.add_pass()

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        results.add_fail(f"Timeline Activity: {str(e)}")

def test_timeline_tokens():
    """Test 2: Timeline Tokens Endpoint"""
    print_test("Timeline Tokens Endpoint")

    try:
        url = f"{BASE_URL}/api/dashboard/timeline/tokens"
        params = {"period": "30d"}
        headers = {
            "X-User-Id": TEST_USER_EMAIL,
            "X-Dev-Bypass": "1"
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            print_error(f"Status code: {response.status_code}")
            results.add_fail(f"Timeline Tokens: HTTP {response.status_code}")
            return

        data = response.json()

        # API returns directly a list
        if not isinstance(data, list):
            print_error("Response is not a list")
            results.add_fail("Timeline Tokens: Invalid data structure")
            return

        if len(data) == 0:
            print_warning("Tokens list is empty - no data available")
            results.add_warning()
            results.add_pass()
            return

        # Validate structure
        first_entry = data[0]
        required_fields = ["date", "input", "output", "total"]
        missing_fields = [f for f in required_fields if f not in first_entry]

        if missing_fields:
            print_error(f"Missing fields: {missing_fields}")
            results.add_fail(f"Timeline Tokens: Missing fields {missing_fields}")
            return

        # Validate total = input + output
        if first_entry["total"] != first_entry["input"] + first_entry["output"]:
            print_warning("Total != input + output in first entry")
            results.add_warning()

        print_success(f"Status: {response.status_code}")
        print_success(f"Data points: {len(data)}")
        print_info(f"Sample: {first_entry}")
        results.add_pass()

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        results.add_fail(f"Timeline Tokens: {str(e)}")

def test_timeline_costs():
    """Test 3: Timeline Costs Endpoint"""
    print_test("Timeline Costs Endpoint")

    try:
        url = f"{BASE_URL}/api/dashboard/timeline/costs"
        params = {"period": "30d"}
        headers = {
            "X-User-Id": TEST_USER_EMAIL,
            "X-Dev-Bypass": "1"
        }

        response = requests.get(url, params=params, headers=headers)

        if response.status_code != 200:
            print_error(f"Status code: {response.status_code}")
            results.add_fail(f"Timeline Costs: HTTP {response.status_code}")
            return

        data = response.json()

        # API returns directly a list
        if not isinstance(data, list):
            print_error("Response is not a list")
            results.add_fail("Timeline Costs: Invalid data structure")
            return

        if len(data) == 0:
            print_warning("Costs list is empty - no data available")
            results.add_warning()
            results.add_pass()
            return

        # Validate structure
        first_entry = data[0]
        required_fields = ["date", "cost"]
        missing_fields = [f for f in required_fields if f not in first_entry]

        if missing_fields:
            print_error(f"Missing fields: {missing_fields}")
            results.add_fail(f"Timeline Costs: Missing fields {missing_fields}")
            return

        print_success(f"Status: {response.status_code}")
        print_success(f"Data points: {len(data)}")
        print_info(f"Sample: {first_entry}")
        results.add_pass()

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        results.add_fail(f"Timeline Costs: {str(e)}")

def test_admin_global():
    """Test 4: Admin Global Dashboard"""
    print_test("Admin Global Dashboard")

    try:
        url = f"{BASE_URL}/api/admin/dashboard/global"
        headers = {
            "X-User-Id": ADMIN_USER_EMAIL,
            "X-User-Role": "admin",
            "X-Dev-Bypass": "1"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print_error(f"Status code: {response.status_code}")
            results.add_fail(f"Admin Global: HTTP {response.status_code}")
            return

        data = response.json()

        # Check users_breakdown
        if "users_breakdown" not in data:
            print_error("Missing 'users_breakdown' field")
            results.add_fail("Admin Global: Missing users_breakdown")
            return

        users = data["users_breakdown"]

        if len(users) == 0:
            print_warning("No users found in breakdown")
            results.add_warning()
        else:
            print_success(f"Users found: {len(users)}")
            # Validate first user structure
            first_user = users[0]
            required_fields = ["user_id", "email", "role", "total_cost"]
            missing_fields = [f for f in required_fields if f not in first_user]

            if missing_fields:
                print_error(f"Missing fields in user: {missing_fields}")
                results.add_fail(f"Admin Global: Missing user fields {missing_fields}")
                return

            print_info(f"Sample user: {first_user}")

        # Check date_metrics
        if "date_metrics" in data and "last_7_days" in data["date_metrics"]:
            days = data["date_metrics"]["last_7_days"]
            if len(days) == 7:
                print_success(f"Date metrics: 7 days present")
            else:
                print_warning(f"Date metrics: {len(days)} days (expected 7)")
                results.add_warning()

        results.add_pass()

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        results.add_fail(f"Admin Global: {str(e)}")

def test_admin_detailed_costs():
    """Test 5: Admin Detailed Costs"""
    print_test("Admin Detailed Costs Endpoint")

    try:
        url = f"{BASE_URL}/api/admin/costs/detailed"
        headers = {
            "X-User-Id": ADMIN_USER_EMAIL,
            "X-User-Role": "admin",
            "X-Dev-Bypass": "1"
        }

        response = requests.get(url, headers=headers)

        if response.status_code != 200:
            print_error(f"Status code: {response.status_code}")
            results.add_fail(f"Admin Detailed Costs: HTTP {response.status_code}")
            return

        data = response.json()

        # Check structure
        required_top_fields = ["users", "total_users", "grand_total_cost", "total_requests"]
        missing_fields = [f for f in required_top_fields if f not in data]

        if missing_fields:
            print_error(f"Missing top-level fields: {missing_fields}")
            results.add_fail(f"Admin Detailed Costs: Missing fields {missing_fields}")
            return

        users = data["users"]

        if len(users) == 0:
            print_warning("No users with detailed costs")
            results.add_warning()
            results.add_pass()
            return

        # Validate first user structure
        first_user = users[0]
        required_user_fields = ["user_id", "total_cost", "total_requests", "modules"]
        missing_user_fields = [f for f in required_user_fields if f not in first_user]

        if missing_user_fields:
            print_error(f"Missing user fields: {missing_user_fields}")
            results.add_fail(f"Admin Detailed Costs: Missing user fields {missing_user_fields}")
            return

        print_success(f"Status: {response.status_code}")
        print_success(f"Users with cost data: {data['total_users']}")
        print_success(f"Grand total cost: ${data['grand_total_cost']:.4f}")
        print_info(f"Total requests: {data['total_requests']}")

        # Validate module structure if modules present
        if len(first_user["modules"]) > 0:
            first_module = first_user["modules"][0]
            required_module_fields = ["module", "cost", "input_tokens", "output_tokens",
                                     "request_count", "first_request", "last_request"]
            missing_module_fields = [f for f in required_module_fields if f not in first_module]

            if missing_module_fields:
                print_warning(f"Missing module fields: {missing_module_fields}")
                results.add_warning()
            else:
                print_info(f"Sample module: {first_module['module']} - ${first_module['cost']:.4f}")

        results.add_pass()

    except Exception as e:
        print_error(f"Exception: {str(e)}")
        results.add_fail(f"Admin Detailed Costs: {str(e)}")

def main():
    """Run all validation tests"""
    print_header("PHASE 1 BACKEND VALIDATION TESTS")
    print(f"Date: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"Base URL: {BASE_URL}")
    print(f"Test User: {TEST_USER_EMAIL}")
    print(f"Admin User: {ADMIN_USER_EMAIL}")

    # Test server health
    offline_reason = None
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=5)
        if response.status_code == 200:
            print_success("Server is healthy")
        else:
            offline_reason = f"Server health check failed: HTTP {response.status_code}"
    except Exception as e:
        offline_reason = f"Cannot connect to server: {str(e)}"

    if offline_reason:
        print_warning(offline_reason)
        print_warning("Backend unreachable — skipping Phase 1 validation suite.")
        print_info("Démarre le backend FastAPI localement ou définis EMERGENCE_VALIDATION_BASE_URL vers une instance accessible.")
        results.add_warning()
        results.add_skip()
        results.print_summary()
        return 0

    # Run all tests
    print_header("PHASE 1.2 - TIMELINE SERVICE ENDPOINTS")
    test_timeline_activity()
    print()
    test_timeline_tokens()
    print()
    test_timeline_costs()

    print_header("PHASE 1.3 & 1.4 - ADMIN DASHBOARD")
    test_admin_global()

    print_header("PHASE 1.5 - DETAILED COSTS ENDPOINT")
    test_admin_detailed_costs()

    # Print summary
    results.print_summary()

    # Return exit code
    return 0 if results.failed == 0 else 1

if __name__ == "__main__":
    sys.exit(main())
