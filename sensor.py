import subprocess
import datetime
from collections import Counter

remote_host = "user@<HOST>"  # Change to your user and host
remote_file = "<PATH_TO_MESSAGES>"  # Change to the correct path
ssh_port = "<PORT>"

today = datetime.datetime.now().strftime("%b %d")
unique_ips = set()
total_drop_hostile = 0
port_counter = Counter()

ssh_cmd = [
    "ssh", "-p", ssh_port, remote_host, f"cat {remote_file}"
]

proc = subprocess.Popen(ssh_cmd, stdout=subprocess.PIPE, text=True)
for line in proc.stdout:
    if today in line and "DROP_HOSTILE" in line:
        total_drop_hostile += 1
        parts = line.split()
        src_ip = None
        dpt = None
        for part in parts:
            if part.startswith("SRC="):
                src_ip = part.split("=")[1]
                unique_ips.add(src_ip)
            if part.startswith("DPT="):
                dpt = part.split("=")[1]
        if dpt:
            port_counter[dpt] += 1

print(f"Total DROP_HOSTILE entries today: {total_drop_hostile}")
print(f"Unique SRC IPs today: {len(unique_ips)}")
print("Top 10 DROP_HOSTILE entries per destination port:")
for port, count in port_counter.most_common(10):
    print(f"{port}: {count}")