# agents/root_agent.py

from google.adk.agents import SequentialAgent

from agents.data_query_agent import data_query_agent
from agents.planner_agent import planner_agent
from agents.executor_agent import executor_agent
from agents.notify_agent import notify_agent


root_agent = SequentialAgent(
    name="ai_kitchen_root_agent",
    description=(
        "AI Kitchen ADK root workflow. "
        "It runs DataQueryAgent, PlannerAgent, ExecutorAgent, and NotifyAgent in sequence."
    ),
    sub_agents=[
        data_query_agent,
        planner_agent,
        executor_agent,
        notify_agent,
    ],
)