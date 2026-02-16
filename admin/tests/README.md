# JavaScript Testing for PBX Admin Panel

## Overview

This directory contains JavaScript tests for the PBX admin panel functionality using Jest.

## Setup

### Prerequisites

- Node.js 20+ and npm installed

### Installation

Install the testing dependencies:

```bash
npm install
```

## Running Tests

### Run all tests

```bash
npm test
```

### Run tests in watch mode

```bash
npm run test:watch
```

### Run tests with coverage

```bash
npm run test:coverage
```

Coverage reports will be generated in the `coverage/` directory.

## Test Structure

Tests are organized in the `admin/tests/` directory with the following structure:

```
admin/tests/
├── voicemail.test.js       # Tests for voicemail management functionality
└── ...                     # Additional test files
```

## Writing Tests

### Test File Naming

- Test files should be named `*.test.js`
- Place test files in `admin/tests/` directory

### Example Test

```javascript
describe('Feature Name', () => {
  beforeEach(() => {
    // Setup code
  });

  it('should do something', async () => {
    // Test code
    expect(result).toBe(expected);
  });
});
```

## Current Test Coverage

### Voicemail Management (`voicemail.test.js`)

Tests the following functions:

- `loadVoicemailTab()`: Loading extensions list
  - Successful extension loading
  - Handling authentication errors (401)
  - Handling server errors (500)
  - Handling network errors
  - Including authentication headers

- `loadVoicemailForExtension()`: Loading voicemail messages
  - Hiding sections when no extension provided
  - Successful voicemail message loading
  - Handling authentication errors (401)
  - Handling server errors (500)
  - Including authentication headers
  - Showing sections when extension provided

## Best Practices

1. **Mock External Dependencies**: Always mock `fetch`, `localStorage`, and other browser APIs
2. **Test Error Cases**: Include tests for both success and failure scenarios
3. **Use Descriptive Names**: Test descriptions should clearly state what is being tested
4. **Arrange-Act-Assert**: Structure tests with clear setup, execution, and verification phases
5. **Avoid Test Interdependencies**: Each test should be independent and not rely on others

## Continuous Integration

Tests should be run as part of the CI/CD pipeline:

```yaml
# Example GitHub Actions workflow
- name: Run JavaScript Tests
  run: |
    npm install
    npm test
```

## Troubleshooting

### Common Issues

**Tests failing with "Cannot find module"**
- Run `npm install` to ensure all dependencies are installed

**Tests timing out**
- Check for missing `async/await` in test functions
- Ensure all mocked promises are resolved/rejected

**Coverage not generating**
- Ensure test files match the pattern in `package.json`
- Check that source files are in the correct location

## Contributing

When adding new JavaScript functionality to the admin panel:

1. Write tests first (TDD approach recommended)
2. Ensure tests pass before submitting PR
3. Maintain or improve coverage percentage
4. Follow existing test patterns and conventions
