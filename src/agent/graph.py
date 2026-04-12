"""LangGraph chat agent with OpenAI via OpenRouter.

Demonstrates a single-node graph that makes real LLM calls
via ChatOpenAI, using the LangGraph Platform's MessagesState
for persistent conversation threads.
"""

from __future__ import annotations

from langchain_openai import ChatOpenAI
from langgraph.graph import MessagesState, StateGraph
from langgraph.runtime import Runtime
from typing_extensions import TypedDict


class Context(TypedDict):
    """Runtime context for the agent.

    Set these when creating assistants OR when invoking the graph.
    """

    model_name: str
    system_prompt: str


async def call_model(
    state: MessagesState, runtime: Runtime[Context]
) -> dict:
    """Invoke OpenAI with the conversation messages."""
    context = runtime.context or {}
    model_name = context.get("model_name", "gpt-4o-mini")
    system_prompt = context.get(
        "system_prompt",
        "You are a helpful assistant.",
    )

    model = ChatOpenAI(
        model=model_name,
        base_url="https://openrouter.ai/api/v1",
    )
    messages = [{"role": "system", "content": system_prompt}] + state["messages"]
    response = await model.ainvoke(messages)
    return {"messages": [response]}


# Define the graph
graph = (
    StateGraph(MessagesState, context_schema=Context)
    .add_node(call_model)
    .add_edge("__start__", "call_model")
    .compile(name="ChatBot")
)
