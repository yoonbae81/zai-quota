# ZAI Usage - Test Suite

## Running Tests

### Run All Tests
```bash
python -m unittest discover tests
```

### Run Specific Test File
```bash
python -m unittest tests.test_main
```

### Verbose Output
```bash
python -m unittest discover tests -v
```

## Test Structure

```
tests/
├── __init__.py
└── test_main.py
```

## Test Coverage

- `test_main.py`: Tests for main script functions
  - `calculate_metrics`: Tests metrics calculation from token limit data
  - `extract_token_limit`: Tests extraction of TOKENS_LIMIT from API response
