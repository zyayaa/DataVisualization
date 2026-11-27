import os

from dotenv import load_dotenv

from agents.developer import Developer

load_dotenv()

from langgraph.prebuilt import ToolNode
from langchain_core.messages import HumanMessage
from langchain_core.runnables import RunnableConfig
from langgraph.constants import START
from langgraph.graph import StateGraph
from agents.agentstate import AgentState

litellmUrl = "http://localhost:4000/v1"
litellmMasterKey = os.getenv("LITELLM_MASTER_KEY")

if not litellmMasterKey:
    raise ValueError("Environment variable LITELLM_MASTER_KEY not set")

if __name__ == "__main__":
    developerAgent = Developer(litellmUrl, litellmMasterKey)

    graph_builder = StateGraph(AgentState)
    graph_builder.add_node("developer", developerAgent.node)
    graph_builder.add_node("developer_tools", ToolNode(developerAgent.tools))

    graph_builder.add_edge(START, "developer")
    graph_builder.add_conditional_edges("developer", developerAgent.next)
    graph_builder.add_edge("developer_tools", "developer")

    graph = graph_builder.compile()

    request = (
        "Explore all .parquet files in /workspace folder. "
        "Focus only on Vila Nova de Famalicao data"
        "Cross data found, identify the principal trends and anomalies, "
        "generate 2 charts in Seaborn that summarize the most important findings"
    )

    humanMessage = HumanMessage(content=request)
    config = RunnableConfig(recursion_limit=100)

    for event in graph.stream(
            {"messages": [humanMessage]},
            config=config,
            stream_mode="values",
    ):
        last_message = event["messages"][-1]
        last_message.pretty_print()