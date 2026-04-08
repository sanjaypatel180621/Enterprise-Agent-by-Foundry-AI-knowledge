import os
import sys
import aiohttp
import json
import asyncio
from typing import List
from pathlib import Path

# Add parent directory to path for imports
sys.path.append(str(Path(__file__).parent.parent))

class AzureSearchTool:
   """
   Async MCP-like tool to query Azure Cognitive Search index.
   Reads endpoint/key/index from environment and returns joined content snippets.
   """
   def __init__(self):
      self.endpoint = os.getenv("AZURE_SEARCH_ENDPOINT")
      self.api_key = os.getenv("AZURE_SEARCH_API_KEY")
      self.index_name = os.getenv("AZURE_SEARCH_INDEX")
      if not all([self.endpoint, self.api_key, self.index_name]):
            raise RuntimeError("Azure Search env vars not set (AZURE_SEARCH_ENDPOINT/KEY/INDEX).")
      if not self.endpoint.endswith('/'):
            self.endpoint += '/'
      self.api_version = "2023-11-01"

   async def search(self, query: str, top: int = 5) -> str:
      """
      Query the Azure Search index and return concatenated content snippets.
      """
      url = f"{self.endpoint}indexes/{self.index_name}/docs/search?api-version={self.api_version}"
      headers = {"Content-Type": "application/json", "api-key": self.api_key}
      body = {"search": query, "top": top}

      async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=body) as resp:
               if resp.status != 200:
                  text = await resp.text()
                  raise RuntimeError(f"Azure Search error {resp.status}: {text}")
               data = await resp.json()
               docs = data.get("value", [])
               snippets: List[str] = []
               for d in docs:
                  snippet = d.get("content") or d.get("text") or d.get("description") or json.dumps(d)
                  snippets.append(snippet.strip())
               return "\n\n".join(snippets) if snippets else "No results found."

   async def health_check(self):
      """Check if Azure Search service is accessible."""
      try:
            url = f"{self.endpoint}indexes/{self.index_name}?api-version={self.api_version}"
            headers = {"Content-Type": "application/json", "api-key": self.api_key}
            
            async with aiohttp.ClientSession() as session:
               async with session.get(url, headers=headers) as resp:
                  return {
                        "status": "healthy" if resp.status == 200 else "unhealthy",
                        "status_code": resp.status,
                        "endpoint": self.endpoint,
                        "index": self.index_name
                  }
      except Exception as e:
            return {
               "status": "error",
               "error": str(e),
               "endpoint": self.endpoint,
               "index": self.index_name
            }

# Example usage and testing
async def main():
   """Test the Azure Search tool"""
   try:
      # Load environment variables
      from utils.env import load_env
      load_env()
      
      # Initialize search tool
      search_tool = AzureSearchTool()
      
      # Health check
      health = await search_tool.health_check()
      print(f"Health Status: {json.dumps(health, indent=2)}")
      
      # Test search
      test_queries = [
            "travel reimbursement policy",
            "GDPR compliance requirements", 
            "employee leave policies"
      ]
      
      for query in test_queries:
            print(f"\n{'='*60}")
            print(f"Testing search: {query}")
            print('='*60)
            
            result = await search_tool.search(query, top=3)
            print(result)
            
   except Exception as e:
      print(f"Error testing Azure Search tool: {e}")

if __name__ == "__main__":
   import asyncio
   asyncio.run(main())