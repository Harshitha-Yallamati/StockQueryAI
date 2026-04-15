import json
import asyncio
from openai import OpenAI
import tools as inventory_tools
import rag

# Configure the standard OpenAI SDK to point to your local Ollama instance.
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama',
)

OLLAMA_MODEL = "qwen2.5:1.5b"

TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "query_inventory_db",
            "description": "Get the stock quantity of a specific product by its name.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "The name of the product"
                    }
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_product_details",
            "description": "Get the complete details of a specific product including price, quantity, and category.",
            "parameters": {
                "type": "object",
                "properties": {
                    "product_name": {
                        "type": "string",
                        "description": "The name of the product"
                    }
                },
                "required": ["product_name"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_low_stock_products",
            "description": "Get a list of products that have a stock quantity below a certain threshold.",
            "parameters": {
                "type": "object",
                "properties": {
                    "threshold": {
                        "type": "integer",
                        "description": "The inventory threshold number to check against."
                    }
                },
                "required": ["threshold"]
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "get_total_inventory_value",
            "description": "Calculate and return the total monetary value of all items in the inventory.",
            "parameters": {
                "type": "object",
                "properties": {},
                "required": []
            }
        }
    },
    {
        "type": "function",
        "function": {
            "name": "search_knowledge_base",
            "description": "Perform a semantic vector search on unstructured company knowledge, manuals, or policies.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The search phrase to retrieve context for."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

async def stream_agent(user_message: str, message_history: list = None):
    """
    Executes the conversational agent loop with async streaming support.
    """
    if message_history is None:
        message_history = []

    # --- Short-Circuit Logic (Performance Boost) ---
    query_lower = user_message.lower()
    short_circuit_keywords = ["stock", "price", "how many", "quantity", "inventory"]
    
    if any(k in query_lower for k in short_circuit_keywords):
        # We try to use the raw query as the product name for a fast lookup
        # This works well if the user just asks "Laptops stock" or similar.
        # We'll use a simplified regex-less extraction or just the last few words.
        cleaned_query = query_lower.replace("stock", "").replace("price", "").replace("how many", "").replace("quantity", "").strip()
        if cleaned_query:
            result = inventory_tools.get_product_details(cleaned_query)
            if "error" not in result:
                yield json.dumps({"type": "thought", "content": "Instant lookup triggered ⚡"}) + "\n"
                response = f"I found **{result['name']}** in the database. Its current price is ${result['price']} and there are **{result['quantity']}** units in stock."
                yield json.dumps({"type": "content", "content": response}) + "\n"
                return

    messages = [
        {"role": "system", "content": "You are an intelligent inventory assistant. Answer queries using the database tools provided. Be concise and helpful."}
    ]
    messages.extend(message_history)
    messages.append({"role": "user", "content": user_message})

    yield json.dumps({"type": "thought", "content": f"Processing with {OLLAMA_MODEL}..."}) + "\n"

    # First LLM call
    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=0.0
        )
    except Exception as e:
        yield json.dumps({"type": "content", "content": f"Error connecting to Ollama: {str(e)}"}) + "\n"
        return

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    if tool_calls:
        messages.append(response_message)
        
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            yield json.dumps({"type": "tool", "name": function_name, "args": function_args}) + "\n"
            
            # Map tool to local module
            if hasattr(inventory_tools, function_name):
                function_to_call = getattr(inventory_tools, function_name)
                # Ensure it's not a blocking call if it was async, 
                # but these are standard sync DB calls.
                function_response = function_to_call(**function_args)
            elif hasattr(rag, function_name):
                function_to_call = getattr(rag, function_name)
                function_response = function_to_call(**function_args)
            else:
                function_response = {"error": f"Tool '{function_name}' not found."}
                
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(function_response),
            })
            
        # Second LLM call: Streaming response
        try:
            second_response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                temperature=0.2,
                stream=True
            )
            for chunk in second_response:
                if chunk.choices[0].delta.content:
                    yield json.dumps({"type": "content", "content": chunk.choices[0].delta.content}) + "\n"
        except Exception as e:
            yield json.dumps({"type": "content", "content": f"Error streaming response: {str(e)}"}) + "\n"
            
    else:
        # direct content without tool calls
        yield json.dumps({"type": "content", "content": response_message.content}) + "\n"

