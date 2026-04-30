#!/usr/bin/env bash
# ─────────────────────────────────────────────────────────────────────────────
# run_tests.sh — Categorized test runner for ad-synth-ai
#
# Usage:
#   bash scripts/run_tests.sh              # unit + module (fast, default)
#   bash scripts/run_tests.sh unit         # unit tests only
#   bash scripts/run_tests.sh module       # module tests only
#   bash scripts/run_tests.sh system       # system tests (requires GOOGLE_API_KEY)
#   bash scripts/run_tests.sh connection   # connection/API key tests
#   bash scripts/run_tests.sh all          # everything
#
# Results are saved to: logs/test_results_<timestamp>.log
# ─────────────────────────────────────────────────────────────────────────────

set -euo pipefail

CATEGORY="${1:-default}"
TIMESTAMP=$(date +"%Y%m%d_%H%M%S")
mkdir -p logs
LOGFILE="logs/test_results_${TIMESTAMP}.log"

# ── Helpers ──────────────────────────────────────────────────────────────────
OVERALL_PASS=0
OVERALL_FAIL=0
SECTIONS_FAILED=()

header() {
    local title="$1"
    local line="══════════════════════════════════════════"
    echo ""                                        | tee -a "$LOGFILE"
    echo "$line"                                   | tee -a "$LOGFILE"
    echo "  $title"                                | tee -a "$LOGFILE"
    echo "$line"                                   | tee -a "$LOGFILE"
}

run_pytest() {
    local section="$1"
    shift
    local exit_code=0
    uv run pytest "$@" --tb=short -v 2>&1 | tee -a "$LOGFILE" || exit_code=$?

    # Extract pass/fail counts from pytest summary line
    local last_summary
    last_summary=$(grep -E "^(PASSED|FAILED|ERROR|=+ .* =+)" "$LOGFILE" | tail -5 | grep "passed\|failed\|error" | tail -1 || true)

    if [[ $exit_code -eq 0 ]]; then
        echo ""                                    | tee -a "$LOGFILE"
        echo "  ✓ $section — PASSED"              | tee -a "$LOGFILE"
        OVERALL_PASS=$((OVERALL_PASS + 1))
    else
        echo ""                                    | tee -a "$LOGFILE"
        echo "  ✗ $section — FAILED (exit $exit_code)" | tee -a "$LOGFILE"
        OVERALL_FAIL=$((OVERALL_FAIL + 1))
        SECTIONS_FAILED+=("$section")
    fi
    return 0  # Don't exit on individual test failure — collect all results
}

# ── Test Sections ─────────────────────────────────────────────────────────────
run_unit() {
    header "UNIT TESTS  (fast, fully mocked)"
    run_pytest "unit" tests/unit -m unit --ignore=tests/unit/test_agents
    run_pytest "unit-legacy" tests/unit/test_agents tests/unit/test_services tests/unit/test_tools
}

run_module() {
    header "MODULE TESTS  (real DB, mocked external services)"
    run_pytest "module" tests/module -m module
    run_pytest "module-integration" tests/integration
}

run_system() {
    header "SYSTEM TESTS  (end-to-end — requires GOOGLE_API_KEY)"
    if [[ -z "${GOOGLE_API_KEY:-}" ]]; then
        echo "  ⚠ GOOGLE_API_KEY not set — system tests will skip"   | tee -a "$LOGFILE"
    fi
    run_pytest "system" tests/system -m system -s --timeout=180
}

run_connection() {
    header "CONNECTION TESTS  (live API key checks)"
    echo "  API keys found:"                                          | tee -a "$LOGFILE"
    for var in GOOGLE_API_KEY GOOGLE_GENAI_USE_VERTEXAI GCP_PROJECT_ID \
               SERPAPI_API_KEY YOUTUBE_API_KEY REDDIT_CLIENT_ID \
               TWITTER_BEARER_TOKEN GOOGLE_CSE_API_KEY STORAGE_BACKEND GCS_BUCKET; do
        if [[ -n "${!var:-}" ]]; then
            echo "    ✓ $var"                                         | tee -a "$LOGFILE"
        else
            echo "    - $var (not set — tests will skip)"             | tee -a "$LOGFILE"
        fi
    done
    echo ""                                                           | tee -a "$LOGFILE"
    run_pytest "connection" tests/connections -m connection -s --timeout=30
}

# ── Summary ───────────────────────────────────────────────────────────────────
print_summary() {
    local divider="────────────────────────────────────────────"
    echo ""                                                           | tee -a "$LOGFILE"
    echo "$divider"                                                   | tee -a "$LOGFILE"
    echo "  OVERALL SUMMARY"                                         | tee -a "$LOGFILE"
    echo "$divider"                                                   | tee -a "$LOGFILE"
    echo "  Sections passed : $OVERALL_PASS"                        | tee -a "$LOGFILE"
    echo "  Sections failed : $OVERALL_FAIL"                        | tee -a "$LOGFILE"
    if [[ ${#SECTIONS_FAILED[@]} -gt 0 ]]; then
        echo "  Failed sections : ${SECTIONS_FAILED[*]}"            | tee -a "$LOGFILE"
    fi
    echo ""                                                           | tee -a "$LOGFILE"
    echo "  Log saved to: $LOGFILE"                                  | tee -a "$LOGFILE"
    echo "$divider"                                                   | tee -a "$LOGFILE"
    if [[ $OVERALL_FAIL -eq 0 ]]; then
        echo "  RESULT: ALL SECTIONS PASSED ✓"                      | tee -a "$LOGFILE"
    else
        echo "  RESULT: $OVERALL_FAIL SECTION(S) FAILED ✗"         | tee -a "$LOGFILE"
    fi
    echo "$divider"                                                   | tee -a "$LOGFILE"
}

# ── Entry point ───────────────────────────────────────────────────────────────
echo "ad-synth-ai test runner — $(date)"      | tee "$LOGFILE"
echo "Category: $CATEGORY"                     | tee -a "$LOGFILE"

case "$CATEGORY" in
    unit)        run_unit ;;
    module)      run_module ;;
    system)      run_system ;;
    connection)  run_connection ;;
    all)
        run_unit
        run_module
        run_system
        run_connection
        ;;
    default|"")
        run_unit
        run_module
        ;;
    *)
        echo "Unknown category: $CATEGORY"
        echo "Usage: bash scripts/run_tests.sh [unit|module|system|connection|all]"
        exit 1
        ;;
esac

print_summary

# Exit with failure if any section failed
[[ $OVERALL_FAIL -eq 0 ]]
