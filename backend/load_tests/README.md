# Priotag Backend Load Testing

Professional load testing suite for the Priotag backend application. This suite helps you benchmark your server's performance and determine how many concurrent users it can handle.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Test Scenarios](#test-scenarios)
- [Configuration](#configuration)
- [Understanding Results](#understanding-results)
- [Advanced Usage](#advanced-usage)
- [Cleanup](#cleanup)
- [Best Practices](#best-practices)

## Overview

This load testing suite uses [Locust](https://locust.io/), a modern, scalable load testing framework. It simulates realistic user behavior including:

- User registration
- Authentication (login/logout)
- Priority creation and updates
- Priority retrieval
- Account management
- Session verification

## Features

- **Multiple User Types**: Regular users and intensive users for different testing scenarios
- **Realistic Workflows**: Simulates actual user behavior patterns
- **Comprehensive Metrics**: Response times, throughput (RPS), error rates
- **Multiple Test Scenarios**: Basic load, stress testing, spike testing
- **Professional Reports**: HTML reports and CSV data exports
- **Easy Configuration**: Environment variables and command-line options
- **Web UI**: Real-time monitoring and control through browser interface

## Installation

### Prerequisites

- Python 3.8 or higher
- pip (Python package manager)
- Access to Priotag backend (running locally or deployed)

## Quick Start

### 1. Basic Load Test (Recommended First Test)

Test with 20 concurrent users for 5 minutes:

```bash
# From the load_tests directory
./scripts/run_basic.sh http://localhost:8000
```

Replace `http://localhost:8000` with your backend URL.

### 2. Web UI Mode (Interactive)

For real-time control and monitoring:

```bash
./scripts/run_web_ui.sh http://localhost:8000
```

Then open your browser to `http://localhost:8089` and configure:
- Number of users
- Spawn rate (users/second)
- Host URL

## Test Scenarios

### Basic Load Test

**Purpose**: Establish baseline performance
**Users**: 20 concurrent users
**Duration**: 5 minutes
**Spawn Rate**: 2 users/second

```bash
./scripts/run_basic.sh http://localhost:8000
```

**Environment Variables**:
```bash
LOAD_TEST_USERS=20 \
LOAD_TEST_SPAWN_RATE=2 \
LOAD_TEST_RUN_TIME=5m \
./scripts/run_basic.sh http://localhost:8000
```

### Stress Test

**Purpose**: Find system breaking point
**Users**: 100 concurrent users
**Duration**: 10 minutes
**Spawn Rate**: 5 users/second

```bash
./scripts/run_stress.sh http://localhost:8000
```

**Environment Variables**:
```bash
LOAD_TEST_STRESS_USERS=100 \
LOAD_TEST_SPAWN_RATE=5 \
LOAD_TEST_RUN_TIME=10m \
./scripts/run_stress.sh http://localhost:8000
```

### Spike Test

**Purpose**: Test sudden traffic spikes
**Users**: 50 concurrent users
**Duration**: 3 minutes
**Spawn Rate**: 25 users/second (very rapid)

```bash
./scripts/run_spike.sh http://localhost:8000
```

**Environment Variables**:
```bash
LOAD_TEST_SPIKE_USERS=50 \
LOAD_TEST_SPIKE_SPAWN_RATE=25 \
LOAD_TEST_RUN_TIME=3m \
./scripts/run_spike.sh http://localhost:8000
```

## Configuration

### Environment Variables

All tests can be configured using environment variables:

| Variable                  | Description                             | Default                 |
| ------------------------- | --------------------------------------- | ----------------------- |
| `LOAD_TEST_BASE_URL`      | Backend URL                             | `http://localhost:8000` |
| `LOAD_TEST_MAGIC_WORD`    | Institution magic word for registration | `test-magic-word`       |
| `LOAD_TEST_USER_PREFIX`   | Prefix for test usernames               | `loadtest_user`         |
| `LOAD_TEST_USER_PASSWORD` | Password for test users                 | `TestPassword123!`      |
| `LOAD_TEST_MIN_WAIT`      | Min wait between tasks (ms)             | `1000`                  |
| `LOAD_TEST_MAX_WAIT`      | Max wait between tasks (ms)             | `3000`                  |
| `LOAD_TEST_USERS`         | Number of concurrent users              | `20`                    |
| `LOAD_TEST_SPAWN_RATE`    | Users spawned per second                | `2`                     |
| `LOAD_TEST_RUN_TIME`      | Test duration (e.g., `5m`, `1h`)        | `5m`                    |

### Example: Custom Configuration

```bash
# Test with 50 users, spawning 10/second, running for 15 minutes
LOAD_TEST_USERS=50 \
LOAD_TEST_SPAWN_RATE=10 \
LOAD_TEST_RUN_TIME=15m \
LOAD_TEST_MAGIC_WORD=your-magic-word \
./scripts/run_basic.sh https://your-server.com
```

### Configuration File

Edit `config.py` to change default settings:

```python
class LoadTestConfig:
    BASE_URL = "http://localhost:8000"
    MAGIC_WORD = "your-magic-word"
    USER_PREFIX = "loadtest_user"
    # ... other settings
```

## Understanding Results

### Reports Location

After each test run, reports are generated in the `reports/` directory:

```
reports/
├── basic_load_test_20231215_143022.html    # HTML report
├── basic_load_test_20231215_143022_stats.csv      # Stats CSV
├── basic_load_test_20231215_143022_failures.csv   # Failures CSV
└── basic_load_test_20231215_143022_exceptions.csv # Exceptions CSV
```

### Key Metrics

#### 1. Requests Per Second (RPS)

- **What it means**: Number of requests the server handles per second
- **Good**: Higher is better (e.g., 100+ RPS)
- **Warning**: Declining RPS under load indicates performance issues

#### 2. Response Time

- **Median (50th percentile)**: Typical user experience
  - Good: < 200ms
  - Acceptable: 200-500ms
  - Slow: > 500ms

- **95th percentile**: What most users experience
  - Good: < 500ms
  - Acceptable: 500ms-1s
  - Slow: > 1s

- **99th percentile**: Worst-case for most users
  - Good: < 1s
  - Acceptable: 1-2s
  - Slow: > 2s

#### 3. Error Rate

- **What it means**: Percentage of failed requests
- **Good**: 0% errors
- **Acceptable**: < 0.1% for non-critical operations
- **Problem**: > 1% indicates issues

#### 4. Concurrent Users Supported

- **How to find**: Number of users when response times stay acceptable
- **Example**: If response times stay under 500ms with 50 users but jump to 2s with 100 users, your limit is around 50-75 concurrent users

### Example Report Interpretation

```
Total requests: 15,234
Total failures: 12 (0.08%)
Average response time: 234ms
Median response time: 189ms
95th percentile: 456ms
99th percentile: 891ms
RPS: 50.78
```

**Analysis**:
- ✅ Low error rate (0.08%)
- ✅ Good average response time (234ms)
- ✅ Acceptable 95th percentile (456ms)
- ⚠️ 99th percentile approaching 1s (watch this)
- ✅ Good throughput (50 RPS)

**Conclusion**: System performing well, can likely handle more load.

## Advanced Usage

### Custom User Behaviors

Edit `locustfile.py` to add custom task behaviors:

```python
@task(5)  # Weight = 5 (higher weight = more frequent)
def my_custom_operation(self):
    """Custom operation to test."""
    if not self.session.is_authenticated():
        return

    self.client.get(
        config.get_api_url("my-endpoint"),
        cookies=self.session.get_cookie_dict(),
        name="/api/v1/my-endpoint",
    )
```

### Running Distributed Tests

For very high load, run Locust in distributed mode:

**Master node**:
```bash
locust -f locustfile.py --master --host http://your-server.com
```

**Worker nodes** (run on multiple machines):
```bash
locust -f locustfile.py --worker --master-host <master-ip>
```

### Custom Test Scenarios

Create custom scenarios by importing user classes:

```python
from locustfile import PriotagUser, IntensiveUser

# Run only intensive users
locust -f locustfile.py --host http://localhost:8000 IntensiveUser
```

### Monitoring During Tests

Watch server resources while testing:

**CPU and Memory**:
```bash
top
# or
htop
```

**Docker stats** (if using Docker):
```bash
docker stats
```

**Backend logs**:
```bash
docker compose logs -f backend
# or
tail -f /path/to/backend.log
```

## Cleanup

### Remove Test Users

After testing, clean up test users from the database:

```bash
# Dry run (see what would be deleted)
python scripts/cleanup_users.py --dry-run

# Actually delete users
python scripts/cleanup_users.py

# Custom prefix
python scripts/cleanup_users.py --prefix my_test_user

# Custom host
python scripts/cleanup_users.py --host https://your-server.com
```

**Options**:
- `--prefix`: Username prefix to match (default: `loadtest_user`)
- `--host`: Backend URL (default: `http://localhost:8000`)
- `--max-users`: Maximum users to check (default: 1000)
- `--dry-run`: Preview deletions without actually deleting

## Best Practices

### 1. Start Small

Begin with basic load tests (10-20 users) to establish baseline:

```bash
LOAD_TEST_USERS=10 ./scripts/run_basic.sh http://localhost:8000
```

### 2. Gradual Increase

Increase load gradually to find limits:

```bash
# Test with 20, 50, 100, 200 users
for users in 20 50 100 200; do
    echo "Testing with $users users..."
    LOAD_TEST_USERS=$users ./scripts/run_basic.sh http://localhost:8000
    sleep 60  # Wait between tests
done
```

### 3. Monitor Server Resources

Always monitor your server during tests:
- CPU usage
- Memory usage
- Disk I/O
- Network bandwidth
- Database connections
- Redis memory

### 4. Test in Staging First

Never run heavy load tests on production without:
- Testing in staging environment first
- Scheduling during low-traffic periods
- Having rollback plan ready
- Monitoring alerts configured

### 5. Analyze Failures

When errors occur, examine:

```bash
# Check failures CSV
cat reports/stress_test_*_failures.csv

# Check backend logs
docker compose logs backend | grep ERROR
```

### 6. Test Realistic Scenarios

Configure wait times to match real user behavior:

```bash
# Faster users (power users)
LOAD_TEST_MIN_WAIT=500 \
LOAD_TEST_MAX_WAIT=1500 \
./scripts/run_basic.sh http://localhost:8000

# Slower users (casual browsing)
LOAD_TEST_MIN_WAIT=3000 \
LOAD_TEST_MAX_WAIT=10000 \
./scripts/run_basic.sh http://localhost:8000
```

### 7. Document Results

Keep a record of test results:

```bash
# Create results log
cat >> results_log.txt << EOF
Date: $(date)
Test: Basic Load Test
Users: 50
Duration: 5m
Result: Success
RPS: 75.3
Avg Response: 145ms
95th percentile: 387ms
Errors: 0.02%
---
EOF
```

## Troubleshooting

### Issue: "Failed to verify magic word"

**Solution**: Set the correct magic word:
```bash
LOAD_TEST_MAGIC_WORD=your-actual-magic-word ./scripts/run_basic.sh
```

### Issue: High error rate (> 5%)

**Possible causes**:
- Server overloaded (reduce concurrent users)
- Rate limiting triggered (increase wait times)
- Backend/database issues (check logs)

**Solution**:
```bash
# Reduce load and increase wait times
LOAD_TEST_USERS=10 \
LOAD_TEST_MIN_WAIT=2000 \
LOAD_TEST_MAX_WAIT=5000 \
./scripts/run_basic.sh http://localhost:8000
```

### Issue: "Connection refused"

**Solution**: Ensure backend is running and accessible:
```bash
# Test backend is reachable
curl http://localhost:8000/api/v1/health

# Check if backend is running
docker compose ps
```

### Issue: Tests run too long

**Solution**: Set shorter duration:
```bash
LOAD_TEST_RUN_TIME=2m ./scripts/run_basic.sh http://localhost:8000
```

## Directory Structure

```
load_tests/
├── locustfile.py           # Main Locust test file
├── config.py               # Configuration settings
├── utils.py                # Helper utilities
├── requirements.txt        # Python dependencies
├── README.md              # This file
├── scripts/
│   ├── run_basic.sh       # Basic load test
│   ├── run_stress.sh      # Stress test
│   ├── run_spike.sh       # Spike test
│   ├── run_web_ui.sh      # Web UI mode
│   └── cleanup_users.py   # User cleanup script
└── reports/               # Generated test reports
    └── (generated files)
```

## Further Reading

- [Locust Documentation](https://docs.locust.io/)
- [Load Testing Best Practices](https://docs.locust.io/en/stable/writing-a-locustfile.html)
- [Interpreting Performance Metrics](https://www.keycdn.com/blog/website-performance-metrics)

## Support

For issues or questions:
1. Check troubleshooting section above
2. Review backend logs
3. Consult Locust documentation
4. Open an issue in the project repository

---

**Happy Load Testing! 🚀**
