import subprocess
import os

PROJECT_DIR = "/Users/gustavogongora/tienda_gongora"
VENV_PYTHON = "/Users/gustavogongora/joyeriagongora/bin/python"

def run_tailwind():
    print("Iniciando observador Tailwind (en segundo plano)...")
    return subprocess.Popen(
        [VENV_PYTHON, "manage.py", "tailwind", "start"],
        cwd=PROJECT_DIR,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )

def run_server():
    print("Levantando Django runserver...")
    proc = subprocess.Popen(
        [VENV_PYTHON, "manage.py", "runserver"],
        cwd=PROJECT_DIR,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True
    )
    for line in proc.stdout:
        print(line, end="")
    proc.wait()

if __name__ == "__main__":
    tailwind_proc = run_tailwind()
    run_server()