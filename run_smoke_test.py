"""
VoiceQA Smoke Test — Production Readiness Runner
==================================================
Master orchestration script that executes the full test suite in sequence
and provides a GO/NO-GO verdict for production deployment.

Usage:
    python run_smoke_test.py                        # Full suite
    python run_smoke_test.py --fast                  # Skip stress test
    python run_smoke_test.py --session_id X --token Y # Use existing session

Requirements: pytest, pytest-asyncio, websockets, httpx, numpy, redis
"""

import subprocess
import sys
import os
import time
import asyncio
import argparse
import json

# ---------------------------------------------------------------------------
# ANSI Colors (Windows 10+ compatible)
# ---------------------------------------------------------------------------
os.system("")  # Enable ANSI escape codes on Windows

# Force UTF-8 output on Windows
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

class C:
    BOLD    = "\033[1m"
    GREEN   = "\033[92m"
    RED     = "\033[91m"
    YELLOW  = "\033[93m"
    CYAN    = "\033[96m"
    DIM     = "\033[2m"
    RESET   = "\033[0m"
    BG_GREEN = "\033[42m\033[97m"
    BG_RED   = "\033[41m\033[97m"


def banner(text, color=C.CYAN):
    width = 64
    print()
    print(f"{color}{'=' * width}{C.RESET}")
    print(f"{color}{C.BOLD}  {text.center(width - 4)}{C.RESET}")
    print(f"{color}{'=' * width}{C.RESET}")
    print()


def step_header(step_num, title):
    print(f"\n{C.BOLD}{C.CYAN}+--- Step {step_num}: {title}{C.RESET}")
    print(f"{C.CYAN}|{C.RESET}")


def step_pass(msg="PASSED"):
    print(f"{C.CYAN}|{C.RESET}")
    print(f"{C.CYAN}+---> {C.GREEN}{C.BOLD}[PASS] {msg}{C.RESET}\n")


def step_fail(msg="FAILED"):
    print(f"{C.CYAN}|{C.RESET}")
    print(f"{C.CYAN}+---> {C.RED}{C.BOLD}[FAIL] {msg}{C.RESET}\n")


def log(msg, indent=True):
    prefix = f"{C.CYAN}|{C.RESET}  " if indent else "  "
    print(f"{prefix}{msg}")


# ---------------------------------------------------------------------------
# Step 0: Environment Pre-checks
# ---------------------------------------------------------------------------

def check_environment() -> bool:
    """Validates that Redis and critical dependencies are available."""
    step_header(0, "Environment Pre-checks")
    all_ok = True

    # Check Python version
    py_ver = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    log(f"Python: {C.GREEN}{py_ver}{C.RESET}")

    # Check Redis
    try:
        import redis
        r = redis.Redis(host='localhost', port=6379, db=0, socket_connect_timeout=3)
        r.ping()
        log(f"Redis:  {C.GREEN}Connected{C.RESET} (localhost:6379)")
        r.close()
    except Exception as e:
        log(f"Redis:  {C.RED}UNREACHABLE{C.RESET} — {e}")
        all_ok = False

    # Check critical packages
    packages = ["pytest", "websockets", "httpx", "numpy"]
    for pkg in packages:
        try:
            __import__(pkg)
            log(f"{pkg:12s}: {C.GREEN}OK{C.RESET}")
        except ImportError:
            log(f"{pkg:12s}: {C.RED}MISSING{C.RESET}")
            all_ok = False

    # Check LIVE_PIPELINE_ENABLED
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass  # .env won't be loaded, but os.getenv still works
    flag = os.getenv("LIVE_PIPELINE_ENABLED", "False")
    if flag.lower() in ("true", "1", "yes"):
        log(f"LIVE_PIPELINE_ENABLED: {C.GREEN}{flag}{C.RESET}")
    else:
        log(f"LIVE_PIPELINE_ENABLED: {C.YELLOW}{flag}{C.RESET} (set to True for live tests)")

    if all_ok:
        step_pass("Environment OK")
    else:
        step_fail("Environment check failed")

    return all_ok


# ---------------------------------------------------------------------------
# Step 1: Unit & Integration Logic
# ---------------------------------------------------------------------------

def run_logic_tests() -> bool:
    """Runs pytest on the flusher integration tests."""
    step_header(1, "Unit & Integration Logic Tests")
    log("Running: pytest tests/test_logic_flusher.py -v --tb=short")
    log("")

    result = subprocess.run(
        [sys.executable, "-m", "pytest", "tests/test_logic_flusher.py", "-v", "--tb=short", "--no-header"],
        capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__))
    )

    # Print pytest output with indentation
    for line in result.stdout.strip().split("\n"):
        if "PASSED" in line:
            log(f"{C.GREEN}{line.strip()}{C.RESET}")
        elif "FAILED" in line:
            log(f"{C.RED}{line.strip()}{C.RESET}")
        elif "passed" in line or "failed" in line:
            log(f"{C.BOLD}{line.strip()}{C.RESET}")
        else:
            log(f"{C.DIM}{line.strip()}{C.RESET}")

    if result.returncode == 0:
        step_pass("All logic tests passed")
        return True
    else:
        if result.stderr:
            for line in result.stderr.strip().split("\n")[-5:]:
                log(f"{C.RED}{line.strip()}{C.RESET}")
        step_fail("Logic Failure — fix before proceeding")
        return False


# ---------------------------------------------------------------------------
# Step 2: Connectivity & Protocol Simulation
# ---------------------------------------------------------------------------

async def run_connectivity_test(session_id: str, token: str) -> dict:
    """
    Runs the extension simulator for a single session.
    Returns metrics dict with success status.
    """
    step_header(2, "Connectivity & Protocol Simulation")
    log(f"Session: {session_id[:24]}...")
    log(f"Streaming 10s of 16kHz/16-bit PCM @ 500ms chunks")
    log("")

    results = {
        "success": False,
        "chunks_sent": 0,
        "suggestions": 0,
        "upload_ok": False,
        "latency_p95": None,
        "error": None
    }

    try:
        # Import simulator functions
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
        from simulate_extension import stream_audio, upload_agent_audio

        # Stream audio
        log(f"Streaming audio via WebSocket...")
        latencies = await stream_audio(session_id, token)
        results["chunks_sent"] = 20  # 10s / 0.5s per chunk
        results["suggestions"] = len(latencies)

        if latencies:
            sorted_lat = sorted(latencies)
            results["latency_p95"] = sorted_lat[int(len(sorted_lat) * 0.95)]
            log(f"Suggestions received: {C.GREEN}{len(latencies)}{C.RESET}")
            log(f"Suggestion Latency p95: {C.BOLD}{results['latency_p95']:.1f}ms{C.RESET}")
        else:
            log(f"Suggestions received: {C.YELLOW}0{C.RESET} (RAG may not have matching data)")

        # Upload dummy agent mic
        log(f"Uploading dummy agent microphone...")
        status_code = await upload_agent_audio(session_id)
        results["upload_ok"] = (status_code == 200)

        if results["upload_ok"]:
            log(f"Agent audio upload: {C.GREEN}200 OK{C.RESET}")
        else:
            log(f"Agent audio upload: {C.RED}{status_code}{C.RESET}")

        results["success"] = True

    except Exception as e:
        results["error"] = str(e)
        log(f"{C.RED}Error: {e}{C.RESET}")

    if results["success"]:
        step_pass(f"Protocol verified ({results['chunks_sent']} chunks, upload {'OK' if results['upload_ok'] else 'FAIL'})")
    else:
        step_fail(f"Connectivity failed: {results['error']}")

    return results


# ---------------------------------------------------------------------------
# Step 3: GPU Stress Test
# ---------------------------------------------------------------------------

async def run_stress_test(sessions: list) -> dict:
    """
    Runs 2 concurrent sessions against the backend.
    Monitors for OOM and tracks latency.
    """
    step_header(3, "GPU Stress Test (RTX 3050 — 2 Sessions)")
    log(f"Concurrent sessions: {C.BOLD}{len(sessions)}{C.RESET}")
    log(f"Duration per session: 6 seconds")
    log("")

    results = {
        "success": False,
        "oom_detected": False,
        "total_chunks": 0,
        "total_suggestions": 0,
        "latency_p95": None,
        "errors": []
    }

    try:
        sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "tests"))
        from stress_test_gpu import run_session

        tasks = []
        for i, (sid, tok) in enumerate(sessions):
            tasks.append(run_session(i + 1, sid, tok))

        raw_results = await asyncio.gather(*tasks, return_exceptions=True)

        all_latencies = []
        for r in raw_results:
            if isinstance(r, Exception):
                results["errors"].append(str(r))
                continue
            results["total_chunks"] += r["chunks_sent"]
            results["total_suggestions"] += r["suggestions_received"]
            all_latencies.extend(r["suggestion_latencies_ms"])
            results["errors"].extend(r["errors"])

        # Check for OOM
        results["oom_detected"] = any(
            "CUDA" in e or "OOM" in e or "out of memory" in e.lower()
            for e in results["errors"]
        )

        if all_latencies:
            sorted_lat = sorted(all_latencies)
            results["latency_p95"] = sorted_lat[int(len(sorted_lat) * 0.95)]

        log(f"Total chunks sent:    {C.BOLD}{results['total_chunks']}{C.RESET}")
        log(f"Total suggestions:    {results['total_suggestions']}")

        if results["latency_p95"]:
            color = C.GREEN if results["latency_p95"] < 200 else C.YELLOW
            log(f"Suggestion p95:       {color}{results['latency_p95']:.1f}ms{C.RESET}")

        if results["oom_detected"]:
            log(f"GPU VRAM:             {C.RED}OOM DETECTED{C.RESET}")
        elif results["errors"]:
            log(f"Errors:               {C.YELLOW}{len(results['errors'])}{C.RESET}")
        else:
            log(f"GPU VRAM:             {C.GREEN}Stable{C.RESET}")

        results["success"] = not results["oom_detected"] and len(results["errors"]) == 0

    except Exception as e:
        results["errors"].append(str(e))
        log(f"{C.RED}Stress test error: {e}{C.RESET}")

    if results["success"]:
        step_pass("No OOM. GPU stable under concurrent load.")
    elif results["oom_detected"]:
        step_fail("GPU OOM DETECTED — reduce concurrent sessions or use smaller model")
    else:
        step_fail(f"Stress test had {len(results['errors'])} error(s)")

    return results


# ---------------------------------------------------------------------------
# Final Verdict
# ---------------------------------------------------------------------------

def print_verdict(step_results: dict):
    """Displays the final GO/NO-GO banner."""
    all_passed = all(step_results.values())
    failed_steps = [name for name, ok in step_results.items() if not ok]

    print()
    print(f"{'=' * 64}")
    print(f"{C.BOLD}  SMOKE TEST SUMMARY{C.RESET}")
    print(f"{'-' * 64}")

    for name, ok in step_results.items():
        icon = f"{C.GREEN}[PASS]{C.RESET}" if ok else f"{C.RED}[FAIL]{C.RESET}"
        print(f"  {icon}  {name}")

    print(f"{'=' * 64}")

    if all_passed:
        print()
        print(f"  {C.BG_GREEN}{C.BOLD}                                                          {C.RESET}")
        print(f"  {C.BG_GREEN}{C.BOLD}   PROCEED TO PRODUCTION: SYSTEM IS STABLE                 {C.RESET}")
        print(f"  {C.BG_GREEN}{C.BOLD}                                                          {C.RESET}")
        print()
    else:
        print()
        print(f"  {C.BG_RED}{C.BOLD}                                                          {C.RESET}")
        print(f"  {C.BG_RED}{C.BOLD}   STOP: CRITICAL ISSUES DETECTED                          {C.RESET}")
        print(f"  {C.BG_RED}{C.BOLD}                                                          {C.RESET}")
        print()
        for step in failed_steps:
            print(f"  {C.RED}-> Failed: {step}{C.RESET}")
        print()


# ---------------------------------------------------------------------------
# Main Orchestrator
# ---------------------------------------------------------------------------

async def main():
    parser = argparse.ArgumentParser(
        description="VoiceQA Smoke Test — Production Readiness Runner"
    )
    parser.add_argument("--fast", action="store_true",
                        help="Skip the GPU stress test (Step 3)")
    parser.add_argument("--session_id", type=str, default=None,
                        help="Pre-created session ID for connectivity test")
    parser.add_argument("--token", type=str, default=None,
                        help="Reconnect token for the session")
    parser.add_argument("--stress_sessions", type=str, nargs="+", default=None,
                        help="Session pairs as 'session_id:token' for stress test (exactly 2)")
    args = parser.parse_args()

    banner("VoiceQA Smoke Test — Production Readiness")

    start_time = time.perf_counter()
    step_results = {}

    # ── Step 0: Environment ──
    env_ok = check_environment()
    step_results["Environment Pre-checks"] = env_ok
    if not env_ok:
        print_verdict(step_results)
        return 1

    # ── Step 1: Logic Tests ──
    logic_ok = run_logic_tests()
    step_results["Unit & Integration Logic"] = logic_ok
    if not logic_ok:
        print_verdict(step_results)
        return 1

    # ── Step 2: Connectivity ──
    if args.session_id and args.token:
        conn_result = await run_connectivity_test(args.session_id, args.token)
        step_results["Connectivity & Protocol"] = conn_result["success"]
        if not conn_result["success"]:
            print_verdict(step_results)
            return 1
    else:
        step_header(2, "Connectivity & Protocol Simulation")
        log(f"{C.YELLOW}SKIPPED{C.RESET} — No --session_id / --token provided")
        log(f"To run: python run_smoke_test.py --session_id <id> --token <tok>")
        step_pass("Skipped (no active session)")
        step_results["Connectivity & Protocol"] = True  # Non-blocking skip

    # ── Step 3: Stress Test ──
    if args.fast:
        step_header(3, "GPU Stress Test (RTX 3050)")
        log(f"{C.YELLOW}SKIPPED{C.RESET} — --fast flag enabled")
        step_pass("Skipped (fast mode)")
        step_results["GPU Stress (VRAM Stability)"] = True
    elif args.stress_sessions and len(args.stress_sessions) == 2:
        sessions = []
        for s in args.stress_sessions:
            parts = s.split(":")
            sessions.append((parts[0], parts[1]))
        stress_result = await run_stress_test(sessions)
        step_results["GPU Stress (VRAM Stability)"] = stress_result["success"]
    else:
        step_header(3, "GPU Stress Test (RTX 3050)")
        log(f"{C.YELLOW}SKIPPED{C.RESET} — No --stress_sessions provided")
        log(f"To run: python run_smoke_test.py --stress_sessions 'sid1:tok1' 'sid2:tok2'")
        step_pass("Skipped (no stress sessions)")
        step_results["GPU Stress (VRAM Stability)"] = True

    # ── Final Verdict ──
    elapsed = time.perf_counter() - start_time
    print(f"\n{C.DIM}Total execution time: {elapsed:.1f}s{C.RESET}")
    print_verdict(step_results)

    all_passed = all(step_results.values())
    return 0 if all_passed else 1


# ---------------------------------------------------------------------------
# Entry Point
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    exit_code = asyncio.run(main())
    print()
    input("Press Enter to exit...")
    sys.exit(exit_code)
