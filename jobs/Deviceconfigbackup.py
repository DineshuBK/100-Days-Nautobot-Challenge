import os
import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from netmiko import ConnectHandler

# ---------- File Inputs ----------
#DEVICE_FILE = "devices.txt"      # One device IP/hostname per line
DEVICE_FILE = r"<<Path to>> devices.txt"
CREDENTIAL_FILE = r"<<Path to>> credentials.txt"  # username:password format (single line)
COMMAND_FILE = r"<<Path to>> commands.txt"    # One command per line
OUTPUT_DIR = "outputs"           # Folder to save output files

# ---------- Load Inputs ----------
with open(DEVICE_FILE) as f:
    devices = [line.strip() for line in f if line.strip()]

with open(CREDENTIAL_FILE) as f:
    creds = f.read().strip().split(":")#-------------------+
    USERNAME, PASSWORD = creds[0], creds[1]

with open(COMMAND_FILE) as f:
    commands = [line.strip() for line in f if line.strip()]

# ---------- Ensure Output Directory ----------
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# ---------- Worker Function ----------
def collect_outputs(host):
    device = {
        "device_type": "cisco_ios",   # Change as needed (cisco_xe, juniper, etc.)
        "host": host,
        "username": USERNAME,
        "password": PASSWORD,
        "fast_cli": False, # Disable for large command outputs
    }
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = os.path.join(OUTPUT_DIR, f"{host}_{timestamp}.txt")

    try:
        conn = ConnectHandler(**device)
        conn.enable()
        print(f"[CONNECTED] Successfully connected to {host}")
        
        conn.send_command("terminal length 0")  # avoid paging
        with open(filename, "w", encoding="utf-8") as f:  # Open text file in write mode to add the output
            for cmd in commands:
                f.write(f"\n\n<------ {cmd} ----->\n")
                # output = conn.send_command(cmd)
                # output = conn.send_command(cmd, expect_string=r"[>#]")
                #output = conn.send_command(cmd, expect_string=r"#", read_timeout=60)  # Fix for pattern match issue
                # Use send_command_timing for large outputs to avoid prompt errors
                output = conn.send_command_timing(cmd, delay_factor=4, max_loops=2000, read_timeout=0)  # Read_timeout=120 Never time out from absolute timer
                f.write(output)
                
        conn.disconnect()
        return f"[SUCCESS] {host} -> {filename}"
    except Exception as e:
        return f"[FAILED] {host} -> {str(e)}"

# ---------- Multi-thread Execution ----------
def main():
    results = []
    max_threads = 50   # Tune based on system performance
    with ThreadPoolExecutor(max_threads) as executor:
        futures = {executor.submit(collect_outputs, host): host for host in devices}
        for future in as_completed(futures):
            results.append(future.result())

    print("\n".join(results))


if __name__ == "__main__":
    main()
