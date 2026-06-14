# agents/root_agent.py

from google.adk.agents import SequentialAgent

from agents.order_intake_agent import order_intake_agent
from agents.data_query_agent import data_query_agent
from agents.planner_agent import planner_agent
from agents.executor_agent import executor_agent
from agents.notify_agent import notify_agent


root_agent = SequentialAgent(
    name="ai_kitchen_coordinator_agent",
    description=(
        "AI Kitchen Coordinator workflow. "
        "It coordinates order understanding, resource assessment, production planning, "
        "equipment execution, and notification/escalation."
    ),
    sub_agents=[
        order_intake_agent,
        data_query_agent,
        planner_agent,
        executor_agent,
        notify_agent,
    ],
)