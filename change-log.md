# Change Log

## 2024-01-XX - Project Initialization

### Description
Initialized monorepo structure for Hybrid Cloud Controller project with packages directory, test directories, and configuration files.

### Files Created
- `pyproject.toml` - Project metadata and build configuration
- `requirements.piptools` - Production dependencies
- `requirements-development.piptools` - Development dependencies
- `pytest.ini` - Test configuration
- `ruff.toml` - Formatting and linting rules
- `change-log.md` - This file
- Directory structure: `packages/`, `tests/unit/`, `tests/property/`, `tests/integration/`

## 2024-01-XX - Database Package Setup

### Description
Created database package with SQLAlchemy models and Alembic migration setup. Implemented all 11 database models (UserModel, SessionModel, ConfigurationModel, TCOResultModel, PricingDataModel, ProvisionModel, ResourceModel, TerraformStateModel, CredentialModel, MetricsModel, ConversationModel) with proper relationships and constraints.

### Files Created
- `packages/database/__init__.py` - Database initialization with engine and session management
- `packages/database/models.py` - All SQLAlchemy models matching design schema
- `packages/database/migrations/alembic.ini` - Alembic configuration
- `packages/database/migrations/env.py` - Alembic environment setup
- `packages/database/migrations/script.py.mako` - Migration template
- `packages/database/migrations/README.md` - Migration usage documentation
- `packages/database/migrations/versions/` - Directory for migration files

### Files Modified
- `requirements.piptools` - Added alembic>=1.13.0
- `pyproject.toml` - Added alembic>=1.13.0 to dependencies

### Requirements Validated
- 9.1: Store AWS pricing data with timestamps
- 9.2: Store user Configuration records
- 9.3: Store provisioned resource records
- 9.4: Store TCO calculation results
- 9.6: Support database schema migrations

## 2024-01-XX - Authentication Service Implementation

### Description
Implemented authentication service with user registration, login, session management, and 30-minute inactivity timeout. Uses bcrypt for password hashing and secure random tokens for sessions.

### Files Created
- `packages/security/__init__.py` - Security package initialization
- `packages/security/auth.py` - Authentication functions (register_user, authenticate, validate_session, invalidate_session, check_session_timeout)
- `tests/conftest.py` - Shared test fixtures for database sessions
- `tests/unit/test_auth.py` - Comprehensive unit tests for authentication service (20 tests)

### Requirements Validated
- 12.1: User registration form accepting username and password
- 12.2: Password hashing using bcrypt before database storage
- 12.3: Session creation with token on valid login
- 12.4: Session invalidation on logout
- 12.5: 30-minute inactivity timeout for sessions

## 2024-01-XX - Credential Encryption Service Implementation

### Description
Implemented AES-256 encryption service for securing credentials (AWS API keys, registry credentials, SSH keys) at rest. Uses AES-256-CBC with random initialization vectors and retrieves encryption keys from environment variables.

### Files Created
- `packages/security/crypto.py` - Encryption functions (encrypt_credential, decrypt_credential, get_encryption_key)
- `tests/unit/test_crypto.py` - Comprehensive unit tests for encryption service (18 tests)

### Requirements Validated
- 12.6: Store AWS API keys encrypted at rest using AES-256
- 12.7: Store container registry credentials encrypted at rest using AES-256
- 12.8: Store SSH keys and access credentials encrypted at rest using AES-256
- 12.9: Retrieve encryption keys from environment variables

## 2024-01-XX - Input Sanitization Implementation

### Description
Implemented input sanitization and container image URL validation to prevent SQL injection, XSS attacks, and validate container image URLs for Docker Hub, ECR, and private registries. Provides defense-in-depth security measures.

### Files Created
- `packages/security/sanitizer.py` - Sanitization functions (sanitize_input, validate_container_image_url)
- `tests/unit/test_sanitizer.py` - Comprehensive unit tests for sanitization (29 tests)

### Files Modified
- `packages/security/__init__.py` - Added sanitizer module export

### Requirements Validated
- 12.12: Sanitize user input to prevent SQL injection and XSS attacks
- 12.13: Validate container image URL format and allowed registry domains
- 11.1: Container image URL input field for CaaS deployments

## 2024-01-XX - Configuration Validation Implementation

### Description
Implemented configuration validation for TCO Engine to validate compute specs, storage specs, network specs, and workload profiles. Returns specific error messages for each invalid field.

### Files Created
- `packages/tco_engine/__init__.py` - TCO Engine package initialization
- `packages/tco_engine/validation.py` - Configuration validation function with ValidationError exception
- `tests/unit/test_validation.py` - Comprehensive unit tests for validation (16 tests)

### Requirements Validated
- 1.5: Validate all required fields are populated with valid values
- 1.6: Display specific validation error messages for each invalid field

## 2024-01-XX - On-Premises Cost Calculator Implementation

### Description
Implemented on-premises cost calculator with functions to calculate hardware, power, cooling, maintenance, and data transfer costs. Uses industry-standard estimates: hardware costs based on CPU/RAM/storage specs, power consumption at 50W per core, cooling at 40% of power costs, maintenance at 17.5% of hardware costs annually, and bandwidth/leased line costs at $3 per Mbps.

### Files Created
- `packages/tco_engine/on_prem_costs.py` - On-premises cost calculation functions (calculate_hardware_costs, calculate_power_costs, calculate_cooling_costs, calculate_maintenance_costs, calculate_data_transfer_costs)
- `tests/unit/test_on_prem_costs.py` - Comprehensive unit tests for cost calculations (15 tests)

### Requirements Validated
- 2.1: Calculate on-premises TCO including hardware, power, cooling, and maintenance costs
- 2.6: Include data transfer costs in on-premises calculations

## 2024-01-XX - TCO Calculation Engine Implementation

### Description
Implemented the main TCO calculation engine that orchestrates complete TCO calculations by combining on-premises and AWS cost calculations. The engine generates itemized cost breakdowns with line items for each cost category and projects costs for 1-year, 3-year, and 5-year periods. Includes data classes for Configuration, AWSPricing, CostLineItem, and CostBreakdown.

### Files Created
- `packages/tco_engine/calculator.py` - Main TCO calculation orchestrator (calculate_tco, project_costs, _calculate_on_prem_breakdown, _calculate_aws_breakdown)
- `tests/unit/test_calculator.py` - Comprehensive unit tests for TCO calculator (14 tests)

### Key Features
- Orchestrates on-premises and AWS cost calculations for multiple time periods
- Generates itemized cost breakdowns with specific line items for each category
- On-premises categories: Hardware, Power, Cooling, Maintenance, Data Transfer
- AWS categories: EC2, EBS, S3, Data Transfer
- Projects costs for 1, 3, and 5 years with proper scaling (hardware is one-time, other costs are recurring)
- Ensures 3-year >= 1-year and 5-year >= 3-year for recurring costs

### Requirements Validated
- 2.1: Calculate on-premises TCO including hardware, power, cooling, and maintenance costs
- 2.2: Calculate AWS TCO using current pricing data
- 2.3: Compute TCO projections for 1-year, 3-year, and 5-year periods
- 2.4: Itemize cost breakdowns by category for both options
- 2.5: Display side-by-side comparison of on-premises and AWS costs
- 2.6: Include data transfer costs in both calculations

## 2024-01-XX - Pricing Service Implementation

### Description
Implemented AWS pricing data fetcher that retrieves pricing from AWS Pricing API for EC2, EBS, S3, and data transfer services. Stores pricing data with timestamps in the database for historical tracking. Provides fallback pricing values when API calls fail for individual services. Includes functions to retrieve current pricing and query historical pricing data for trend analysis.

### Files Created
- `packages/pricing_service/__init__.py` - Pricing service package initialization
- `packages/pricing_service/fetcher.py` - Pricing data fetcher (fetch_pricing_data, get_current_pricing, get_pricing_history)
- `tests/unit/test_pricing_service.py` - Comprehensive unit tests for pricing service (10 tests)

### Key Features
- Fetches EC2 pricing for 11 common instance types (t3, m5, c5, r5 families)
- Fetches EBS pricing for 5 volume types (gp3, gp2, io2, st1, sc1)
- Fetches S3 pricing for 5 storage classes (STANDARD, INTELLIGENT_TIERING, STANDARD_IA, ONEZONE_IA, GLACIER)
- Fetches data transfer pricing (internet egress, inter-region, inter-AZ, inbound)
- Uses fallback pricing values when individual API calls fail
- Stores pricing data with timestamps in PricingDataModel
- Serializes/deserializes Decimal values to/from JSON for database storage
- Retrieves most recent pricing data from database
- Queries historical pricing data within date ranges for trend analysis
- Logs warnings when using fallback values

### Requirements Validated
- 3.1: Retrieve pricing data from AWS Pricing API for EC2, EBS, S3, and data transfer services
- 3.3: Store pricing data in database with timestamp
- 3.4: Retain historical pricing data for trend analysis
- 3.5: Use most recent cached pricing data when API unavailable (via fallback values)
- 3.6: Return most recent pricing record from database when TCO Engine requests pricing data

## 2024-01-XX - Pricing Scheduler Implementation

### Description
Implemented pricing scheduler that automatically fetches AWS pricing data every 24 hours with retry logic and exponential backoff on failure. The scheduler runs in a background thread and executes pricing fetches with up to 6 retry attempts using exponential backoff delays (1, 2, 4, 8, 16, 32 minutes). Falls back to cached pricing data if all retries fail.

### Files Created
- `packages/pricing_service/scheduler.py` - Pricing scheduler (PricingScheduler class, schedule_daily_fetch, execute_fetch, get_scheduler, stop_scheduler)
- `tests/unit/test_scheduler.py` - Comprehensive unit tests for scheduler (13 tests)

### Files Modified
- `pytest.ini` - Added asyncio marker for async test support

### Key Features
- Background thread-based scheduler that runs continuously
- Executes pricing fetch immediately on start, then every 24 hours
- Implements exponential backoff retry logic: 1, 2, 4, 8, 16, 32 minutes
- Maximum of 6 retry attempts (total ~63 minutes of retries)
- Falls back to cached pricing data if all retries fail
- Logs all fetch attempts, failures, and cache usage
- Provides singleton scheduler instance via get_scheduler()
- Graceful shutdown with stop() method
- Returns detailed result dict with success status, data, error, attempts, and cached_used flag

### Requirements Validated
- 3.2: Execute pricing data retrieval once every 24 hours
- 3.5: Use most recent cached pricing data when API unavailable and log warning

## 2024-01-XX - Conversation Manager Implementation

### Description
Implemented conversation manager for Q&A service that maintains conversation history per session. Stores messages with role (user/assistant), content, and timestamp in the database. Provides functions to add messages, retrieve conversation history in chronological order, and clear history for a session.

### Files Created
- `packages/qa_service/context.py` - Conversation manager functions (add_message, get_history, clear_history)
- `tests/unit/test_conversation_manager.py` - Comprehensive unit tests for conversation manager (15 tests)

### Files Modified
- `packages/qa_service/__init__.py` - Added conversation manager function exports

### Key Features
- Add messages to conversation history with role validation (user/assistant only)
- Store messages with unique ID, session ID, configuration ID, role, content, and timestamp
- Retrieve conversation history in chronological order (sorted by timestamp)
- Return history as list of dictionaries with id, role, content, and ISO format timestamp
- Clear all messages for a specific session
- Session isolation - history is maintained separately per session
- Async function signatures for future async database support

### Requirements Validated
- 4.5: Display Q&A responses in conversational format (via history retrieval)
- 4.6: Maintain conversation history for the current user session
