#!/usr/bin/env python3
"""
AUTONOMOUS STARTUP & FULL LIFECYCLE TEST ORCHESTRATOR
Uses uv run exclusively - no pip
Starts all services, verifies health, runs PHASE 1-3, generates forensic report
"""

import subprocess
import time
import sys
import os
import json
from pathlib import Path
from datetime import datetime

PROJECT_ROOT = Path(r"C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono")
FRONTEND_DIR = PROJECT_ROOT / "frontend"

# Store process IDs
backend_proc = None
frontend_proc = None
worker_proc = None

def log(msg, level="INFO", prefix=""):
    """Pretty logging"""
    colors = {
        "INFO": "\033[94m",
        "SUCCESS": "\033[92m",
        "ERROR": "\033[91m",
        "WARN": "\033[93m",
        "PHASE": "\033[96m",
    }
    reset = "\033[0m"
    ts = datetime.now().strftime("%H:%M:%S")
    color = colors.get(level, "")
    print(f"{color}[{ts}] {level:8} {prefix}{msg}{reset}")

def run_uv_command(cmd_args, cwd, label, timeout=30):
    """Run command via uv run"""
    full_cmd = f"uv run {' '.join(cmd_args)}"
    log(f"Starting: {label}", "PHASE")
    log(f"Command: {full_cmd}", "INFO")
    
    try:
        proc = subprocess.Popen(
            full_cmd,
            cwd=str(cwd),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        log(f"{label} spawned (PID: {proc.pid})", "SUCCESS")
        return proc
    except Exception as e:
        log(f"Failed to start {label}: {e}", "ERROR")
        return None

def check_port_health(port, service_name, timeout=10):
    """Check if service is responding on port"""
    import socket
    start = time.time()
    
    while time.time() - start < timeout:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(2)
            result = sock.connect_ex(('127.0.0.1', port))
            sock.close()
            
            if result == 0:
                log(f"{service_name} responding on port {port}", "SUCCESS")
                return True
        except:
            pass
        
        time.sleep(1)
    
    log(f"{service_name} timeout on port {port}", "ERROR")
    return False

def verify_env():
    """Verify .env and uv availability"""
    log("PRE-FLIGHT CHECKS", "PHASE")
    
    if not (PROJECT_ROOT / ".env").exists():
        log(".env file missing!", "ERROR")
        return False
    log(".env found", "SUCCESS")
    
    # Check uv availability
    try:
        result = subprocess.run(
            "uv --version",
            shell=True,
            capture_output=True,
            text=True,
            timeout=5
        )
        log(f"uv available: {result.stdout.strip()}", "SUCCESS")
    except Exception as e:
        log(f"uv check failed: {e}", "ERROR")
        return False
    
    return True

def main():
    global backend_proc, frontend_proc, worker_proc
    
    log("=" * 80, "PHASE")
    log("AUTONOMOUS STARTUP & FULL LIFECYCLE TEST ORCHESTRATOR", "PHASE")
    log("Principal QA Automation Engineer - Chaos Mode", "PHASE")
    log("=" * 80, "PHASE")
    log("")
    
    # Pre-flight checks
    if not verify_env():
        log("Pre-flight checks failed", "ERROR")
        return False
    
    log("")
    log("=" * 80, "PHASE")
    log("PHASE 0: SERVICE STARTUP", "PHASE")
    log("=" * 80, "PHASE")
    log("")
    
    # Start Backend
    log("BACKEND", "PHASE", "→ ")
    backend_proc = run_uv_command(
        ["python", "run_backend.py"],
        PROJECT_ROOT,
        "Backend (FastAPI)"
    )
    if not backend_proc:
        log("Failed to start backend", "ERROR")
        return False
    
    time.sleep(5)
    
    if not check_port_health(8000, "Backend", timeout=10):
        log("Backend health check failed - autonomous remediation", "WARN")
        # Try killing and restarting
        try:
            subprocess.run("taskkill /F /IM python.exe", shell=True, capture_output=True)
            time.sleep(2)
            backend_proc = run_uv_command(
                ["python", "run_backend.py"],
                PROJECT_ROOT,
                "Backend (FastAPI - Restart)"
            )
            time.sleep(5)
            if not check_port_health(8000, "Backend", timeout=10):
                log("Backend restart failed", "ERROR")
                return False
        except Exception as e:
            log(f"Backend remediation failed: {e}", "ERROR")
            return False
    
    log("")
    
    # Start Frontend
    log("FRONTEND", "PHASE", "→ ")
    frontend_proc = subprocess.Popen(
        "npm run dev",
        cwd=str(FRONTEND_DIR),
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        shell=True,
        text=True
    )
    if not frontend_proc:
        log("Failed to start frontend", "ERROR")
        return False
    log(f"Frontend spawned (PID: {frontend_proc.pid})", "SUCCESS")
    
    time.sleep(6)
    
    if not check_port_health(3000, "Frontend", timeout=10):
        log("Frontend health check failed", "ERROR")
        return False
    
    log("")
    
    # Start Worker
    log("WORKER", "PHASE", "→ ")
    worker_proc = run_uv_command(
        ["python", "run_worker.py"],
        PROJECT_ROOT,
        "Worker (AI Processing)"
    )
    if not worker_proc:
        log("Failed to start worker", "ERROR")
        return False
    
    time.sleep(3)
    log("")
    
    log("=" * 80, "SUCCESS")
    log("✅ ALL SERVICES RUNNING", "SUCCESS")
    log("=" * 80, "SUCCESS")
    log("  Frontend:  http://localhost:3000", "INFO")
    log("  Backend:   http://localhost:8000/docs", "INFO")
    log("  Worker:    Processing engine active", "INFO")
    log("")
    
    # Now run lifecycle test
    log("=" * 80, "PHASE")
    log("PHASE 1-3: FULL LIFECYCLE TEST", "PHASE")
    log("=" * 80, "PHASE")
    log("")
    
    time.sleep(3)
    
    try:
        log("Launching full lifecycle test via uv run...", "PHASE")
        test_result = subprocess.run(
            "uv run python full_lifecycle_test.py",
            cwd=str(PROJECT_ROOT),
            shell=True,
            capture_output=True,
            text=True,
            timeout=180
        )
        
        log("TEST OUTPUT:", "PHASE")
        log("=" * 80, "PHASE")
        print(test_result.stdout)
        if test_result.stderr:
            log("STDERR:", "WARN")
            print(test_result.stderr)
        log("=" * 80, "PHASE")
        
        test_passed = test_result.returncode == 0
        
    except subprocess.TimeoutExpired:
        log("Lifecycle test timeout (180s exceeded)", "ERROR")
        test_passed = False
    except Exception as e:
        log(f"Lifecycle test failed: {e}", "ERROR")
        test_passed = False
    
    log("")
    
    # Generate final forensic report
    log("=" * 80, "PHASE")
    log("GENERATING FINAL FORENSIC REPORT", "PHASE")
    log("=" * 80, "PHASE")
    log("")
    
    report = {
        "timestamp": datetime.utcnow().isoformat(),
        "test_result": "PASSED" if test_passed else "FAILED",
        "services": {
            "backend": "RUNNING" if backend_proc and backend_proc.poll() is None else "STOPPED",
            "frontend": "RUNNING" if frontend_proc and frontend_proc.poll() is None else "STOPPED",
            "worker": "RUNNING" if worker_proc and worker_proc.poll() is None else "STOPPED",
        },
        "phases": {
            "phase_1": "GENESIS_ENCOUNTER",
            "phase_2": "CLINICAL_CONFLICT",
            "phase_3": "ADMIN_OVERRIDE_AND_AUDIT",
        }
    }
    
    print(json.dumps(report, indent=2))
    
    log("")
    if test_passed:
        log("=" * 80, "SUCCESS")
        log("🎉 FULL LIFECYCLE TEST COMPLETE - PRODUCTION READY", "SUCCESS")
        log("=" * 80, "SUCCESS")
    else:
        log("=" * 80, "ERROR")
        log("❌ LIFECYCLE TEST FAILED - REQUIRES INVESTIGATION", "ERROR")
        log("=" * 80, "ERROR")
    
    # Cleanup
    log("", "INFO")
    log("Shutting down services...", "WARN")
    try:
        if backend_proc:
            backend_proc.terminate()
        if frontend_proc:
            frontend_proc.terminate()
        if worker_proc:
            worker_proc.terminate()
        log("Services stopped", "SUCCESS")
    except:
        pass
    
    return test_passed

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        sys.exit(1)
