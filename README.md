# MultiAgent Customer Support System

[![CI/CD Pipeline](https://github.com/phfarath/customer_support_multiAgent/actions/workflows/ci.yml/badge.svg)](https://github.com/phfarath/customer_support_multiAgent/actions/workflows/ci.yml)
[![codecov](https://codecov.io/gh/phfarath/customer_support_multiAgent/branch/main/graph/badge.svg)](https://codecov.io/gh/phfarath/customer_support_multiAgent)
[![Security](https://img.shields.io/badge/security-bandit-yellow.svg)](https://github.com/PyCQA/bandit)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-3100/)
[![License: MIT](https://img.shields.io/badge/License-MIT-green.svg)](https://opensource.org/licenses/MIT)

AI-powered customer support system using MongoDB + Python with FastAPI.

## Architecture

### 4 Specialized Agents

1. **Triage Agent** - Analyzes tickets and determines priority, category, and sentiment
2. **Router Agent** - Routes tickets to appropriate teams (billing, tech, general)
3. **Resolver Agent** - Generates responses and attempts to resolve tickets
4. **Escalator Agent** - Decides when to escalate tickets to human agents

### MongoDB Collections

- `tickets` - Ticket information
- `agent_states` - Agent decision states
- `interactions` - Ticket interactions
- `routing_decisions` - Routing decisions
- `audit_logs` - Complete audit trail

## Project Structure

```
MultiAgent/
├── main.py                 # FastAPI application entry point
├── requirements.txt         # Python dependencies
├── .env.example           # Environment configuration template
├── src/
│   ├── config.py          # Application settings
│   ├── agents/            # Agent implementations
│   │   ├── base_agent.py
│   │   ├── triage_agent.py
│   │   ├── router_agent.py
│   │   ├── resolver_agent.py
│   │   └── escalator_agent.py
│   ├── api/               # FastAPI routes
│   │   └── routes.py
│   ├── database/          # MongoDB connection
│   │   ├── connection.py
│   │   └── transactions.py
│   ├── models/            # Pydantic models
│   │   ├── ticket.py
│   │   ├── agent_state.py
│   │   ├── interaction.py
│   │   ├── routing_decision.py
│   │   └── audit_log.py
│   └── utils/             # Utilities
│       └── pipeline.py    # Agent pipeline orchestrator
├── scripts/               # Utility scripts
│   └── load_test_data.py
├── test_data/            # Test data
│   └── tickets.json
└── logs/                 # Application logs
```

## Installation

1. Clone the repository
2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Configure environment:
```bash
cp .env.example .env
# Edit .env with your MongoDB URI and other settings
```

## Running the Application

Start the FastAPI server:
```bash
python main.py
```

Or using uvicorn:
```bash
uvicorn main:app --reload
```

## Authentication

**All API endpoints require authentication via API Key** (except `/docs`, `/health`, and `/telegram/webhook`).

### Creating Your First API Key

```bash
python scripts/create_initial_api_key.py --company-id your_company_id --name "Initial Key"
```

This will output an API key like: `sk_AbCdEfGhIjKlMnOpQrStUvWxYz1234567890`

**Important:** Save this key securely. It won't be shown again.

### Using API Keys

Include the `X-API-Key` header in all API requests:

```bash
curl -H "X-API-Key: sk_YOUR_API_KEY" http://localhost:8000/api/tickets
```

## API Endpoints

**Note:** All endpoints below require the `X-API-Key` header.

### Create Ticket
```http
POST /api/tickets
X-API-Key: sk_YOUR_API_KEY
Content-Type: application/json

{
  "ticket_id": "TICKET-001",
  "customer_id": "CUST-001",
  "channel": "email",
  "subject": "Issue description",
  "description": "Full issue description..."
}
```

### Run Pipeline
```http
POST /api/run_pipeline/{ticket_id}
X-API-Key: sk_YOUR_API_KEY
```

### Get Ticket
```http
GET /api/tickets/{ticket_id}
X-API-Key: sk_YOUR_API_KEY
```

### Get Audit Trail
```http
GET /api/tickets/{ticket_id}/audit
X-API-Key: sk_YOUR_API_KEY
```

### List Tickets
```http
GET /api/tickets?status=open&priority=P1&limit=50
X-API-Key: sk_YOUR_API_KEY
```

### API Key Management

**List API Keys:**
```http
GET /api/keys
X-API-Key: sk_YOUR_API_KEY
```

**Create New API Key:**
```http
POST /api/keys
X-API-Key: sk_YOUR_API_KEY
Content-Type: application/json

{
  "company_id": "your_company_id",
  "name": "Production Key",
  "permissions": ["read", "write"]
}
```

**Revoke API Key:**
```http
DELETE /api/keys/{key_id}
X-API-Key: sk_YOUR_API_KEY
```

## Dashboard Authentication

The Streamlit Dashboard requires authentication with JWT tokens.

### Creating Dashboard Users

Create your first user:
```bash
python scripts/create_dashboard_user.py \
    --email admin@company.com \
    --password SecurePassword123! \
    --company-id your_company_id \
    --full-name "Admin User" \
    --role admin
```

**Roles:**
- `admin`: Full access (can modify bot config, products, respond to tickets)
- `operator`: Can respond to tickets and view configs (default)

### Accessing the Dashboard

1. Start the dashboard:
```bash
streamlit run src/dashboard/app.py
```

2. Open http://localhost:8501

3. Login with email and password

**Features:**
- JWT-based authentication (24h token expiration)
- Company isolation (users only see their company's data)
- Secure password hashing with bcrypt
- Session management with automatic token verification

## Loading Test Data

Load test tickets into MongoDB:
```bash
python scripts/load_test_data.py
```

## Escalation Rules

Tickets are escalated to human agents if ANY:
- Priority is P1 AND interactions_count > 2
- Sentiment score < -0.7 (very angry customer)
- Resolver confidence < 0.6
- Time since creation > 4 hours (SLA breach)

## Configuration

Edit `.env` file to configure:
- MongoDB connection
- OpenAI API key (for AI agents)
- API host/port
- Escalation thresholds
- Logging level

## Test Tickets

5 test tickets are provided in `test_data/tickets.json`:
- TICKET-001: Duplicate charge → P1 → billing → resolved
- TICKET-002: App crash → P2 → tech → escalated (low confidence)
- TICKET-003: Help request → P3 → general → resolved
- TICKET-004: Angry customer → P1 → escalated (negative sentiment)
- TICKET-005: Urgent refund → P1 → billing → escalated (SLA breach)

## Development

### Running Tests

```bash
# Install dev dependencies
pip install -r requirements-dev.txt

# Run tests with coverage
pytest

# Run tests without coverage
pytest --no-cov

# Run specific test markers
pytest -m unit          # Unit tests only
pytest -m integration   # Integration tests only
```

### Load Testing

```bash
# Basic load test (50 users, 60 seconds)
./scripts/run_load_test.sh

# Custom parameters
./scripts/run_load_test.sh 100 10 120s  # 100 users, 10/s spawn, 120s

# Stress test preset
./scripts/run_load_test.sh stress

# Interactive mode (web UI)
locust -f tests/load/locustfile.py --host http://localhost:8000
```

### Code Quality

```bash
# Lint code
ruff check src/ tests/

# Format code
black src/ tests/

# Type checking
mypy src/

# Security scan
bandit -r src/
```

## CI/CD Pipeline

The project uses GitHub Actions for continuous integration:

| Job | Description |
|-----|-------------|
| **Lint & Format** | Runs Ruff, Black, and MyPy |
| **Tests & Coverage** | Runs pytest with 70% minimum coverage |
| **Security Scan** | Bandit, Safety, and Gitleaks |
| **Docker Build** | Builds and scans image with Trivy |
| **Deploy Check** | Validates deployment readiness |

### Manual Load Testing

Trigger a load test from GitHub Actions:
1. Go to Actions → Load Testing
2. Click "Run workflow"
3. Configure users, spawn rate, and duration

## Docker

### Build and Run

```bash
# Build image
docker build -t customer-support .

# Run with docker-compose
docker-compose up -d

# View logs
docker-compose logs -f api
```

### Health Check

```bash
curl http://localhost:8000/api/health
```
