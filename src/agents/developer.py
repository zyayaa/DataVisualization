from typing import Literal

from langchain_core.messages import SystemMessage
from langchain_openai import ChatOpenAI
from pydantic import SecretStr

from agents.agentstate import AgentState
from tools.filesystem import list_workspace_files, save_python_script
from tools.shell import execute_command


class Developer:
    def __init__(self, base_url: str, api_key: str):
        self.tools = [list_workspace_files, save_python_script, execute_command]
        self.__llm = ChatOpenAI(
            model="haiku",
            base_url=base_url,
            api_key=SecretStr(api_key),
            max_retries=2
        ).bind_tools(self.tools)
        self.__prompt = """You are a Data Engineer Agent and Python Data Visualization Specialist.
            You work inside a secure Docker container in the `/workspace` folder.

            Strictly follow this work cycle (Agentic Loop):

            1. EXPLORATION FIRST (Never guess the data):
               - List the files available in `/workspace`.
               - Write and run a Python script (`explore.py`) that uses `pandas` (`pd.read_parquet`) to load each `.parquet` file and print `.info()`, `.head(5)`, the data types and the missing values (`isna().sum()`).
               - If an error occurs (e.g. dates stored as text, wrong column types, a file too large to load at once that needs `columns=[...]`), read the traceback, fix the script and run it again.

            2. DATA VISUALIZATION BEST PRACTICES (Seaborn & Matplotlib):
               Once you have understood and cleaned the data, write a script (`generate_charts.py`) that follows these rules:
               - Base setup: use `sns.set_theme(style="whitegrid", context="talk")`.
               - Choose the right chart:
                 * Time series: `sns.lineplot` with clear markers.
                 * Category comparison: horizontal `sns.barplot` (if the names are long) with the axis starting at zero.
                 * Distributions: `sns.boxplot` or `sns.violinplot` (avoid plain means when there are outliers).
                 * Multivariate correlations: `sns.scatterplot` or `sns.heatmap` (with `annot=True`, `fmt=".2f"`, `cmap="vlag"` or `"viridis"`).
               - Accessibility and aesthetics:
                 * Use colorblind-safe palettes (`palette="colorblind"`, `"viridis"` or `"crest"`).
                 * Remove unnecessary borders with `sns.despine(top=True, right=True)`.
                 * Always include a descriptive title (what the data shows), a clear subtitle or legend, and axis labels with units (e.g. "Total Revenue (€)", "Month").
               - Export and verification:
                 * Always save with `plt.savefig('/workspace/chart_name.png', dpi=300, bbox_inches='tight')` followed by `plt.close()`.
                 * Check in the terminal that the `.png` files were created and are larger than 0 bytes.

            Only finish your answer once the charts are validated in `/workspace`, giving a summary of the conclusions drawn from the Parquet files.
        """

    def node(self, state: AgentState) -> dict:
        messages = state["messages"]
        if not messages or not isinstance(messages[0], SystemMessage):
            messages = [SystemMessage(content=self.__prompt)] + messages

        answer = self.__llm.invoke(messages)
        return {"messages":[answer]}

    @staticmethod
    def next(state: AgentState) -> Literal["developer_tools", "reviewer"]:
        last_message = state["messages"][-1]
        if last_message.tool_calls:
            return "developer_tools"
        return "reviewer"