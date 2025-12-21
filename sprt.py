import os
import subprocess
import tempfile

FASTCHESS = "/Users/ambujshukla/fastchess/fastchess"
VENV_PYTHON = os.path.abspath(".venv/bin/python3")
MAIN_SCRIPT = "src/main.py"

def main():
    cwd = os.getcwd()

    logs_dir = os.path.join(cwd, "logs")
    os.makedirs(logs_dir, exist_ok=True)

    log_new = os.path.join(logs_dir, "new_engine.log")
    log_old = os.path.join(logs_dir, "old_engine.log")

    openings_file = os.path.join(cwd, "8moves_v3.pgn")
    # pgn_out = os.path.join(cwd, "games.pgn")

    with tempfile.TemporaryDirectory() as temp_dir:
        subprocess.run(["git", "clone", ".", temp_dir], check=True, capture_output=True)
        subprocess.run(["git", "checkout", "HEAD~1"], cwd=temp_dir, check=True, capture_output=True)

        cmd_new_shell = f"cd {cwd} && {VENV_PYTHON} -u {MAIN_SCRIPT} 2>&1 | tee {log_new}"
        cmd_old_shell = f"cd {temp_dir} && {VENV_PYTHON} -u {MAIN_SCRIPT} 2>&1 | tee {log_old}"

        fastchess_args = [
            FASTCHESS,

            "-engine",
            "cmd=/bin/sh",
            f"args=-c '{cmd_new_shell}'",
            "name=New",

            "-engine",
            "cmd=/bin/sh",
            f"args=-c '{cmd_old_shell}'",
            "name=Old",

            "-openings", f"file={openings_file}", "format=pgn", "order=random",
            # "-pgnout", f"file={pgn_out}",

            "-each", "tc=10+0.5",
            "-rounds", "100", "-repeat",
            "-concurrency", "8",
            "-recover",

            # tweak elo0 and elo1 here
            "-sprt", "elo0=-20", "elo1=0", "alpha=0.05", "beta=0.05"
        ]

        subprocess.run(fastchess_args)


if __name__ == "__main__":
    main()

# https://www.dogeystamp.com/chess3/
# read the lines just before "interpreting the output"