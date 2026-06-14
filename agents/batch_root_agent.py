# agents/batch_root_agent.py

from google.adk.agents import SequentialAgent

from agents.batch_order_intake_agent import batch_order_intake_agent
from agents.batch_resource_assessment_agent import batch_resource_assessment_agent
from agents.batch_planning_agent import batch_planning_agent
from agents.batch_execution_agent import batch_execution_agent
from agents.batch_notify_agent import batch_notify_agent


root_agent = SequentialAgent(
    name="ai_kitchen_batch_coordinator_agent",
    description=(
        "AI Kitchen batch order coordinator workflow. "
        "It handles multi-order intake, resource assessment, batch planning, "
        "and notification/escalation by using ADK SequentialAgent."
    ),
    sub_agents=[
        batch_order_intake_agent,
        batch_resource_assessment_agent,
        batch_planning_agent,
        batch_execution_agent,
        batch_notify_agent,
    ],
)