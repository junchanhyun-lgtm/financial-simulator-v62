import subprocess
import sys
from pathlib import Path


ROOT_DIR = Path(__file__).resolve().parents[1]


PYTHON_FILES = [
    "app.py",
    "config.py",
    "utils.py",
    "data_defaults.py",
    "simulator.py",
    "ui_inputs.py",
    "params_builder.py",
    "ui_layout.py",
    "simulation_runner.py",
    "result_state.py",
    "ui_results.py",
    "tools/check_simulator_equivalence.py",
]


def run_command(command):
    print(f"\n> {' '.join(command)}")
    result = subprocess.run(command, cwd=ROOT_DIR)

    if result.returncode != 0:
        raise SystemExit(result.returncode)


def main():
    run_command([sys.executable, "-m", "py_compile", *PYTHON_FILES])
    run_command([sys.executable, "tools/check_simulator_equivalence.py"])

    print("\nOK: project checks passed.")


if __name__ == "__main__":
    main()