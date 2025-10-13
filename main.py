#        --------- What is the purpose of this file? ---------
# This script is responsible for running and stopping the bot. It should also
# ensure that the local copy of the bot is sync'd with its remote counterpart.
# It also has a frequency parameter that details how many times in a day it
# should check for new changes. Once a new change is detected, this script
# should stop the bot, sync the changes, and re-run the bot.

# The aspect of the bot that detects changes from github is derived from
# the source below.
#   - Source: https://gist.github.com/gwpl/6f2c8f2574db6df770c51795d02cd458

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from threading import Thread
from typing import Callable
import subprocess, sys

from trbot.log import repl_log
from trbot.strategy import LiveStrategy, quit_event
from trbot.all_strat import TrendFollowingStrat

@dataclass
class CmdOutput:
    code: int
    stdout: str
    stderr: str

def run_bot() -> None:
    symbols: list[str] = [
        "GE", "HPQ", "EBAY", "XLF", "GE", "GOOG", "SPY", "AAPL",
        "PEP", "LOGI", "INTC", "TGT", "WMT", "NIO", "HIMS", "AMZN"
    ]

    ls = TrendFollowingStrat(
        acct_name="Alpaca Bot 03",
        strat_name="Trend following",
        symbols=symbols.copy(), paper=True
    )

    ls.export_everything("test.json")
    new_strat = LiveStrategy.import_everything("test.json")
    new_strat.export_everything("duplicate.json")

    # try:
    #     ls.start_loop()
    # except KeyboardInterrupt:
    #     log.error("Received keyboard interrupt, ctrl-c...")
    #     log.info("Shutting down")
    #     ls.shutdown()
    #     log.info("Complete ... Goodbye!")

@dataclass
class ReplCmd:
    func: Callable[[list[str]], None]
    desc: str

class Runner:
    def __init__(self) -> None:
        self.should_quit: bool = False
        self.now: datetime = datetime.now()
        self.last_check: datetime = field(init=False)
        self.bot_thread: Thread = Thread(target=run_bot)
        self.bot_running: bool = False
        self.freq: int = 1

        self.repl_cmds: dict[str, ReplCmd] = {
            "start": ReplCmd(
                func=self._repl_bot_start,
                desc="Start running the bot (if not already running)"
            ),
            "stop": ReplCmd(
                func=self._repl_bot_stop,
                desc="Stop running the bot (if already running)"
            ),
            "commit": ReplCmd(
                func=self._repl_commit,
                desc="Get the current commit hash of the local and remote repo"
            ),
            "quit": ReplCmd(
                func=self._repl_quit,
                desc="Quit the current program"
            ),
            "help": ReplCmd(
                func=self._repl_help,
                desc="Print a list of all the available repl commands and a brief description"
            )
        }

    def _repl_bot_start(self, _args: list[str]) -> None:
        if not self.bot_running:
            if quit_event.is_set():
                quit_event.clear()

            self.bot_thread.start()
            self.bot_running = True
            repl_log.info("Bot has started.")
        else:
            repl_log.info("Bot is already running")

    def _repl_bot_stop(self, _args: list[str]) -> None:
        if self.bot_running:
            quit_event.set()
            self.bot_thread.join()
            self.bot_running = False
            repl_log.info("Bot has stopped.")
        else:
            repl_log.info("Bot is not running so there's nothing to kill")

    def _repl_commit(self, _args: list[str]) -> None:
        repl_log.info(f"Local commit:  {self.get_current_commit(use_remote=False)}")
        repl_log.info(f"Remote commit: {self.get_current_commit(use_remote=True)}")

    def _repl_quit(self, _args: list[str]) -> None:
        repl_log.info(f"Quitting...")
        self.should_quit = True

    def _repl_help(self, _args: list[str]) -> None:
        repl_log.info("Listed below are all the available commands")
        for cmd, rc in self.repl_cmds.items():
            repl_log.info(f"{cmd:^15} |   {rc.desc}")

    def _repl_set_freq(self, args: list[str]) -> None:
        try:
            new_freq = int(args[0].strip())
        except Exception as e:
            repl_log.warn(f"Unable to parse {args[0]} into an integer")
            repl_log.warn(f"{repr(e)}")
            repl_log.info(f"Keeping previous frequency of {self.freq}")
            return

        repl_log.info(f"Changing check frequency from {self.freq} to {new_freq}")
        self.freq = new_freq

    @property
    def gap_between_checks(self) -> timedelta:
         return timedelta(hours=24 / self.freq)

    def run(self) -> None:
        self.last_check = self.now

        while not self.should_quit:
            if self.now - self.last_check >= self.gap_between_checks:
                self.sync_w_remote()
                self.last_check = self.now

            user_input: str = input("> ")
            repl_log.debug(f"Input received: '{user_input}'")

            parts = user_input.split()
            if parts[0] not in self.repl_cmds.keys():
                repl_log.warn(f"Unknown subcommand provided: '{parts[0]}'")
                continue

            self.repl_cmds[parts[0]].func(parts[1:])
            self.now = datetime.now()

        if self.bot_running:
            self._repl_bot_stop([])

    def run_cmd(self, cmd: list[str]) -> CmdOutput:
        try:
            repl_log.debug(f"cmd: {cmd}")
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=False
            )
            return CmdOutput(proc.returncode, proc.stdout, proc.stderr)
        except Exception as e:
            repl_log.fatal(f"Failed to run cmd ({cmd}): {repr(e)}")

    def get_all_commits(self, use_remote: bool) -> list[str]:
        cmd_args = ["git", "log", "--oneline"]
        if use_remote:
            cmd_args.extend(["origin", "main"])

        output = self.run_cmd(cmd_args)
        if output.code != 0:
            repl_log.error(f"subcmd exited with code {output.code}")
            repl_log.error(f"stdout: {output.stderr}")
            sys.exit(1)

        print(output.stdout)

        # Parse git commit logs
        hashes: list[str] = []
        lines: list[str] = output.stdout.splitlines()
        for line in lines:
            parts: list[str] = line.split()
            hashes.append(parts[0])

        return hashes

    def get_local_branch(self) -> str:
        cmd = self.run_cmd(["git", "rev-parse", "--abbrev-ref", "HEAD"])

        if cmd.code != 0:
            repl_log.error(f"stderr: {cmd.stderr}")
            repl_log.error("failed to get current branch")

        return cmd.stdout.strip()

    def get_current_commit(self, use_remote: bool) -> str:
        dest = "origin/main" if use_remote else "HEAD"
        cmd = self.run_cmd(["git", "rev-parse", dest])

        if cmd.code != 0:
            repl_log.error(f"stderr: {cmd.stderr}")
            repl_log.error("failed to get current commit hash")

        return cmd.stdout.strip()

    def fetch_latest(self):
        cmd = self.run_cmd(["git", "fetch", "origin"])
        if cmd.code != 0:
            repl_log.error(cmd.stderr)
            repl_log.error("fetched latest changes from origin")
        else:
            repl_log.error("failed to fetch latest change from origin")

    def sync_w_remote(self):
        self.fetch_latest()

        local_commit = self.get_current_commit(use_remote=False)
        remote_commit = self.get_current_commit(use_remote=True)
        if local_commit != remote_commit:
            cmd = self.run_cmd(["git", "pull", "origin", "main"])
            if cmd.code != 0:
                repl_log.error(f"stderr: {cmd.stderr}")
                repl_log.error("failed to sync changes with remote")

# ============================================================================

Runner().run()
