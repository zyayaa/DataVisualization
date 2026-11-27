import io
import tarfile

from langchain_core.tools import tool

from tools.sandbox import sandbox


@tool
def list_workspace_files() -> str:
    """List all files in the workspace directory"""
    container = sandbox()
    exit_code, output = container.exec_run("ls -la /workspace")
    return output.decode("utf-8", errors="replace")

@tool
def save_python_script(file_name: str, code: str) -> str:
    """
    Save a Python script inside /workspace in the Docker container.
    Use this tool to write data exploration or graph generation scripts.
    """
    if not file_name.endswith(".py"):
        file_name += ".py"

    clean_name = file_name.split("/")[-1]
    container = sandbox()

    tar_stream = io.BytesIO()
    with tarfile.open(fileobj=tar_stream, mode="w") as tar:
        data_bytes = code.encode("utf-8")
        tarinfo = tarfile.TarInfo(name=clean_name)
        tarinfo.size = len(data_bytes)
        tar.addfile(tarinfo, io.BytesIO(data_bytes))

    tar_stream.seek(0)
    container.put_archive("/workspace", tar_stream)
    return f"File '/workspace/{clean_name}' saved successfully."