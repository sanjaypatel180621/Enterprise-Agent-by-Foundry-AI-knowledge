import os
import asyncio
from agent_framework.azure import AzureOpenAIResponsesClient  # type: ignore

async def build_hr_agent():
   """
   Creates and configures an HR specialist agent for handling employee-related queries.
   
   Returns:
      An agent client configured with HR policy expertise and guidance instructions.
   """
   # Initialize Azure OpenAI client with credentials from environment variables
   client = AzureOpenAIResponsesClient(
      api_key=os.getenv("AZURE_OPENAI_API_KEY"),
      endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
      deployment_name=os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"),
      api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
   )
   
   # Create HR specialist agent with comprehensive employment and policy knowledge
   return client.create_agent(
      name="HRAgent",
      instructions=(
            "If the user asks to create a ticket (phrases like \"create a ticket\", \"submit a leave request\", \"open a support ticket\"), output a structured block starting with:\n"
            "CREATE_TICKET\n"
            "Subject: <one-line subject>\n"
            "Body: <detailed description>\n"
            "Tags: tag1,tag2 (optional)\n"
            "Email: john.doe@example.com (optional)\n"
            "Name: John Doe (optional)\n"
            "Return only the CREATE_TICKET block when requesting a ticket; do not call any APIs yourself.\n\n"
            "Provide specific, actionable guidance with policy references where applicable. "
            "Be empathetic and professional in your responses."
      ),
   )