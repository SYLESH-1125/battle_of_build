#!/usr/bin/env python3
"""
Startup Verification Script for Digital Human Memory Vault
Tests all three services can start and respond to health checks
"""

import subprocess
import time
import sys
import requests
from pathlib import Path
import signal
import os

PROJECT_ROOT = Path(r"C:\Users\2504690\Hack\MP_battle_of_build\memory-vault-mono")
FRONTEND_DIR = PROJECT_ROOT / "frontend"
BACKEND_DIR = PROJECT_ROOT
WORKER_DIR = PROJECT_ROOT

# Store process handles for cleanup
processes = []

def log(message, level="INFO"):
    """Pretty print with timestamp"""
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    colors = {
        "INFO": "\033[94m",     # Blue
        "SUCCESS": "\033[92m",  # Green
        "ERROR": "\033[91m",    # Red
        "WARN": "\033[93m",     # Yellow
    }
    reset = "\033[0m"
    color = colors.get(level, "")
    print(f"{color}[{timestamp}] {level:8} {message}{reset}")

def run_command(cmd, cwd, label):
    """Start a command in background"""
    try:
        log(f"Starting {label}...", "INFO")
        p = subprocess.Popen(
            cmd,
            cwd=cwd,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
            text=True
        )
        processes.append((p, label))
        log(f"{label} process started (PID: {p.pid})", "SUCCESS")
        return p
    except Exception as e:
        log(f"Failed to start {label}: {e}", "ERROR")
        return None

def check_health(url, timeout=10, service_name="Service"):
    """Check if service is responding"""
    start = time.time()
    while time.time() - start < timeout:
        try:
            response = requests.get(url, timeout=2)
            if response.status_code in [200, 201, 404]:  # 404 is ok for docs check
                log(f"{service_name} is healthy (Status {response.status_code})", "SUCCESS")
                return True
        except requests.ConnectionError:
            time.sleep(1)
        except Exception as e:
            log(f"Health check error: {e}", "WARN")
            time.sleep(1)
    
    log(f"Health check timeout for {service_name}", "ERROR")
    return False

def cleanup():
    """Kill all started processes"""
    log("Cleaning up processes...", "INFO")
    for p, label in processes:
        try:
            p.terminate()
            p.wait(timeout=5)
            log(f"Stopped {label}", "SUCCESS")
        except:
            p.kill()
            log(f"Force-killed {label}", "WARN")

def main():
    log("Digital Human Memory Vault - Startup Verification", "INFO")
    log("=" * 60, "INFO")
    
    # Check prerequisites
    log("Checking prerequisites...", "INFO")
    if not PROJECT_ROOT.exists():
        log(f"Project root not found: {PROJECT_ROOT}", "ERROR")
        return False
    
    if not (PROJECT_ROOT / ".env").exists():
        log("⚠️  .env file not found - services may fail", "WARN")
    
    try:
        log("Verifying Python environment...", "INFO")
        result = subprocess.run(
            ["python", "--version"],
            cwd=PROJECT_ROOT,
            capture_output=True,
            text=True,
            timeout=5
        )
        log(f"Python: {result.stdout.strip()}", "SUCCESS")
    except Exception as e:
        log(f"Python check failed: {e}", "ERROR")
        return False
    
    try:
        log("Verifying npm environment...", "INFO")
        result = subprocess.run(
            ["npm", "--version"],
            cwd=FRONTEND_DIR,
            capture_output=True,
            text=True,
            timeout=5
        )
        log(f"npm: v{result.stdout.strip()}", "SUCCESS")
    except Exception as e:
        log(f"npm check failed: {e}", "ERROR")
        return False
    
    log("=" * 60, "INFO")
    
    # Start services
    log("PHASE 1: Starting Backend (FastAPI on port 8000)...", "INFO")
    backend_cmd = "python run_backend.py"
    backend_proc = run_command(backend_cmd, str(BACKEND_DIR), "Backend")
    if not backend_proc:
        log("Failed to start backend", "ERROR")
        cleanup()
        return False
    
    time.sleep(5)  # Give backend time to start
    
    log("PHASE 2: Verifying Backend health...", "INFO")
    if not check_health("http://127.0.0.1:8000/docs", timeout=10, service_name="Backend"):
        log("Backend failed health check", "ERROR")
        cleanup()
        return False
    
    log("=" * 60, "INFO")
    
    log("PHASE 3: Starting Frontend (Next.js on port 3000)...", "INFO")
    frontend_cmd = "npm run dev -- --webpack"
    frontend_proc = run_command(frontend_cmd, str(FRONTEND_DIR), "Frontend")
    if not frontend_proc:
        log("Failed to start frontend", "ERROR")
        cleanup()
        return False
    
    time.sleep(8)  # Give frontend time to start
    
    log("PHASE 4: Verifying Frontend health...", "INFO")
    if not check_health("http://127.0.0.1:3000", timeout=10, service_name="Frontend"):
        log("Frontend failed health check", "ERROR")
        cleanup()
        return False
    
    log("=" * 60, "INFO")
    
    log("PHASE 5: Starting Worker (Python AI Processing)...", "INFO")
    worker_cmd = "python run_worker.py"
    worker_proc = run_command(worker_cmd, str(WORKER_DIR), "Worker")
    if not worker_proc:
        log("Failed to start worker", "ERROR")
        cleanup()
        return False
    
    time.sleep(3)  # Give worker time to start
    
    log("=" * 60, "INFO")
    log("✅ ALL SERVICES STARTED SUCCESSFULLY!", "SUCCESS")
    log("=" * 60, "INFO")
    log("Frontend:  http://localhost:3000", "INFO")
    log("Backend:   http://localhost:8000/docs", "INFO")
    log("Worker:    Check worker terminal for logs", "INFO")
    log("=" * 60, "INFO")
    
    # Keep processes running
    try:
        log("Services running. Press CTRL+C to stop.", "INFO")
        while True:
            time.sleep(1)
            # Check if any process has died
            for p, label in processes:
                if p.poll() is not None:
                    log(f"⚠️  {label} process died (PID: {p.pid})", "WARN")
    except KeyboardInterrupt:
        log("\nReceived CTRL+C, stopping services...", "WARN")
    finally:
        cleanup()
    
    return True

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except Exception as e:
        log(f"Fatal error: {e}", "ERROR")
        cleanup()
        sys.exit(1)
