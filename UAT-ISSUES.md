# UAT Issues & Observations
**Session Date**: 2026-03-09  
**Tester**: User  
**Status**: In Progress

---

## UI/UX Issues

### Issue #1: Inconsistent Card Heights on Home Page
**Priority**: Low  
**Severity**: Minor (Cosmetic)  
**Status**: Open

**Description**:
The "TCO Analysis" card/banner is taller than the "Provisioning" and "Monitoring" cards on the home page, creating visual inconsistency.

**Location**: Home page (http://localhost:10001)

**Expected**:
All three feature cards should have equal height for visual consistency.

**Actual**:
"TCO Analysis" card is noticeably taller than the other two cards.

**Screenshot**: Provided

**Suggested Fix**:
- Add CSS to ensure equal card heights (e.g., `min-height` or flexbox `align-items: stretch`)
- Or adjust text content to be similar length across all cards

**Workaround**: None needed - purely cosmetic

---

## Functional Issues

### Issue #2: Web UI Cannot Connect to API (Wrong Hostname)
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
Web UI routes were hardcoded to connect to API at `http://localhost:10000` but inside Docker containers, services must use service names (e.g., `http://api:10000`).

**Location**: 
- `packages/web_ui/routes/auth.py`
- `packages/web_ui/routes/configuration.py`

**Error Message**: "Unable to connect to authentication service"

**Expected**:
Web UI should connect to API using Docker service name: `http://api:10000`

**Actual**:
Web UI was trying to connect to `http://localhost:10000` (doesn't work in Docker)

**Fix Applied**:
Changed to use environment variable with default: `API_BASE_URL = os.getenv("API_BASE_URL", "http://api:10000")`

**Status**: ✅ Fixed

---

### Issue #3: Database Not Initialized on Startup
**Priority**: Critical  
**Severity**: Blocker  
**Status**: ✅ Fixed

**Description**:
API was not initializing the database or creating tables on startup, causing registration to fail with "Database not initialized" error.

**Location**: `packages/api/app.py`

**Error Message**: "Unexpected error during registration: Database not initialized. Call init_database() first."

**Expected**:
Database should be initialized and tables created automatically when API starts.

**Actual**:
- API didn't call `init_database()` on startup
- API didn't call `create_tables()` to create schema

**Fix Applied**:
1. Added `init_database()` and `create_tables()` calls in `create_app()` function
2. Added `psycopg2-binary` to requirements (PostgreSQL driver was missing)
3. Manually ran initialization to create all 11 database tables

**Status**: ✅ Fixed - All tables created

---

## Performance Issues

_[To be filled during UAT]_

---

## Security Issues

_[To be filled during UAT]_

---

## Notes

- Continue UAT and document all issues here
- Prioritize functional issues over cosmetic ones
- Batch UI fixes together at the end
