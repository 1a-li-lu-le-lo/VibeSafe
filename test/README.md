# VibeSafe Test Suite

## Overview

VibeSafe includes comprehensive automated testing to ensure security, functionality, and reliability.

## Test Categories

### 1. Unit Tests (`app.test.js`)
- App initialization
- Navigation between tabs
- State management
- Modal interactions
- Event handling

### 2. Security Tests (`security.test.js`)
- Input validation
- Touch ID protection
- Secure communication
- Error information leakage prevention
- XSS prevention

### 3. Integration Tests (`integration.test.js`)
- Full workflow testing with real Tauri backend
- Touch ID authentication flows
- Error scenario handling
- End-to-end secret management

## Running Tests

### Prerequisites
```bash
npm install --save-dev jest @babel/core @babel/preset-env babel-jest jsdom selenium-webdriver
```

### Run All Tests
```bash
npm test
```

### Run Specific Test Suite
```bash
# Unit tests only
npm test app.test.js

# Security tests only
npm test security.test.js

# Integration tests (requires Tauri)
npm test integration.test.js
```

### Coverage Report
```bash
npm test -- --coverage
```

## Test Configuration

### Coverage Thresholds
- Branches: 80%
- Functions: 80%
- Lines: 80%
- Statements: 80%

### Mock Configuration
Tests use mocked Tauri API to avoid requiring the full Tauri runtime for unit tests.

## Writing New Tests

### Test Structure
```javascript
describe('Feature Name', () => {
    beforeEach(() => {
        // Setup
    });
    
    test('should do something', () => {
        // Arrange
        // Act
        // Assert
    });
});
```

### Best Practices
1. Test user interactions, not implementation details
2. Use descriptive test names
3. Keep tests isolated and independent
4. Mock external dependencies
5. Test error cases and edge conditions

## CI/CD Integration

Add to your GitHub Actions workflow:

```yaml
- name: Run Tests
  run: |
    npm install
    npm test -- --ci --coverage
    
- name: Upload Coverage
  uses: codecov/codecov-action@v3
  with:
    file: ./coverage/lcov.info
```