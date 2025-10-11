#        --------- What is the purpose of this file? ---------
# This script is responsible for running and stopping the bot. It should also
# ensure that the local copy of the bot is sync'd with its remote counterpart.
# It also has a frequency parameter that details how many times in a day it
# should check for new changes. Once a new change is detected, this script
# should stop the bot, sync the changes, and re-run the bot.

# The aspect of the bot that detects changes from github is derived from
# the source below.
#   - Source: https://gist.github.com/gwpl/6f2c8f2574db6df770c51795d02cd458

from dataclasses import dataclass
from datetime import datetime, timedelta
import subprocess, sys, threading, time

@dataclass
class CmdOutput:
    code: int
    stdout: str
    stderr: str

def run_cmd(cmd: list[str]) -> CmdOutput | None:
    try:
        print(f"INFO: cmd: {cmd}")
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            check=False
        )
        return CmdOutput(proc.returncode, proc.stdout, proc.stderr)
    except Exception as e:
        print(f"ERROR: Failed to run cmd ({cmd})")
        print(f"ERROR: {repr(e)}")

def get_all_commits(use_remote: bool) -> list[str]:
    cmd_args = ["git", "log", "--oneline"]
    if use_remote:
        cmd_args.extend(["origin", "main"])

    output = run_cmd(cmd_args)
    if output is None:
        sys.exit(1)

    if output.code != 0:
        print(f"ERROR: subcmd exited with code {output.code}")
        print(f"ERROR: stdout: {output.stderr}")
        sys.exit(1)

    print(output.stdout)

    # Parse git commit logs
    hashes: list[str] = []
    lines: list[str] = output.stdout.splitlines()
    for line in lines:
        parts: list[str] = line.split()
        hashes.append(parts[0])

    return hashes

def get_current_commit(use_remote: bool) -> str:
    dest = "origin/main" if use_remote else "HEAD"
    cmd = run_cmd(["git", "rev-parse", dest])

    if cmd is None:
        print("ERROR: failed to get current commit hash")
        sys.exit(1)

    return cmd.stdout.strip()

def fetch_latest():
    cmd = run_cmd(["git", "fetch", "origin"])
    if cmd is not None:
        print("INFO: fetched latest changes from origin")
    else:
        print("ERROR: failed to fetch latest change from origin")

def run_bot() -> bool:
    cmd = run_cmd(["uv", "run", "live_bot.py"])
    if cmd is None:
        print("ERROR: failed to run bot")
        return False

    return True

def sync_w_remote():
    fetch_latest()

    local_commit = get_current_commit(use_remote=False)
    remote_commit = get_current_commit(use_remote=True)
    if local_commit != remote_commit:
        cmd = run_cmd(["git", "pull", "origin", "main"])
        if cmd is None:
            print(f"ERROR: failed to sync changes with remote")

# ============================================================================
freq = 1
gap_between_checks = timedelta(hours=24 / freq)

now = datetime.now()
start = now
# Check for remote changes before running the bot
last_check = start

bot_thread = threading.Thread(target=run_bot)
bot_thread.start()

while True:
    if now - last_check >= gap_between_checks:
        sync_w_remote()
    else:
        time.sleep(gap_between_checks.total_seconds() - 1)

        last_check = now
        now = datetime.now()
