# Quota - Test Suite

## Running Tests

### Run All Tests
```bash
python3 -m unittest discover tests
```

### Run Specific Test File
```bash
python3 -m unittest tests.test_main
```

### Verbose Output
```bash
python3 -m unittest discover tests -v
```

## Test Structure

```
tests/
├── __init__.py
├── test_main.py
├── test_server_routing.py
└── README.md
```

## Test Coverage

- `test_main.py`: Tests for the provider framework and main script functions
  - `format_reset_info`: Next-reset / remaining-time formatting
  - `QuotaMetrics.to_dict`: Normalized metrics rendering
  - `ZaiProvider`: Provider metadata, TOKENS_LIMIT extraction, fetch normalization
  - `build_comprehensive_view`: All-provider view with stub providers (ok / not_configured / error statuses)
- `test_server_routing.py`: Base-path normalization and `resolve_route` (base route, provider sub-paths, aliases, query strings, 404 cases)
