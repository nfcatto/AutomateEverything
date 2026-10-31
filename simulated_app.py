"""Stand-in for the program you "enter".

Keep this running for a few seconds, then it closes.
Optional: pass a duration in seconds, e.g. `python simulated_app.py 15`.
"""

import os
import sys
import time

duration = int(sys.argv[1]) if len(sys.argv) > 1 else 8

print(f"[simulated_app] opened (pid {os.getpid()}) - staying open for {duration}s")
time.sleep(duration)
print("[simulated_app] closed")
