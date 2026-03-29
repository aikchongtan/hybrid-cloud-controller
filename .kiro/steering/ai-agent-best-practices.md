# AI Agent Best Practices for Hybrid Cloud Controller

This steering file provides guidance for AI coding agents working on the Hybrid Cloud Controller project. Following these practices improves code quality, reduces hallucinations, and ensures consistency.

---

## Context-Hub for API Documentation

### Overview
Use [context-hub](https://github.com/andrewyng/context-hub) by Andrew Ng to fetch curated, versioned API documentation instead of relying on potentially outdated training data. This prevents API hallucinations and ensures accurate implementation.

### Installation
```bash
# Install context-hub globally
npm install -g @context-hub/cli

# Or use npx (no installation required)
npx @context-hub/cli --help
```

### Usage Before Working with APIs

**Before implementing features that use external APIs, fetch the latest documentation:**

```bash
# Fetch AWS SDK (boto3) documentation
chub fetch boto3

# Fetch Flask documentation
chub fetch flask

# Fetch SQLAlchemy documentation
chub fetch sqlalchemy

# Fetch Terraform documentation
chub fetch terraform

# Fetch Docker SDK documentation
chub fetch docker

# Fetch pytest documentation
chub fetch pytest
```

### Key APIs Used in This Project

| Package | Purpose | When to Fetch |
|---------|---------|---------------|
| `boto3` | AWS SDK for EC2, S3, EBS, Pricing API | Before working with AWS provisioning or pricing |
| `flask` | Web framework for API and Web UI | Before creating routes or middleware |
| `sqlalchemy` | Database ORM | Before working with models or queries |
| `terraform` | Infrastructure as Code | Before generating Terraform configs |
| `docker` | Container management | Before working with container provisioning |
| `pytest` | Testing framework | Before writing tests |
| `hypothesis` | Property-based testing | Before writing property tests |
| `bcrypt` | Password hashing | Before working with authentication |
| `cryptography` | Encryption library | Before working with credential encryption |

### Best Practices

1. **Fetch Before Implementation**: Always fetch documentation before starting work on a feature that uses external APIs
2. **Check Version Compatibility**: Ensure the fetched docs match the version in `requirements.txt`
3. **Verify Examples**: Use code examples from context-hub docs rather than generating from memory
4. **Update Regularly**: Re-fetch documentation when upgrading package versions

### Example Workflow

```bash
# 1. Check current package version
grep "boto3" requirements.txt

# 2. Fetch documentation
chub fetch boto3

# 3. Review relevant sections
chub show boto3 ec2

# 4. Implement feature using accurate API calls

# 5. Annotate if documentation is unclear
chub annotate boto3 "EC2 instance creation examples need more detail"
```

---

## Project-Specific API Patterns

### AWS Boto3 Patterns

**LocalStack Configuration**:
```python
# Always use endpoint_url for LocalStack
import boto3

ec2_client = boto3.client(
    'ec2',
    endpoint_url='http://localhost:4566',  # LocalStack
    region_name='us-east-1',
    aws_access_key_id='test',
    aws_secret_access_key='test'
)
```

**Pricing API**:
```python
# Pricing API requires us-east-1 region
pricing_client = boto3.client('pricing', region_name='us-east-1')
```

### Flask Patterns

**Route Authentication**:
```python
# Use Flask's g object for user context (set by middleware)
from flask import g

user_id = getattr(g, 'user_id', None)
if not user_id:
    return error_response('AUTHENTICATION_REQUIRED', 'Authentication required'), 401
```

**Session Management**:
```python
# Use Flask session for Web UI
from flask import session

session['token'] = token
session['user_id'] = user_id
session.permanent = False  # Expires when browser closes
```

### SQLAlchemy Patterns

**Session Management**:
```python
# Always use try/finally for session cleanup
from packages.database import get_session

session = get_session()
try:
    # Database operations
    session.commit()
except Exception as e:
    session.rollback()
    raise
finally:
    session.close()
```

**Query Patterns**:
```python
# Use filter() for WHERE clauses
result = session.query(Model).filter(
    Model.id == id,
    Model.user_id == user_id
).first()
```

---

## Avoiding Common Hallucinations

### 1. AWS API Methods
❌ **Don't guess method names**:
```python
# Wrong - hallucinated method
ec2.create_instance(...)  # Doesn't exist
```

✅ **Use context-hub to verify**:
```python
# Correct - actual boto3 method
ec2.run_instances(...)
```

### 2. Flask Route Decorators
❌ **Don't invent decorators**:
```python
# Wrong - doesn't exist
@app.authenticate()
def my_route():
    pass
```

✅ **Use actual Flask patterns**:
```python
# Correct - use middleware or before_request
@app.before_request
def check_auth():
    # Authentication logic
    pass
```

### 3. SQLAlchemy Relationships
❌ **Don't guess relationship syntax**:
```python
# Wrong - incorrect syntax
relationship('Model', foreign_key='id')
```

✅ **Use context-hub to verify**:
```python
# Correct - actual SQLAlchemy syntax
relationship('Model', foreign_keys=[foreign_key_column])
```

---

## Testing with Accurate APIs

### Property-Based Testing with Hypothesis

**Fetch Hypothesis docs before writing property tests**:
```bash
chub fetch hypothesis
```

**Use actual Hypothesis strategies**:
```python
from hypothesis import given, strategies as st

@given(
    cpu_cores=st.integers(min_value=1, max_value=128),
    memory_gb=st.integers(min_value=1, max_value=1024)
)
def test_configuration_validation(cpu_cores, memory_gb):
    # Test implementation
    pass
```

### Pytest Fixtures

**Fetch pytest docs for fixture patterns**:
```bash
chub fetch pytest
```

---

## Documentation and Comments

### When to Add Comments

1. **Complex AWS API Calls**: Explain why specific parameters are used
2. **LocalStack Workarounds**: Document any LocalStack-specific behavior
3. **Security Decisions**: Explain authentication/encryption choices
4. **Performance Optimizations**: Document why certain approaches were chosen

### Example:
```python
# Use us-east-1 for Pricing API (required by AWS, not available in other regions)
pricing_client = boto3.client('pricing', region_name='us-east-1')

# LocalStack doesn't support Pricing API, so we use fallback values
if not pricing_data:
    logger.warning("Using fallback pricing data (LocalStack limitation)")
    pricing_data = get_fallback_pricing()
```

---

## Feedback Loop

### Annotating Documentation Gaps

When you encounter unclear or missing documentation:

```bash
# Annotate for future improvement
chub annotate boto3 "EC2 run_instances: Need example for network interface configuration"

# Provide feedback on documentation quality
chub feedback flask "Excellent examples for route decorators"
```

### Learning from Previous Sessions

Context-hub maintains annotations across sessions, so:
1. Check annotations before starting work
2. Add new annotations when you discover gaps
3. Update annotations when documentation improves

---

## Integration with Development Workflow

### Pre-Implementation Checklist

Before implementing a feature:
- [ ] Identify external APIs needed
- [ ] Fetch documentation with context-hub
- [ ] Review relevant examples and patterns
- [ ] Check project-specific patterns (this file)
- [ ] Verify package versions match requirements.txt

### During Implementation

- [ ] Reference fetched documentation for API calls
- [ ] Follow project-specific patterns
- [ ] Add comments for complex API usage
- [ ] Test with actual API behavior (not assumptions)

### Post-Implementation

- [ ] Annotate any documentation gaps discovered
- [ ] Update this file if new patterns emerge
- [ ] Run tests to verify API usage is correct

---

## Additional AI Agent Tools

### GitHub Agentic Workflows (gh-aw)

**Status**: Optional - Not currently used

**Potential Use Cases**:
- Automated UAT test runs on PR
- Automated deployment workflows
- Status report generation

**Installation** (if needed in future):
```bash
gh extension install githubnext/gh-aw
```

---

## Project-Specific Considerations

### LocalStack Limitations

LocalStack doesn't support all AWS services. Known limitations:
- ❌ Pricing API not available → Use fallback pricing
- ❌ Some ECS features limited → Test with real AWS for production
- ✅ EC2, S3, EBS work well for development

### Development vs Production

**Development (LocalStack)**:
```python
endpoint_url = 'http://localhost:4566'
```

**Production (Real AWS)**:
```python
endpoint_url = None  # Use default AWS endpoints
```

### Security Considerations

- Never commit AWS credentials to git
- Use environment variables for secrets
- Encrypt sensitive data in database (use `packages/security/crypto.py`)
- Validate all user inputs (use `packages/security/sanitizer.py`)

---

## Resources

- **Context-Hub**: https://github.com/andrewyng/context-hub
- **Project Documentation**: `README.md`
- **UAT Guide**: `UAT-GUIDED-SESSION.md`
- **Coding Standards**: `.kiro/steering/coding-standards.md`
- **API Documentation**: Use `chub show <package>` for details

---

## Maintenance

This file should be updated when:
- New external APIs are added to the project
- New patterns emerge from development
- Context-hub adds support for new packages
- Team discovers better practices

**Last Updated**: 2026-03-22
