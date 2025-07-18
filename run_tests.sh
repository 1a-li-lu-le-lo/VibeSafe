#!/bin/bash
#
# VibeSafe Test Runner
#

set -e

echo "🧪 VibeSafe Test Suite"
echo "===================="
echo

# Check if pytest is installed
if ! command -v pytest &> /dev/null; then
    echo "❌ pytest not found. Installing test dependencies..."
    pip install -e ".[dev]"
fi

# Run different test suites
echo "Running unit tests..."
pytest tests/test_encryption.py tests/test_storage.py -v

echo
echo "Running CLI tests..."
pytest tests/test_cli.py -v

echo
echo "Running security tests..."
pytest tests/test_security.py -v -m security

echo
echo "Running integration tests..."
pytest tests/test_integration.py -v -m integration

echo
echo "Running all tests with coverage..."
pytest --cov=vibesafe --cov-report=term-missing --cov-report=html

echo
echo "✅ Test suite complete!"
echo "📊 Coverage report available in htmlcov/index.html"