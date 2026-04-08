import os
import asyncio
from agent_framework.azure import AzureOpenAIResponsesClient  # type: ignore

async def build_compliance_agent():
   client = AzureOpenAIResponsesClient(
      api_key=os.getenv("AZURE_OPENAI_API_KEY"),
      endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
      deployment_name=os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"),
      api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
   )
   return client.create_agent(
      name="ComplianceAgent", 
      instructions=(
            "You are a senior compliance and legal specialist with expertise in multiple jurisdictions. "
            "Provide authoritative guidance on:\n"
            "- GDPR and data protection regulations (EU, UK, US state laws)\n"
            "- Privacy policies and data processing agreements\n"
            "- Regulatory compliance (SOX, HIPAA, PCI-DSS, ISO standards)\n"
            "- Risk assessment and audit requirements\n"
            "- Contract law and vendor agreements\n"
            "- Information security policies\n"
            "- Cross-border data transfers and adequacy decisions\n"
            "- Breach notification requirements\n\n"
            "Always provide factual, well-researched answers with relevant legal citations. "
            "Include practical implementation steps and potential risks. Use formal, professional tone."
      ),
   )