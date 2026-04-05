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
│   ├── api/              # REST API endpoints
│   ├── web_ui/           # Flask web interface
│   ├── tco_engine/       # TCO calculation logic
│   ├── pricing_service/  # AWS pricing integration
│   ├── qa_service/       # Conversational Q&A
│   ├── provisioner/      # Infrastructure provisioning
│   ├── monitoring/       # Metrics and dashboard
│   ├── database/         # Data access layer
│   └── security/         # Authentication & encryption
├── tests/
│   ├── unit/             # Unit tests
│   ├── property/         # Property-based tests
│   └── integration/      # Integration tests
├── docker-compose.yml    # Docker Compose configuration
├── Dockerfile.api        # API service Dockerfile
├── Dockerfile.web_ui     # Web UI service Dockerfile
├── .env.example          # Environment variables template
├── pyproject.toml        # Project metadata and build configuration
├── requirements.piptools # Production dependencies
├── requirements-development.piptools # Development dependencies
├── pytest.ini            # Test configuration
├── ruff.toml            # Formatting and linting rules
└── change-log.md        # Project change log
```

## Requirements

- Python 3.13+
- Docker and Docker Compose (for containerized development)
- uv (for dependency management)

## Quick Start with Docker Compose

The easiest way to get started is using Docker Compose, which sets up all services including the database and LocalStack.

### 1. Clone the repository

```bash
git clone <repository-url>
cd hybrid-cloud-controller
```

### 2. Set up environment variables

```bash
cp .env.example .env
# Edit .env and update values as needed (defaults work for development)
```

### 3. Start all services

```bash
docker-compose up -d
```

This will start:
- **PostgreSQL database** on port 5432
- **LocalStack** (AWS emulation) on port 4566
- **API service** on port 10000
- **Web UI** on port 10001

### 4. Access the application

- Web UI: http://localhost:10001
- API: http://localhost:10000
- LocalStack: http://localhost:4566

### 5. View logs

```bash
# All services
docker-compose logs -f

# Specific service
docker-compose logs -f web_ui
docker-compose logs -f api
```

### 6. Stop services

```bash
docker-compose down

# Remove volumes (database data)
docker-compose down -v
```

## Configuration Guide

### Understanding Endpoint Configuration

The application uses different endpoint configurations depending on whether services communicate **within Docker** (inter-container) or from **outside Docker** (your browser or host machine).

#### Docker Service Names vs Localhost

**Rule of Thumb:**
- **Inter-container communication** (Container → Container): Use Docker service names
- **External access** (Browser → Container): Use `localhost`

#### Endpoint Configuration Table

| Purpose | Environment Variable | Docker Compose Value | Local Development Value | Used By | Connects To |
|---------|---------------------|---------------------|------------------------|---------|-------------|
| **Database** | `DATABASE_URL` | `postgresql://...@database:5432/...` | `postgresql://...@localhost:5432/...` | API, Web UI | PostgreSQL |
| **LocalStack** | `LOCALSTACK_ENDPOINT` | `http://localstack:4566` | `http://localhost:4566` | API | LocalStack |
| **API Service** | `API_BASE_URL` | `http://api:10000` | `http://localhost:10000` | Web UI | API |

#### Why This Matters

**Docker Networking:**
- Inside Docker Compose, containers are on a private network
- Each service has a hostname matching its service name (e.g., `database`, `api`, `localstack`)
- Using `localhost` inside a container refers to **that container itself**, not other services

**External Access:**
- Your browser and host machine are **outside** the Docker network
- Docker Compose maps container ports to your host machine
- You access services via `localhost:<port>` from your browser

#### Configuration Examples

**✅ Correct - Docker Compose (.env for containers):**
```bash
DATABASE_URL=postgresql://hybrid_cloud_user:password@database:5432/hybrid_cloud
LOCALSTACK_ENDPOINT=http://localstack:4566
API_BASE_URL=http://api:10000
```

**✅ Correct - Local Development (.env for host):**
```bash
DATABASE_URL=postgresql://hybrid_cloud_user:password@localhost:5432/hybrid_cloud
LOCALSTACK_ENDPOINT=http://localhost:4566
API_BASE_URL=http://localhost:10000
```

**❌ Incorrect - Mixed configuration:**
```bash
# Don't mix Docker service names with localhost!
DATABASE_URL=postgresql://...@localhost:5432/...  # Wrong for Docker
LOCALSTACK_ENDPOINT=http://localstack:4566        # Correct
API_BASE_URL=http://localhost:10000               # Wrong for Docker
```

#### Browser Access (Always localhost)

From your browser or host machine, always use `localhost`:
- Web UI: `http://localhost:10001`
- API (direct): `http://localhost:10000`
- LocalStack (direct): `http://localhost:4566`
- Database (direct): `localhost:5432`

#### Quick Reference

**When to use Docker service names:**
- ✅ API connecting to Database → `database:5432`
- ✅ API connecting to LocalStack → `localstack:4566`
- ✅ Web UI connecting to API → `api:10000`

**When to use localhost:**
- ✅ Browser accessing Web UI → `localhost:10001`
- ✅ curl/Postman testing API → `localhost:10000`
- ✅ psql connecting to database → `localhost:5432`

### Environment Variables Reference

The `.env.example` file is pre-configured for Docker Compose. Copy it to `.env`:

```bash
cp .env.example .env
```

**For Docker Compose (default):** No changes needed - the example file uses Docker service names.

**For local development:** Update these variables to use `localhost`:
```bash
DATABASE_URL=postgresql://hybrid_cloud_user:dev_password_change_me@localhost:5432/hybrid_cloud
LOCALSTACK_ENDPOINT=http://localhost:4566
API_BASE_URL=http://localhost:10000
```

### Verifying Configuration

After starting services, verify connectivity:

```bash
# Check all services are running
docker-compose ps

# Test API health (from host)
curl http://localhost:10000/api/health

# Test LocalStack health (from host)
curl http://localhost:4566/_localstack/health

# Test database connection (from host)
psql -h localhost -p 5432 -U hybrid_cloud_user -d hybrid_cloud

# Test inter-container connectivity (from inside API container)
docker-compose exec api curl http://localstack:4566/_localstack/health
```

## Local Development Setup

For local development without Docker:

### 1. Install uv

```bash
pip install uv
```

### 2. Compile and install dependencies

```bash
uv pip-compile requirements.piptools -o requirements.txt
uv pip-compile requirements-development.piptools -o requirements-development.txt
uv pip install -r requirements-development.txt
```

### 3. Set up environment variables

```bash
cp .env.example .env
# Edit .env with your configuration
```

### 4. Set up the database

```bash
# Install PostgreSQL locally or use Docker:
docker run -d \
  --name hybrid-cloud-db \
  -e POSTGRES_DB=hybrid_cloud \
  -e POSTGRES_USER=hybrid_cloud_user \
  -e POSTGRES_PASSWORD=dev_password_change_me \
  -p 5432:5432 \
  postgres:16-alpine
```

### 5. Set up LocalStack

```bash
# Run LocalStack in Docker:
docker run -d \
  --name hybrid-cloud-localstack \
  -e SERVICES=ec2,ebs,s3,ecs,pricing \
  -p 4566:4566 \
  localstack/localstack:latest
```

### 6. Run database migrations

```bash
# TODO: Add Alembic migration commands when migrations are set up
# alembic upgrade head
```

### 7. Start the API server

```bash
python -m packages.api.app
# API will be available at http://localhost:10000
```

### 8. Start the Web UI (in a separate terminal)

```bash
python -m packages.web_ui.app
# Web UI will be available at http://localhost:10001
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

# Run with coverage
pytest --cov=packages --cov-report=html
```

### Environment Variables

Key environment variables (see `.env.example` for complete list):

- `DATABASE_URL`: PostgreSQL connection string
- `ENCRYPTION_KEY`: AES-256 encryption key for credentials (32 bytes)
- `SECRET_KEY`: Flask secret key for sessions
- `LOCALSTACK_ENDPOINT`: LocalStack endpoint URL
- `REQUIRE_HTTPS`: Enable/disable HTTPS enforcement (false for local dev)
- `SESSION_TIMEOUT_MINUTES`: Session inactivity timeout (default: 30)

**Security Note**: Never commit `.env` file or use default keys in production!

### Generating Secure Keys

```bash
# Generate encryption key (32 bytes for AES-256)
python -c "import secrets; print(secrets.token_hex(32))"

# Generate secret key
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

## Architecture

The application follows a modular monorepo architecture:

- **Web UI**: Flask-based web interface with Bulma CSS
- **API Layer**: RESTful API with Flask
- **TCO Engine**: Cost calculation logic for on-premises and AWS
- **Pricing Service**: AWS Pricing API integration with daily updates
- **Q&A Service**: Conversational assistance for cost analysis
- **Provisioner**: Terraform-based infrastructure provisioning
- **Monitoring**: Metrics collection and dashboard
- **Security**: Authentication, encryption, and input sanitization

## Services

### API Service (Port 10000)

REST API endpoints:
- `/api/auth/*` - Authentication (register, login, logout)
- `/api/configurations/*` - Configuration management
- `/api/tco/*` - TCO calculations
- `/api/provision/*` - Infrastructure provisioning
- `/api/qa/*` - Q&A service
- `/api/monitoring/*` - Monitoring metrics

### Web UI Service (Port 10001)

Web interface pages:
- `/` - Configuration input
- `/tco-results/<id>` - TCO comparison results
- `/qa/<id>` - Q&A chat interface
- `/provision/<id>` - Cloud path selection and provisioning
- `/monitoring` - Monitoring dashboard
- `/login` - User login
- `/register` - User registration

### LocalStack (Port 4566)

AWS service emulation:
- EC2 instances
- EBS volumes
- S3 storage
- ECS containers
- Pricing API

### Database (Port 5432)

PostgreSQL database storing:
- User accounts and sessions
- Configurations and TCO results
- AWS pricing data
- Provisioned resources
- Terraform state
- Monitoring metrics

## Troubleshooting

### Docker Compose Issues

```bash
# Rebuild containers after code changes
docker-compose up -d --build

# Check service health
docker-compose ps

# View service logs
docker-compose logs -f <service-name>
```

### Database Connection Issues

```bash
# Check database is running
docker-compose ps database

# Connect to database
docker-compose exec database psql -U hybrid_cloud_user -d hybrid_cloud
```

### LocalStack Issues

```bash
# Check LocalStack health
curl http://localhost:4566/_localstack/health

# View LocalStack logs
docker-compose logs -f localstack
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## License

MIT
