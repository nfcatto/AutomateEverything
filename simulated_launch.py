"""Stand-in for the program that should open automatically."""

import datetime
import time

now = datetime.datetime.now().strftime("%H:%M:%S")
print(f"[simulated_launch] LAUNCHED at {now}")
time.sleep(3)
print("[simulated_launch] closed")
