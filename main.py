import asyncio
import time
import logging
import re
import sys
import os
from typing import Dict, Any
from utils.env import load_env
from agents.planner_agent import build_planner_agent, classify_target
from agents.hr_agent import build_hr_agent
from agents.compliance_agent import build_compliance_agent
from agents.finance_agent import build_finance_agent
from tools.azure_search_tool import AzureSearchTool
from tools.freshdesk_tool import FreshdeskTool

if sys.platform == "win32":
   os.environ.setdefault("PYTHONUTF8", "1")
   if sys.stdout.encoding != "utf-8":
      sys.stdout.reconfigure(encoding="utf-8")
      sys.stderr.reconfigure(encoding="utf-8")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def parse_create_ticket_block(response_text: str) -> Dict[str, Any]:
   """
   Parse CREATE_TICKET block from agent response.
   """
   if "CREATE_TICKET" not in response_text:
      return None
   
   # Extract the CREATE_TICKET block
   lines = response_text.split('\n')
   ticket_start = -1
   
   for i, line in enumerate(lines):
      if line.strip() == "CREATE_TICKET":
            ticket_start = i
            break
   
   if ticket_start == -1:
      return None
   
   # Parse ticket details
   ticket_data = {
      "subject": "",
      "body": "",
      "tags": [],
      "email": "system@enterprise.com",
      "name": "Enterprise System User"
   }
   
   # Process lines after CREATE_TICKET
   for line in lines[ticket_start + 1:]:
      line = line.strip()
      if not line:
            continue
            
      if line.startswith("Subject:"):
            ticket_data["subject"] = line[8:].strip()
      elif line.startswith("Body:"):
            ticket_data["body"] = line[5:].strip()
      elif line.startswith("Tags:"):
            tags_str = line[5:].strip()
            if tags_str:
               ticket_data["tags"] = [tag.strip() for tag in tags_str.split(',')]
      elif line.startswith("Email:"):
            ticket_data["email"] = line[6:].strip()
      elif line.startswith("Name:"):
            ticket_data["name"] = line[5:].strip()
   
   return ticket_data

async def run_multi_agent_with_user_info(query: str, agents: Dict[str, Any], user_name: str = None) -> Dict[str, Any]:
   """
   Enhanced multi-agent system with CREATE_TICKET pattern support and user name handling.
   """
   start_time = time.time()
   
   try:
      # Step 1: Route the query
      logging.info(f"Routing query: {query[:50]}...")
      target = await classify_target(agents["planner"], query)
      logging.info(f"Query routed to: {target}")
      
      # Step 2: Retrieve relevant context using Azure Search
      logging.info("Retrieving context from knowledge base...")
      context = await agents["search_tool"].search(query, top=3)
      
      # Step 3: Create enriched prompt with context
      enriched_prompt = f"""
Context from Knowledge Base:
{context}

---

User Question: {query}

Please provide a comprehensive answer based on the context above. If no relevant context is found, provide your best guidance based on your training.
"""
      
      # Step 4: Get agent response
      agent_key = target.lower()
      agent_name = f"{target}Agent"
      
      if agent_key in agents:
            logging.info(f"Processing with {agent_name}...")
            answer = await agents[agent_key].run(enriched_prompt)
      else:
            # Fallback to HR if routing unclear
            logging.warning(f"Unknown target '{target}', falling back to HR")
            answer = await agents["hr"].run(enriched_prompt)
            target = "HR"
            agent_name = "HRAgent"
      
      answer_text = str(answer)
      
      # Step 5: Check for CREATE_TICKET pattern in response
      ticket_info = None
      ticket_created = False
      
      ticket_data = parse_create_ticket_block(answer_text)
      
      if ticket_data and "freshdesk_tool" in agents:
            logging.info("CREATE_TICKET pattern detected - creating Freshdesk ticket")
            
            # Use provided user name if available
            if user_name:
               ticket_data["name"] = user_name
               logging.info(f"Using provided user name: {user_name}")
            
            try:
               # Create ticket using parsed data
               ticket_result = await agents["freshdesk_tool"].create_ticket(
                  subject=ticket_data["subject"] or f"{target} Request: {query[:60]}...",
                  description=ticket_data["body"] or f"Request: {query}\n\nAgent Response:\n{answer_text}",
                  tags=ticket_data["tags"] or [target.lower(), "agent-system"],
                  requester={
                        "name": ticket_data["name"],
                        "email": ticket_data["email"]
                  }
               )
               
               if ticket_result.get("success"):
                  ticket_info = ticket_result
                  ticket_created = True
                  ticket_id = ticket_result.get("ticket", {}).get("id")
                  ticket_url = ticket_result.get("ticket", {}).get("url")
                  
                  # Replace CREATE_TICKET block with success message
                  if "CREATE_TICKET" in answer_text:
                        # Remove the CREATE_TICKET block and replace with success message
                        lines = answer_text.split('\n')
                        filtered_lines = []
                        skip_ticket_block = False
                        
                        for line in lines:
                           if line.strip() == "CREATE_TICKET":
                              skip_ticket_block = True
                              # Add success message with user name
                              success_msg = f"""
🎫 **Support Ticket Created Successfully**
- Ticket ID: #{ticket_id}
- Subject: {ticket_data["subject"]}
- Requester: {ticket_data["name"]}
- Status: Open
- URL: {ticket_url}

Your request has been submitted to our {target} team. You will receive updates via email.
"""
                              filtered_lines.append(success_msg)
                              continue
                           elif skip_ticket_block and (line.startswith("Subject:") or line.startswith("Body:") or 
                                                      line.startswith("Tags:") or line.startswith("Email:") or 
                                                      line.startswith("Name:")):
                              continue
                           else:
                              skip_ticket_block = False
                              filtered_lines.append(line)
                        
                        answer_text = '\n'.join(filtered_lines)
               else:
                  answer_text += f"\n\n⚠️ **Note**: Could not create support ticket: {ticket_result.get('error', 'Unknown error')}"
                  
            except Exception as e:
               logging.error(f"Failed to create Freshdesk ticket: {e}")
               answer_text += f"\n\n⚠️ **Note**: Ticket creation failed: {str(e)}"
      
      # Step 6: Process response
      response_time = time.time() - start_time
      
      return {
            "query": query,
            "routed_to": target,
            "agent_name": agent_name,
            "answer": answer_text,
            "context_retrieved": len(context) > 100,  # Simple check if context was found
            "ticket_created": ticket_created,
            "ticket_info": ticket_info,
            "response_time": round(response_time, 2),
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "success": True,
            "user_name": user_name
      }
      
   except Exception as e:
      logging.error(f"Multi-agent processing error: {e}")
      return {
            "query": query,
            "routed_to": "Error",
            "agent_name": "ErrorHandler",
            "answer": f"I encountered an error processing your request: {str(e)}. Please try again.",
            "context_retrieved": False,
            "ticket_created": False,
            "ticket_info": None,
            "response_time": 0,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "success": False,
            "user_name": user_name
      }

async def run_multi_agent(query: str, agents: Dict[str, Any]) -> Dict[str, Any]:
   """
   Wrapper for multi-agent system with no user name.
   """
   return await run_multi_agent_with_user_info(query, agents, None)

def format_response(result: Dict[str, Any]) -> str:
   """Format the agent response for display."""
   status_icon = "✅" if result["success"] else "❌"
   context_icon = "📚" if result.get("context_retrieved") else "📭"
   ticket_icon = "🎫" if result.get("ticket_created") else ""
   
   formatted = f"""
{status_icon} Agent Response Summary:
┌─ Routed to: {result['routed_to']} ({result['agent_name']})
├─ Response time: {result['response_time']}s
├─ Context retrieved: {context_icon} {'Yes' if result.get('context_retrieved') else 'No'}
├─ Ticket created: {ticket_icon} {'Yes' if result.get('ticket_created') else 'No'}
├─ Timestamp: {result['timestamp']}
└─ Status: {'Success' if result['success'] else 'Error'}

💬 Answer:
{result['answer']}
"""
   
   # Add ticket details if available
   if result.get("ticket_info") and result["ticket_info"].get("success"):
      ticket = result["ticket_info"]["ticket"]
      formatted += f"""

🎫 Ticket Details:
├─ ID: #{ticket['id']}
├─ Status: {ticket['status']}
├─ Priority: {ticket['priority']}
└─ URL: {ticket['url']}
"""
   
   return formatted

async def interactive_ticket_creation(agents: Dict[str, Any], base_query: str) -> Dict[str, Any]:
   """
   Simple interactive ticket creation.
   """
   print("\n🎫 **Manual Ticket Creation**")
   print("I'll help you create a support ticket manually.\n")
   
   try:
      # Get basic ticket details
      subject = input(f"📝 Ticket Subject: ").strip() or f"Manual Request: {base_query[:60]}..."
      
      print("\n📄 **Ticket Description** (press Enter twice when done):")
      description_lines = [f"Original Request: {base_query}", ""]
      while True:
            line = input("   ").strip()
            if not line:
               break
            description_lines.append(line)
      
      description = "\n".join(description_lines)
      
      # Create the ticket directly
      print(f"\n🚀 Creating ticket: '{subject}'...")
      
      ticket_result = await agents["freshdesk_tool"].create_ticket(
            subject=subject,
            description=description,
            tags=["manual", "interactive"],
            requester={
               "name": "Enterprise System User", 
               "email": "system@enterprise.com"
            }
      )
      
      if ticket_result.get("success"):
            ticket_info = ticket_result.get("ticket", {})
            print(f"""
✅ **Ticket Created Successfully!**

🎫 Ticket Details:
   • ID: #{ticket_info.get('id')}
   • Subject: {subject}
   • Status: Open
   • URL: {ticket_info.get('url')}

📧 You will receive email updates about your ticket status.
            """)
            return {
               "success": True,
               "ticket_created": True,
               "ticket_info": ticket_result
            }
      else:
            print(f"❌ **Failed to create ticket**: {ticket_result.get('error', 'Unknown error')}")
            return {"success": False, "ticket_created": False}
            
   except KeyboardInterrupt:
      print("\n🚫 Ticket creation cancelled.")
      return {"success": False, "ticket_created": False}
   except Exception as e:
      print(f"❌ **Error during ticket creation**: {str(e)}")
      return {"success": False, "ticket_created": False}

async def run_interactive_mode(agents: Dict[str, Any]):
   """Interactive mode for real-time queries with enhanced ticket creation."""
   print("\n🤖 Enterprise Agent System - Interactive Mode")
   print("Available agents: HR, Finance, Compliance")
   print("Type 'quit' to exit, 'help' for commands, 'ticket' for interactive ticket creation\n")
   
   while True:
      try:
            query = input("Enter your question: ").strip()
            
            if query.lower() in ['quit', 'exit', 'q']:
               print("👋 Goodbye!")
               break
            elif query.lower() == 'help':
               print("""
📋 Available Commands:
- Ask any question about HR, Finance, or Compliance
- 'ticket' - Interactive ticket creation mode
- 'quit' or 'exit' - Exit the system
- 'help' - Show this help message

🎯 Example questions:
- "What's the travel reimbursement limit for meals?"
- "I need to create a ticket for sick leave"
- "Can you help me submit a reimbursement request?"
- "How many vacation days do employees get?"
- "Do we need GDPR compliance for EU customers?"

🎫 Ticket Creation:
- Use 'ticket' command for guided ticket creation
- Or include phrases like "create ticket", "submit request" in your question
- For LEAVE and REIMBURSEMENT requests, you'll be prompted for your name
""")
               continue
            elif query.lower() == 'ticket':
               if "freshdesk_tool" not in agents:
                  print("❌ Ticket creation is not available (Freshdesk tool not configured)")
                  continue
               
               base_query = input("📝 Describe what you need help with: ").strip()
               if base_query:
                  await interactive_ticket_creation(agents, base_query)
               continue
            elif not query:
               continue
               
            # Check if this is a leave or reimbursement request that needs user name
            query_lower = query.lower()
            is_leave_request = any(word in query_lower for word in ["leave", "vacation", "sick", "time off", "pto", "holiday"])
            is_reimbursement_request = any(word in query_lower for word in ["reimburse", "expense", "travel", "receipt", "reimbursement"])
            wants_ticket = any(keyword in query_lower for keyword in ["create ticket", "submit ticket", "file ticket", "raise ticket", 
                              "create request", "submit request", "file request", "need help with",
                              "open ticket", "new ticket", "support ticket", "help ticket"])
            
            user_name = None
            if (is_leave_request or is_reimbursement_request) and wants_ticket:
               print("\n👤 For leave and reimbursement requests, I need to collect some information:")
               user_name = input("Please enter your name: ").strip()
               if not user_name:
                  print("❌ Name is required for this type of request. Please try again.")
                  continue
               print(f"✅ Thank you, {user_name}! Processing your request...")
               
            print("\n🤔 Processing your query...")
            result = await run_multi_agent_with_user_info(query, agents, user_name)
            print(format_response(result))
            print()  # Add spacing between queries
            
      except KeyboardInterrupt:
            print("\n👋 Goodbye!")
            break
      except Exception as e:
            logging.error(f"Interactive mode error: {e}")
            print(f"❌ Error: {e}")
            print()

async def run_batch_tests(agents: Dict[str, Any]):
   """Run focused test with ticket creation."""
   test_queries = [
      "I need to create a ticket for my travel reimbursement request"
   ]
   
   print("🧪 Running focused batch tests with grounded data integration...\n")
   
   for i, query in enumerate(test_queries, 1):
      print(f"{'='*80}")
      print(f"TEST {i}/{len(test_queries)}: {query}")
      print(f"{'='*80}")
      
      result = await run_multi_agent(query, agents)
      print(format_response(result))
      
      # Small delay between queries for better readability
      if i < len(test_queries):
            await asyncio.sleep(1.0)  # Longer delay for tool operations

async def main():
   """Main application entry point with enhanced features and tool integration."""
   print("🚀 Initializing Enterprise Agent System with Tools...")
   
   try:
      # Load environment and build agents
      load_env()
      logging.info("Building agent network...")
      
      # Build core agents
      agents = {
            "planner": await build_planner_agent(),
            "hr": await build_hr_agent(), 
            "compliance": await build_compliance_agent(),
            "finance": await build_finance_agent()
      }
      
      # Initialize and attach tools
      logging.info("Initializing tools...")
      
      try:
            search_tool = AzureSearchTool()
            agents["search_tool"] = search_tool
            
               
      except Exception as e:
            logging.error(f"Failed to initialize Azure Search tool: {e}")
            # Create mock search tool for testing
            class MockSearchTool:
               async def search(self, query, top=3):
                  return f"📭 Mock search results for: {query}\n(Azure Search tool not configured)"
            agents["search_tool"] = MockSearchTool()
      
      # Initialize Freshdesk tool for ticket creation
      try:
            freshdesk_tool = FreshdeskTool()
            agents["freshdesk_tool"] = freshdesk_tool
            logging.info("✅ Freshdesk tool initialized successfully")
      except Exception as e:
            logging.warning(f"⚠️ Freshdesk tool initialization failed: {e}")
            # System will work without Freshdesk, just won't create tickets
      
      logging.info("✅ All agents and tools initialized")
      
      # Check if running interactively or in batch mode
      import sys
      if len(sys.argv) > 1 and sys.argv[1] == "--interactive":
            await run_interactive_mode(agents)
      else:
            await run_batch_tests(agents)
            
   except Exception as e:
      logging.error(f"System initialization failed: {e}")
      print(f"❌ Failed to start system: {e}")
      
      # Try to run with minimal configuration
      logging.info("Attempting to run with minimal configuration...")
      try:
            minimal_agents = {
               "planner": await build_planner_agent(),
               "hr": await build_hr_agent(),
               "compliance": await build_compliance_agent(), 
               "finance": await build_finance_agent(),
               "search_tool": type('MockSearch', (), {'search': lambda self, q, top=3: f"Mock search for: {q}"})()
            }
            await run_batch_tests(minimal_agents)
      except Exception as minimal_error:
            print(f"❌ Even minimal configuration failed: {minimal_error}")

if __name__ == "__main__":
   asyncio.run(main())