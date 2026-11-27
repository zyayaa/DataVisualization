from langgraph.graph import MessagesState

class AgentState(MessagesState):
    approved: bool
    attempts: int