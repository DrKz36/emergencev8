#!/usr/bin/env python3
"""
ARGUS Simple - Log Monitor (Python version)
Monitors backend and frontend for errors in real-time
"""

import sys
import socket
import time
import subprocess
from pathlib import Path
from datetime import datetime
import psutil

# Colors for terminal output
class Colors:
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    GRAY = '\033[90m'
    RESET = '\033[0m'
    BOLD = '\033[1m'

def print_color(text, color=""):
    print(f"{color}{text}{Colors.RESET}")

def check_port(port):
    """Check if a port is being listened on"""
    for conn in psutil.net_connections():
        if conn.laddr.port == port and conn.status == 'LISTEN':
            return True, conn.pid
    return False, None

def find_process_by_pid(pid):
    """Find process info by PID"""
    try:
        proc = psutil.Process(pid)
        return proc
    except:
        return None

def print_banner():
    print()
    print_color("=" * 60, Colors.CYAN)
    print_color("   ARGUS - Development Log Monitor", Colors.CYAN)
    print_color("   The All-Seeing Guardian (Python Edition)", Colors.CYAN)
    print_color("=" * 60, Colors.CYAN)
    print()

def main():
    print_banner()

    session_id = datetime.now().strftime("%Y%m%d-%H%M%S")
    print_color(f"Session ID: {session_id}", Colors.GRAY)
    print()

    # Check for running services
    print_color("Checking for running services...", Colors.YELLOW)
    print()

    backend_port = 8000
    frontend_port = 5173

    backend_running, backend_pid = check_port(backend_port)
    frontend_running, frontend_pid = check_port(frontend_port)

    if not backend_running and not frontend_running:
        print_color("ERROR: Neither backend nor frontend is running!", Colors.RED)
        print()
        print_color("Please start the services first:", Colors.YELLOW)
        print_color("  Backend:  cd src/backend && python -m uvicorn main:app --reload --port 8000", Colors.GRAY)
        print_color("  Frontend: cd src/frontend && npm run dev", Colors.GRAY)
        print()
        return 1

    if backend_running:
        backend_proc = find_process_by_pid(backend_pid)
        print_color(f"[OK] Backend detected on port {backend_port} (PID: {backend_pid})", Colors.GREEN)
        if backend_proc:
            print_color(f"   Process: {backend_proc.name()} - {' '.join(backend_proc.cmdline()[:3])}", Colors.GRAY)
    else:
        print_color(f"[WARN] Backend not detected on port {backend_port}", Colors.YELLOW)

    print()

    if frontend_running:
        frontend_proc = find_process_by_pid(frontend_pid)
        print_color(f"[OK] Frontend detected on port {frontend_port} (PID: {frontend_pid})", Colors.GREEN)
        if frontend_proc:
            print_color(f"   Process: {frontend_proc.name()} - {' '.join(frontend_proc.cmdline()[:3])}", Colors.GRAY)
    else:
        print_color(f"[WARN] Frontend not detected on port {frontend_port}", Colors.YELLOW)

    print()
    print_color("=" * 60, Colors.CYAN)
    print()

    # Show process information
    print_color("Process Information:", Colors.CYAN)
    print()

    if backend_running and backend_proc:
        try:
            cpu = backend_proc.cpu_percent(interval=0.1)
            mem = backend_proc.memory_info().rss / 1024 / 1024  # MB
            print_color(f"Backend Process (PID {backend_pid}):", Colors.BOLD)
            print_color(f"  CPU: {cpu:.1f}%", Colors.GRAY)
            print_color(f"  Memory: {mem:.1f} MB", Colors.GRAY)
            print_color(f"  Status: {backend_proc.status()}", Colors.GRAY)
            print_color(f"  Working Dir: {backend_proc.cwd()}", Colors.GRAY)
            print()
        except Exception as e:
            print_color(f"  Could not get process info: {e}", Colors.YELLOW)

    if frontend_running and frontend_proc:
        try:
            cpu = frontend_proc.cpu_percent(interval=0.1)
            mem = frontend_proc.memory_info().rss / 1024 / 1024  # MB
            print_color(f"Frontend Process (PID {frontend_pid}):", Colors.BOLD)
            print_color(f"  CPU: {cpu:.1f}%", Colors.GRAY)
            print_color(f"  Memory: {mem:.1f} MB", Colors.GRAY)
            print_color(f"  Status: {frontend_proc.status()}", Colors.GRAY)
            print_color(f"  Working Dir: {frontend_proc.cwd()}", Colors.GRAY)
            print()
        except Exception as e:
            print_color(f"  Could not get process info: {e}", Colors.YELLOW)

    print_color("=" * 60, Colors.CYAN)
    print()

    # Check recent connections
    print_color("Recent Connections:", Colors.CYAN)
    print()

    backend_connections = 0
    frontend_connections = 0

    for conn in psutil.net_connections():
        if conn.laddr.port == backend_port:
            if conn.status in ['ESTABLISHED', 'TIME_WAIT']:
                backend_connections += 1
        if conn.laddr.port == frontend_port:
            if conn.status in ['ESTABLISHED', 'TIME_WAIT']:
                frontend_connections += 1

    print_color(f"  Backend (port {backend_port}): {backend_connections} connections", Colors.GRAY)
    print_color(f"  Frontend (port {frontend_port}): {frontend_connections} connections", Colors.GRAY)
    print()

    # Test HTTP endpoints
    print_color("Testing HTTP Endpoints:", Colors.CYAN)
    print()

    try:
        import requests

        if backend_running:
            try:
                response = requests.get(f"http://localhost:{backend_port}/docs", timeout=2)
                print_color(f"  [OK] Backend API docs: HTTP {response.status_code}", Colors.GREEN)
            except Exception as e:
                print_color(f"  [WARN] Backend API: {str(e)}", Colors.YELLOW)

        if frontend_running:
            try:
                response = requests.get(f"http://localhost:{frontend_port}", timeout=2)
                print_color(f"  [OK] Frontend: HTTP {response.status_code}", Colors.GREEN)
            except Exception as e:
                print_color(f"  [WARN] Frontend: {str(e)}", Colors.YELLOW)
    except ImportError:
        print_color("  [WARN] requests module not available, skipping HTTP tests", Colors.YELLOW)

    print()
    print_color("=" * 60, Colors.CYAN)
    print()

    print_color("Tips:", Colors.CYAN)
    print_color("  - Logs are typically shown in the terminal where services are running", Colors.GRAY)
    print_color("  - Check backend logs in the uvicorn terminal", Colors.GRAY)
    print_color("  - Check frontend logs in the vite/npm terminal", Colors.GRAY)
    print_color("  - For real-time error detection, the full ARGUS monitor is needed", Colors.GRAY)
    print()

    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print()
        print_color("Interrupted by user", Colors.YELLOW)
        sys.exit(0)
