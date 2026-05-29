# AI App Compiler - Startup Script
# Verifies environment dependencies, spins up the backend server, and opens the playground UI.

import os
import sys
import time
import threading
import webbrowser
import subprocess

def install_dependencies():
    """
    Checks for fastapi and uvicorn dependencies and installs them if missing.
    """
    print("====================================================")
    print("       Checking Python Dependencies...")
    print("====================================================")
    
    required_packages = ["fastapi", "uvicorn", "pydantic"]
    missing_packages = []
    
    for pkg in required_packages:
        try:
            __import__(pkg)
        except ImportError:
            missing_packages.append(pkg)
            
    if missing_packages:
        print(f"Installing missing dependencies: {', '.join(missing_packages)}...")
        try:
            # Run pip install with BypassSandbox style privileges outside container if executing from terminal
            subprocess.check_call([sys.executable, "-m", "pip", "install"] + missing_packages)
            print("Dependencies installed successfully.")
        except Exception as e:
            print("WARNING: Failed to install packages via pip automatically. Please run manually:")
            print(f"  pip install {' '.join(missing_packages)}")
            print("Error Details:", e)
    else:
        print("All dependencies are already installed.")

def open_browser():
    """
    Opens browser dashboard link after a short delay to allow server boot.
    """
    time.sleep(2.0)
    url = "http://127.0.0.1:8000/"
    print(f"\nOpening compiler dashboard at {url}...")
    webbrowser.open(url)

def main():
    # 1. Clean and install packages
    install_dependencies()
    
    # 2. Start browser opener thread
    threading.Thread(target=open_browser, daemon=True).start()
    
    # 3. Launch FastAPI server
    print("\n====================================================")
    print("       AI App Compiler Playground Startup")
    print("       Starting compiler dashboard on http://127.0.0.1:8000")
    print("====================================================")
    
    try:
        import uvicorn
        uvicorn.run("app:app", host="127.0.0.1", port=8000, reload=False)
    except KeyboardInterrupt:
        print("\nShutdown signal received. Terminating backend compiler process.")
    except Exception as e:
        print("\nFailed to run compiler server:", e)
        print("Verify your python path environment mappings or execute:")
        print("  python -m uvicorn app:app --port 8000")

if __name__ == "__main__":
    main()
