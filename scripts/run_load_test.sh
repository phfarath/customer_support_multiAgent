#!/bin/bash
#
# Load Testing Script for Customer Support MultiAgent
#
# Usage:
#   ./scripts/run_load_test.sh                    # Default: 50 users, 60s
#   ./scripts/run_load_test.sh 100 10 120s        # Custom: 100 users, spawn 10/s, 120s
#   ./scripts/run_load_test.sh stress             # Stress test preset
#   ./scripts/run_load_test.sh soak               # Soak test preset (long running)
#
# Environment Variables:
#   LOAD_TEST_HOST    Target host (default: http://localhost:8000)
#   TEST_API_KEY      API key for authenticated endpoints
#

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Default configuration
HOST=${LOAD_TEST_HOST:-http://localhost:8000}
LOCUSTFILE="tests/load/locustfile.py"
REPORTS_DIR="reports/load_tests"

# Print banner
echo -e "${BLUE}"
echo "=============================================="
echo "   Customer Support MultiAgent Load Testing  "
echo "=============================================="
echo -e "${NC}"

# Create reports directory
mkdir -p "$REPORTS_DIR"

# Check if locust is installed
if ! command -v locust &> /dev/null; then
    echo -e "${RED}Error: locust is not installed${NC}"
    echo "Install with: pip install locust"
    exit 1
fi

# Check if locustfile exists
if [ ! -f "$LOCUSTFILE" ]; then
    echo -e "${RED}Error: Locustfile not found at $LOCUSTFILE${NC}"
    exit 1
fi

# Parse arguments
case "${1:-default}" in
    stress)
        # Stress test: High load, short duration
        USERS=200
        SPAWN_RATE=20
        DURATION="120s"
        USER_CLASS="StressTestUser"
        echo -e "${YELLOW}Running STRESS TEST${NC}"
        ;;
    soak)
        # Soak test: Moderate load, long duration
        USERS=30
        SPAWN_RATE=2
        DURATION="30m"
        USER_CLASS="CustomerSupportUser"
        echo -e "${YELLOW}Running SOAK TEST (30 minutes)${NC}"
        ;;
    readonly)
        # Read-only test
        USERS=100
        SPAWN_RATE=10
        DURATION="60s"
        USER_CLASS="ReadOnlyUser"
        echo -e "${YELLOW}Running READ-ONLY TEST${NC}"
        ;;
    default|*)
        # Default or custom parameters
        USERS=${1:-50}
        SPAWN_RATE=${2:-5}
        DURATION=${3:-60s}
        USER_CLASS=""
        echo -e "${YELLOW}Running DEFAULT TEST${NC}"
        ;;
esac

# Generate timestamp for report files
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
HTML_REPORT="$REPORTS_DIR/report_${TIMESTAMP}.html"
CSV_PREFIX="$REPORTS_DIR/results_${TIMESTAMP}"

# Print configuration
echo ""
echo -e "${BLUE}Configuration:${NC}"
echo "  Host:        $HOST"
echo "  Users:       $USERS"
echo "  Spawn Rate:  $SPAWN_RATE/s"
echo "  Duration:    $DURATION"
if [ -n "$USER_CLASS" ]; then
    echo "  User Class:  $USER_CLASS"
fi
echo "  Report:      $HTML_REPORT"
echo ""

# Check if API is reachable
echo -e "${BLUE}Checking API health...${NC}"
if curl -sf "$HOST/api/health" > /dev/null 2>&1; then
    echo -e "${GREEN}API is healthy${NC}"
else
    echo -e "${RED}Warning: API health check failed. Continuing anyway...${NC}"
fi
echo ""

# Build locust command
LOCUST_CMD="locust -f $LOCUSTFILE --headless"
LOCUST_CMD="$LOCUST_CMD -u $USERS"
LOCUST_CMD="$LOCUST_CMD -r $SPAWN_RATE"
LOCUST_CMD="$LOCUST_CMD -t $DURATION"
LOCUST_CMD="$LOCUST_CMD --host $HOST"
LOCUST_CMD="$LOCUST_CMD --html $HTML_REPORT"
LOCUST_CMD="$LOCUST_CMD --csv $CSV_PREFIX"

if [ -n "$USER_CLASS" ]; then
    LOCUST_CMD="$LOCUST_CMD --class-picker --tags $USER_CLASS"
fi

# Run load test
echo -e "${BLUE}Starting load test...${NC}"
echo ""
eval $LOCUST_CMD

# Check results
echo ""
echo -e "${GREEN}=============================================="
echo "   Load Test Complete!"
echo "=============================================="
echo -e "${NC}"
echo ""
echo "Reports generated:"
echo "  HTML Report: $HTML_REPORT"
echo "  CSV Stats:   ${CSV_PREFIX}_stats.csv"
echo "  CSV History: ${CSV_PREFIX}_stats_history.csv"
echo ""

# Print quick summary from CSV if available
if [ -f "${CSV_PREFIX}_stats.csv" ]; then
    echo -e "${BLUE}Quick Summary:${NC}"
    echo "-------------------------------------------"
    # Extract and display key metrics
    tail -n 1 "${CSV_PREFIX}_stats.csv" | while IFS=',' read -r type name reqs fails median avg min max rps fail_rate; do
        if [ "$type" = "Aggregated" ] || [ -z "$type" ]; then
            echo "Total Requests:    $reqs"
            echo "Failed Requests:   $fails"
            echo "Average Response:  ${avg}ms"
            echo "95th Percentile:   (see HTML report)"
            echo "Requests/sec:      $rps"
        fi
    done
    echo "-------------------------------------------"
fi

echo ""
echo -e "${GREEN}Open the HTML report for detailed analysis:${NC}"
echo "  open $HTML_REPORT  # macOS"
echo "  xdg-open $HTML_REPORT  # Linux"
echo ""
