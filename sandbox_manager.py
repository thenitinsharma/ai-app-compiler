import os
import sys
import time
import socket
import subprocess

class SandboxManager:
    def __init__(self, runtime_dir: str):
        self.runtime_dir = runtime_dir
        self.process = None

    def kill_port_owner(self, port: int):
        """
        Robustly kills any process listening on the specified port on Windows.
        """
        if sys.platform == "win32":
            try:
                # Find PID using netstat
                cmd = f"netstat -ano | findstr :{port}"
                output = subprocess.check_output(cmd, shell=True).decode()
                for line in output.strip().split("\n"):
                    if "LISTENING" in line:
                        parts = line.strip().split()
                        pid = parts[-1]
                        # Terminate PID
                        subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                        print(f"Killed active process {pid} occupying port {port}")
                        time.sleep(0.5)
            except Exception as e:
                pass  # Ignore if port was not occupied
        else:
            try:
                subprocess.run(f"fuser -k {port}/tcp", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                pass

    def stop(self):
        """
        Terminates the running sandbox process.
        """
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=2)
                print("Sandbox process terminated.")
            except Exception:
                try:
                    self.process.kill()
                except Exception:
                    pass
            self.process = None

    def start(self, port: int = 8001) -> bool:
        """
        Prepares the port, spawns the FastAPI app subprocess, and waits for it to respond.
        """
        # Ensure port is clean
        self.stop()
        self.kill_port_owner(port)
        
        # Start subprocess
        cmd = [sys.executable, "api_runtime.py", "--port", str(port)]
        try:
            self.process = subprocess.Popen(
                cmd,
                cwd=self.runtime_dir,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )
            
            # Wait for startup confirmation
            return self.wait_for_port(port)
        except Exception as e:
            print("Failed to start sandbox:", e)
            return False

    def wait_for_port(self, port: int, timeout: float = 8.0) -> bool:
        """
        Checks socket connection status periodically until target port is active.
        """
        start_time = time.time()
        while time.time() - start_time < timeout:
            # Check if subprocess died early
            if self.process and self.process.poll() is not None:
                out, err = self.process.communicate()
                print("Sandbox process crashed on startup.")
                print("Stdout:", out)
                print("Stderr:", err)
                return False
                
            try:
                with socket.create_connection(("127.0.0.1", port), timeout=0.5):
                    print(f"Sandbox verified online at port {port}.")
                    return True
            except (ConnectionRefusedError, socket.timeout):
                time.sleep(0.3)
        print("Sandbox port startup timed out.")
        return False

if __name__ == "__main__":
    # Test harness
    mgr = SandboxManager(".")
    print("Testing sandbox start...")
    success = mgr.start(8001)
    print("Start status:", success)
    time.sleep(2)
    print("Stopping sandbox...")
    mgr.stop()
