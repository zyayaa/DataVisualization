import base64
import glob
import os
from typing import Literal

from langchain_core.language_models import BaseChatModel
from langchain_core.messages import HumanMessage, SystemMessage
from langgraph.constants import END
from pydantic import BaseModel, Field

from agents.agentstate import AgentState


class VisualReview(BaseModel):
    approved: bool = Field(
        description=(
            "True ONLY if all the charts are legible, without cut or overlapped text, "
            "with units on the axis and without subtotal lines mixed in regions"
        )
    )

    detected_issues: list[str] = Field(
        description="Detailed list of visual, aesthetic or data defects found in the PNG images."
    )

    fix_instructions: str = Field(
        description="Exact instructions of python/seaborn/matplotlib to fix issues on next iteration."
    )


class Reviewer:
    def __init__(self, llm: BaseChatModel):
        self.__llm = llm.with_structured_output(VisualReview)
        self.__max_reviews = 10
        self.__role = (
            "You are a Senior Data Visualization Reviewer (Visual QA). "
            "Rigorously inspect each PNG image below and check:\n"
            "1. Are there overlapping axis labels, numbers on top of bars hitting the top/title, or legends covering data?\n"
            "2. Is there any intruding category such as 'ALL' or 'GRAND TOTAL' that distorts the scale?\n"
            "3. Are the titles, legends and axes clear and well formatted?\n"
            "Be strict: if you find any visual or readability defect, reject it (approved=False) "
            "and explain which Seaborn/Matplotlib parameters the agent should adjust."
        )

    def node(self, state: AgentState) -> dict:
        current_attempt = state.get("attempts", 0) + 1
        png_files = sorted(glob.glob(os.path.join("./workspace", "*.png")))

        if not png_files:
            error_msg = HumanMessage(
                content="No png files found, please try again later.",
            )

            return {
                "messages": [error_msg],
                "approved": False,
                "attempts": current_attempt,
            }

        content_blocks = []

        files_inspected = []
        for path in png_files:
            file_name = os.path.basename(path)
            files_inspected.append(file_name)
            with open(path, "rb") as f:
                img_b64 = base64.b64encode(f.read()).decode("utf-8")

            content_blocks.append({"type": "text", "text": f"--- Image: {file_name} ---"})
            content_blocks.append({"type": "image_url", "image_url": f"data:image/png;base64,{img_b64}"})

            print("\n" + "=" * 70)
            print(f"[INFO] Sending {files_inspected} to inspect (Try {current_attempt}).")
            print("=" * 70)

        evaluation: VisualReview = self.__llm.invoke([SystemMessage(content=""), HumanMessage(content=content_blocks)])

        if evaluation.approved:
            print(f"[INFO] Visual QA approved on try {current_attempt}.")
            return {
                "approved": True,
                "attempts": current_attempt,
            }

        print(f"[INFO] Visual QA failed on try {current_attempt}.")
        for issue in evaluation.detected_issues:
            print(f"  - {issue}")

        print(f"  * Fix needed: {evaluation.fix_instructions}\n")

        feedback_msg = HumanMessage(
            content=(
                    f"[Visual Review failed - Try {current_attempt}/{self.__max_reviews}]\n"
                    f"Files visual inspected {files_inspected} and found the following issues:\n"
                    + "\n".join(f"- {p}" for p in evaluation.detected_issues)
                    + f"\n\nMandatory fix instructions:\n{evaluation.fix_instructions}\n\n"
                      "Modify file 'generate_charts.py', and execute on the shell to overwrite the PNGs and present the final summary."
            )
        )
        return {
            "messages": [feedback_msg],
            "approved": False,
            "attempts": current_attempt,
        }

    def next(self, state: AgentState) -> Literal["developer", "__end__"]:
        if state.get("approved", False):
            return END
        if state.get("attempts", 0) >= self.__max_reviews:
            print("[INFO] Maximum visual review attempts reached. Ending process.")
            return END
        return "developer"
