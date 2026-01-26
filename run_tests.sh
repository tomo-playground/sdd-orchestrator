#!/bin/bash

# Shorts Producer - Local Test Runner
# Runs backend (pytest), frontend (vitest), and VRT tests with color-coded output

set -e  # Exit on error

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
BACKEND_RESULT=""
FRONTEND_RESULT=""
VRT_RESULT=""
TOTAL_TESTS=0
PASSED_TESTS=0
FAILED_TESTS=0

# Print header
print_header() {
  echo -e "${BLUE}═══════════════════════════════════════════${NC}"
  echo -e "${BLUE}  Shorts Producer Test Suite${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════${NC}"
  echo ""
}

# Print section
print_section() {
  echo -e "\n${YELLOW}▶ $1${NC}"
  echo "─────────────────────────────────────────────"
}

# Print result
print_result() {
  if [ $1 -eq 0 ]; then
    echo -e "${GREEN}✓ $2 PASSED${NC}"
    PASSED_TESTS=$((PASSED_TESTS + 1))
  else
    echo -e "${RED}✗ $2 FAILED${NC}"
    FAILED_TESTS=$((FAILED_TESTS + 1))
  fi
}

# Print summary
print_summary() {
  echo -e "\n${BLUE}═══════════════════════════════════════════${NC}"
  echo -e "${BLUE}  Test Summary${NC}"
  echo -e "${BLUE}═══════════════════════════════════════════${NC}"
  echo ""

  if [ ! -z "$BACKEND_RESULT" ]; then
    echo -e "Backend Tests:  $BACKEND_RESULT"
  fi

  if [ ! -z "$FRONTEND_RESULT" ]; then
    echo -e "Frontend Tests: $FRONTEND_RESULT"
  fi

  if [ ! -z "$VRT_RESULT" ]; then
    echo -e "VRT Tests:      $VRT_RESULT"
  fi

  echo ""
  echo -e "Total: ${BLUE}$TOTAL_TESTS${NC} suites | ${GREEN}$PASSED_TESTS${NC} passed | ${RED}$FAILED_TESTS${NC} failed"
  echo ""

  if [ $FAILED_TESTS -eq 0 ]; then
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    echo -e "${GREEN}  ALL TESTS PASSED! 🎉${NC}"
    echo -e "${GREEN}═══════════════════════════════════════════${NC}"
    exit 0
  else
    echo -e "${RED}═══════════════════════════════════════════${NC}"
    echo -e "${RED}  SOME TESTS FAILED${NC}"
    echo -e "${RED}═══════════════════════════════════════════${NC}"
    exit 1
  fi
}

# Main script
print_header

# ============================================================
# Backend Tests (pytest)
# ============================================================
print_section "Backend Tests (pytest)"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

if [ ! -d "backend" ]; then
  echo -e "${RED}✗ Backend directory not found${NC}"
  BACKEND_RESULT="${RED}✗ FAILED (dir not found)${NC}"
  FAILED_TESTS=$((FAILED_TESTS + 1))
else
  cd backend

  if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠ No venv found. Run: python -m venv venv && source venv/bin/activate && pip install -r requirements.txt${NC}"
    BACKEND_RESULT="${YELLOW}⚠ SKIPPED (no venv)${NC}"
    cd ..
  else
    # Activate venv and run tests
    source venv/bin/activate

    echo "Running pytest (excluding VRT)..."
    if pytest --ignore=tests/vrt -v; then
      print_result 0 "Backend Tests"
      BACKEND_RESULT="${GREEN}✓ PASSED${NC}"
    else
      print_result 1 "Backend Tests"
      BACKEND_RESULT="${RED}✗ FAILED${NC}"
    fi

    deactivate
    cd ..
  fi
fi

# ============================================================
# Frontend Tests (vitest)
# ============================================================
print_section "Frontend Tests (vitest)"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

if [ ! -d "frontend" ]; then
  echo -e "${RED}✗ Frontend directory not found${NC}"
  FRONTEND_RESULT="${RED}✗ FAILED (dir not found)${NC}"
  FAILED_TESTS=$((FAILED_TESTS + 1))
else
  cd frontend

  if [ ! -d "node_modules" ]; then
    echo -e "${YELLOW}⚠ No node_modules found. Run: npm install${NC}"
    FRONTEND_RESULT="${YELLOW}⚠ SKIPPED (no node_modules)${NC}"
    cd ..
  else
    echo "Running vitest..."
    if npm test -- --run; then
      print_result 0 "Frontend Tests"
      FRONTEND_RESULT="${GREEN}✓ PASSED${NC}"
    else
      print_result 1 "Frontend Tests"
      FRONTEND_RESULT="${RED}✗ FAILED${NC}"
    fi

    cd ..
  fi
fi

# ============================================================
# VRT Tests (pytest)
# ============================================================
print_section "VRT Tests (Visual Regression)"
TOTAL_TESTS=$((TOTAL_TESTS + 1))

if [ ! -d "backend/tests/vrt" ]; then
  echo -e "${YELLOW}⚠ VRT tests not found${NC}"
  VRT_RESULT="${YELLOW}⚠ SKIPPED (no vrt dir)${NC}"
else
  cd backend

  if [ ! -d "venv" ]; then
    echo -e "${YELLOW}⚠ No venv found. Skipping VRT tests.${NC}"
    VRT_RESULT="${YELLOW}⚠ SKIPPED (no venv)${NC}"
    cd ..
  else
    source venv/bin/activate

    echo "Running VRT tests..."
    if pytest tests/vrt -v; then
      print_result 0 "VRT Tests"
      VRT_RESULT="${GREEN}✓ PASSED${NC}"
    else
      print_result 1 "VRT Tests"
      VRT_RESULT="${RED}✗ FAILED${NC}"
    fi

    deactivate
    cd ..
  fi
fi

# ============================================================
# Print Summary
# ============================================================
print_summary
