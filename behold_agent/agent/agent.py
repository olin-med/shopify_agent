from google.adk.agents import Agent
from .prompt import BEHOLD_AGENT_PROMPT
from .tools import fetch_shopify_graphql, validate_graphql_with_mcp, introspect_graphql_schema


root_agent = Agent(
    model="gemini-2.0-flash",
    name="behold_agent",
    description=(
        "Intelligent Shopify sales assistant that proactively helps customers by automatically accessing store data "
        "to provide product recommendations, answer questions, and guide purchasing decisions."
    ),
    instruction=(BEHOLD_AGENT_PROMPT),
    tools=[fetch_shopify_graphql, validate_graphql_with_mcp, introspect_graphql_schema],
)
