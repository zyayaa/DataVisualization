from langchain_core.tools import tool
from tools.sandbox import sandbox


@tool
def execute_command(command: str) -> str:
    """Excutes a bash command inside the Docker container in /workspace and returns the result.
    If the Python script fails, it returns the full Traceback so you can fix the code."""
    container = sandbox()
    safe_cmd = ["timeout", "30s", "bash", "-c", command]

    exit_code, output = container.exec_run(
        safe_cmd,
        workdir="/workspace",
        user="root",
        environment={"PYTHONWARNINGS": "ignore"},
        demux=True
    )

    stdout, stderr = output
    stdout_text = stdout.decode("utf-8", errors="replace") if stdout else ""
    stderr_text = stderr.decode("utf-8", errors="replace") if stderr else ""

    result = f"Exit code: {exit_code}\n"
    if stdout_text:
        result += f"--- STDOUT ---\n{stdout_text}\n"
    if stderr:
        result += f"--- STDERR / TRACEBACK ---\n{stderr_text}\n"

    return result.strip()