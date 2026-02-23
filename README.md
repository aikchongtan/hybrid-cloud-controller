# Hybrid Cloud Controller

A Python-based application that enables users to compare Total Cost of Ownership (TCO) between hosting applications on on-premises infrastructure versus AWS public cloud.

## Features

- Web-based configuration input for compute, storage, network, and workload specifications
- TCO calculation engine comparing on-premises and AWS costs
- AWS pricing integration with daily updates
- Conversational Q&A service for cost analysis
- Infrastructure provisioning using Terraform for both AWS (via LocalStack) and on-premises (IaaS/CaaS)
- Monitoring dashboard for operational metrics
- Secure authentication and credential encryption

## Project Structure

```
hybrid-cloud-controller/
├── packages/              # Main application packages
├── tests/
│   ├── unit/             # Unit tests
│   ├── property/         # Property-based tests
│   └── integration/      # Integration tests
├── pyproject.toml        # Project metadata and build configuration
├── requirements.piptools # Production dependencies
├── requirements-development.piptools # Development dependencies
├── pytest.ini            # Test configuration
├── ruff.toml            # Formatting and linting rules
└── change-log.md        # Project change log
```

## Requirements

- Python 3.13+
- uv (for dependency management)

## Installation

1. Install uv:
```bash
pip install uv
```

2. Compile and install dependencies:
```bash
uv pip-compile requirements.piptools -o requirements.txt
uv pip-compile requirements-development.piptools -o requirements-development.txt
uv pip install -r requirements-development.txt
```

## Development

### Code Formatting and Linting

```bash
# Format code
ruff format .

# Check and fix linting issues
ruff check --fix .
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test categories
pytest tests/unit/
pytest tests/property/
pytest tests/integration/
```

## License

MIT
