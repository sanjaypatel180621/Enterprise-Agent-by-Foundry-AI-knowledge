import os
import asyncio
from agent_framework.azure import AzureOpenAIResponsesClient  # type: ignore

async def build_planner_agent():
   """
   Creates and configures a planner agent that routes user queries to appropriate specialists.
   
   Returns:
      An agent client configured with routing instructions for HR, Finance, and Compliance queries.
   """
   # Initialize Azure OpenAI client with credentials from environment variables
   client = AzureOpenAIResponsesClient(
      api_key=os.getenv("AZURE_OPENAI_API_KEY"),
      endpoint=os.getenv("AZURE_OPENAI_ENDPOINT"),
      deployment_name=os.getenv("AZURE_OPENAI_RESPONSES_DEPLOYMENT_NAME"),
      api_version=os.getenv("AZURE_OPENAI_API_VERSION"),
   )
   
   # Create agent with specialized routing instructions
   return client.create_agent(
      name="PlannerAgent",
      instructions=(
            "You are an intelligent routing agent. Analyze user queries and route them to the appropriate specialist. "
            "Available specialists:\n"
            "- HR: Employee policies, leave, benefits, working hours, performance, hiring\n"
            "- FINANCE: Reimbursements, expenses, budgets, travel costs, meal allowances, equipment purchases\n"
            "- COMPLIANCE: GDPR, data privacy, regulatory requirements, legal compliance, audits\n\n"
            "Return exactly one word: HR, FINANCE, or COMPLIANCE. "
            "Consider keywords like: money, cost, budget, reimburse, expense, payment, allowance → FINANCE\n"
            "Keywords like: leave, sick, vacation, policy, employee, benefits → HR\n"
            "Keywords like: GDPR, privacy, compliance, legal, audit, regulation → COMPLIANCE"
      ),
   )

async def classify_target(planner_agent, user_query: str) -> str:
   """
   Classifies a user query and routes it to the appropriate department using the planner agent.
   
   Args:
      planner_agent: The initialized planner agent instance
      user_query: The user's question or request to be classified
      
   Returns:
      str: One of "HR", "FINANCE", or "COMPLIANCE" indicating the target department
   """
   # Send the query to the planner agent for classification
   result = await planner_agent.run(
      "Analyze and route this query:\n\n"
      f"User query: {user_query}\n\n"
      "Return exactly one word: HR, FINANCE, or COMPLIANCE."
   )
   
   # Extract and normalize the text response from the agent
   text = str(result).strip().lower()
   
   # Primary classification: Check if agent response contains department names
   if "finance" in text or "financial" in text:
      return "FINANCE"
   elif "hr" in text or "human" in text:
      return "HR"
   elif "compliance" in text or "legal" in text:
      return "COMPLIANCE"
   else:
      # Fallback mechanism: If agent response is unclear, use keyword-based scoring
      query_lower = user_query.lower()
      
      # Define keyword lists for each department category
      finance_keywords = ["reimburs", "expense", "cost", "budget", "money", "payment", "allowance", "travel", "meal", "flight", "hotel"]
      hr_keywords = ["leave", "sick", "vacation", "employee", "benefit", "policy", "hire", "performance", "work"]
      compliance_keywords = ["gdpr", "privacy", "compliance", "legal", "audit", "regulation", "data protection"]
      
      # Calculate match scores by counting keyword occurrences in the query
      finance_score = sum(1 for keyword in finance_keywords if keyword in query_lower)
      hr_score = sum(1 for keyword in hr_keywords if keyword in query_lower)
      compliance_score = sum(1 for keyword in compliance_keywords if keyword in query_lower)
      
      # Return the department with the highest keyword match score
      if finance_score > hr_score and finance_score > compliance_score:
            return "FINANCE"
      elif hr_score > compliance_score:
            return "HR"
      else:
            return "COMPLIANCE"