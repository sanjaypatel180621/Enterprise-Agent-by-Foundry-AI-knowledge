import os
import aiohttp
import base64
import ssl
from typing import Dict, Any, Optional

class FreshdeskTool:
   """
   Async Freshdesk tool to create tickets via Freshdesk REST API.
   """
   def __init__(self):
      self.domain = os.getenv("FRESHDESK_DOMAIN")
      self.api_key = os.getenv("FRESHDESK_API_KEY")
      self.default_priority = int(os.getenv("FRESHDESK_DEFAULT_PRIORITY", "1") or 1)
      self.default_group_id = os.getenv("FRESHDESK_DEFAULT_GROUP_ID") or None

      if not self.domain or not self.api_key:
            raise RuntimeError("Freshdesk domain/API key missing in environment.")

      self.base_url = f"https://{self.domain}/api/v2"
      auth_bytes = f"{self.api_key}:X".encode("utf-8")
      auth_header = base64.b64encode(auth_bytes).decode("utf-8")
      self.headers = {
            "Authorization": f"Basic {auth_header}",
            "Content-Type": "application/json"
      }

   async def create_ticket(self, subject: str, description: str, requester: Optional[Dict[str, str]] = None, tags: Optional[list] = None) -> Dict[str, Any]:
      url = f"{self.base_url}/tickets"
      payload: Dict[str, Any] = {
            "subject": subject,
            "description": description,
            "priority": self.default_priority,
            "status": 2  # 2 = Open status in Freshdesk
      }
      if self.default_group_id:
            try:
               payload["group_id"] = int(self.default_group_id)
            except ValueError:
               pass
      if tags:
            payload["tags"] = tags
      if requester:
            if requester.get("email"):
               payload["email"] = requester.get("email")
            if requester.get("name"):
               payload["name"] = requester.get("name")

      # Create SSL context that allows insecure connections for testing
      ssl_context = ssl.create_default_context()
      ssl_context.check_hostname = False
      ssl_context.verify_mode = ssl.CERT_NONE
      
      connector = aiohttp.TCPConnector(ssl=ssl_context)
      
      async with aiohttp.ClientSession(connector=connector) as session:
            async with session.post(url, headers=self.headers, json=payload) as resp:
               data = await resp.json()
               if resp.status not in (200, 201):
                  raise RuntimeError(f"Freshdesk API error {resp.status}: {data}")
               ticket = {
                  "id": data.get("id"),
                  "status": data.get("status"),
                  "priority": data.get("priority"),
                  "url": f"https://{self.domain}/helpdesk/tickets/{data.get('id')}"
               }
               return {"success": True, "ticket": ticket, "raw": data}

   async def health_check(self):
      """Check Freshdesk connectivity by fetching sample endpoint (accounts may not allow GETs; this is best-effort)."""
      try:
            url = f"{self.base_url}/agents"
            # Create SSL context that allows insecure connections for testing
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            
            connector = aiohttp.TCPConnector(ssl=ssl_context)
            
            async with aiohttp.ClientSession(connector=connector) as session:
               async with session.get(url, headers=self.headers) as resp:
                  return {"status": "healthy" if resp.status in (200, 403) else "unhealthy", "status_code": resp.status}
      except Exception as e:
            return {"status": "error", "error": str(e)}