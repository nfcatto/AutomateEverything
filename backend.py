import subprocess
import time
import psutil
from datetime import datetime


process_id=[]
for x in psutil.pids():
    process_id=psutil.pids()



process_name=[]

for x in process_id:
    proc_id_index=x
    process_name=psutil.Process(x)


print(type(process_id))
print(process_id)
print(process_name)    







