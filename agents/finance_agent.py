import os
import asyncio
from agent_framework.azure import AzureOpenAIResponsesClient  # type: ignore

async def build_finance_agent():
   """
   Creates and configures a Finance specialist agent for handling financial and expense queries.
   
   Returns:
      An agent client configured with finance policy and reimbursement expertise.
   """
   # Initialize Azure OpenAI client with credentials from environment variables
   client = AzureOpenAIResponsesClient(
      api_key=os.getenv("AZURE_OPENAI_API_KEY"),
      endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
      deployment_name=os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"),
      api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
   )
   
   # Create Finance specialist agent with expertise in expenses and reimbursements
   return client.create_agent(
      name="FinanceAgent",
      instructions=(
            "If the user asks to create a ticket (phrases like \"create a ticket\", \"submit a reimbursement request\", \"open a support ticket\"), output a structured block starting with:\n"
         "CREATE_TICKET\n"
         "Subject: <one-line subject>\n"
         "Body: <detailed description>\n"
         "Tags: tag1,tag2 (optional)\n"
         "Email: user@example.com (optional)\n"
         "Name: John Doe (optional)\n"
         "Return only the CREATE_TICKET block when requesting a ticket; do not call any APIs yourself."
      ),
   )