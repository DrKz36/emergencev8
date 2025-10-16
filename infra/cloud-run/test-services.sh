#!/bin/bash
# Test script for Emergence microservices on Cloud Run
# Validates that all services are properly deployed and responding

set -e

# Configuration
PROJECT_ID="emergence-469005"
REGION="europe-west1"

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Counters
TESTS_PASSED=0
TESTS_FAILED=0

# Functions
print_test_header() {
    echo ""
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${BLUE}  $1${NC}"
    echo -e "${BLUE}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
}

print_success() {
    echo -e "${GREEN}✅ $1${NC}"
    ((TESTS_PASSED++))
}

print_failure() {
    echo -e "${RED}❌ $1${NC}"
    ((TESTS_FAILED++))
}

print_warning() {
    echo -e "${YELLOW}⚠️  $1${NC}"
}

print_info() {
    echo -e "${BLUE}ℹ️  $1${NC}"
}

# Get service URL
get_service_url() {
    local service_name=$1
    gcloud run services describe "$service_name" \
        --region="$REGION" \
        --project="$PROJECT_ID" \
        --format="value(status.url)" 2>/dev/null || echo ""
}

# Test HTTP endpoint
test_endpoint() {
    local url=$1
    local description=$2
    local expected_status=${3:-200}

    print_info "Testing: $description"
    print_info "URL: $url"

    response=$(curl -s -w "\n%{http_code}" "$url" 2>/dev/null || echo "000")
    status_code=$(echo "$response" | tail -n 1)
    body=$(echo "$response" | sed '$d')

    if [ "$status_code" = "$expected_status" ]; then
        print_success "$description - HTTP $status_code"
        echo "$body" | jq . 2>/dev/null || echo "$body"
        return 0
    else
        print_failure "$description - Expected HTTP $expected_status, got HTTP $status_code"
        echo "$body"
        return 1
    fi
}

# Main test execution
echo "🧪 Emergence Microservices Test Suite"
echo "======================================"
echo ""
print_info "Project: $PROJECT_ID"
print_info "Region: $REGION"

# Test 1: Authentication Service
print_test_header "Test 1: Authentication Service"

AUTH_URL=$(get_service_url "emergence-auth-service")
if [ -z "$AUTH_URL" ]; then
    print_failure "Auth service not found or not deployed"
else
    print_info "Service URL: $AUTH_URL"

    # Health check
    test_endpoint "$AUTH_URL/api/health" "Auth service health check"

    # Dev login endpoint (if dev mode is enabled)
    print_info "Attempting dev login endpoint (may fail if dev mode disabled)"
    curl -s -X POST "$AUTH_URL/api/auth/dev/login" \
        -H "Content-Type: application/json" 2>/dev/null | jq . || print_warning "Dev login disabled or failed"
fi

# Test 2: Session Service
print_test_header "Test 2: Session Management Service"

SESSION_URL=$(get_service_url "emergence-session-service")
if [ -z "$SESSION_URL" ]; then
    print_failure "Session service not found or not deployed"
else
    print_info "Service URL: $SESSION_URL"

    # Health check
    test_endpoint "$SESSION_URL/api/health" "Session service health check"

    # Check if WebSocket endpoint is accessible (will fail with 426 for HTTP, which is expected)
    print_info "Checking WebSocket endpoint availability"
    ws_response=$(curl -s -w "%{http_code}" "$SESSION_URL/ws/test-session" 2>/dev/null)
    if [[ "$ws_response" == *"426"* ]] || [[ "$ws_response" == *"400"* ]]; then
        print_success "WebSocket endpoint responding (upgrade required - expected)"
    else
        print_warning "WebSocket endpoint may not be configured correctly"
    fi
fi

# Test 3: Main Application (if exists)
print_test_header "Test 3: Main Application"

MAIN_URL=$(get_service_url "emergence-app")
if [ -z "$MAIN_URL" ]; then
    print_warning "Main app not found (may not be deployed yet)"
else
    print_info "Service URL: $MAIN_URL"
    test_endpoint "$MAIN_URL/api/health" "Main app health check"
fi

# Test 4: Service Integration
print_test_header "Test 4: Service Integration Tests"

if [ -n "$AUTH_URL" ] && [ -n "$SESSION_URL" ]; then
    print_info "Both auth and session services are running"

    # Test CORS headers
    print_info "Testing CORS configuration on Auth service"
    cors_response=$(curl -s -I -H "Origin: http://localhost:3000" "$AUTH_URL/api/health" 2>/dev/null)
    if echo "$cors_response" | grep -qi "access-control-allow-origin"; then
        print_success "CORS headers present"
    else
        print_warning "CORS headers not found - may need configuration"
    fi
else
    print_warning "Cannot perform integration tests - services not deployed"
fi

# Test 5: Secrets Configuration
print_test_header "Test 5: Secrets Configuration"

print_info "Checking required secrets in Secret Manager"

REQUIRED_SECRETS=(
    "AUTH_JWT_SECRET"
    "AUTH_ADMIN_EMAILS"
    "OPENAI_API_KEY"
    "ANTHROPIC_API_KEY"
)

for secret in "${REQUIRED_SECRETS[@]}"; do
    if gcloud secrets describe "$secret" --project="$PROJECT_ID" &>/dev/null; then
        print_success "Secret $secret exists"
    else
        print_failure "Secret $secret is missing"
    fi
done

# Test 6: Service Metrics
print_test_header "Test 6: Service Metrics & Monitoring"

if [ -n "$SESSION_URL" ]; then
    print_info "Checking Prometheus metrics endpoint"
    metrics_response=$(curl -s -w "%{http_code}" "$SESSION_URL/metrics" 2>/dev/null)
    if [[ "$metrics_response" == *"200"* ]] || [[ "$metrics_response" == *"sessions_"* ]]; then
        print_success "Metrics endpoint responding"
    else
        print_warning "Metrics endpoint may not be configured"
    fi
fi

# Summary
print_test_header "Test Summary"

TOTAL_TESTS=$((TESTS_PASSED + TESTS_FAILED))
PASS_RATE=0
if [ $TOTAL_TESTS -gt 0 ]; then
    PASS_RATE=$((TESTS_PASSED * 100 / TOTAL_TESTS))
fi

echo ""
echo "Total tests run: $TOTAL_TESTS"
echo -e "Passed: ${GREEN}$TESTS_PASSED${NC}"
echo -e "Failed: ${RED}$TESTS_FAILED${NC}"
echo "Pass rate: $PASS_RATE%"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${GREEN}  ✅ All tests passed!${NC}"
    echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    exit 0
else
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo -e "${RED}  ❌ Some tests failed${NC}"
    echo -e "${RED}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
    echo ""
    echo "Review the failures above and check:"
    echo "  - Service deployment status"
    echo "  - Secret Manager configuration"
    echo "  - Cloud Run service logs"
    echo ""
    echo "Troubleshooting:"
    echo "  gcloud run services list --project=$PROJECT_ID --region=$REGION"
    echo "  gcloud run services logs read SERVICE_NAME --project=$PROJECT_ID"
    exit 1
fi
