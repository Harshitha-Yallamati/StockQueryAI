import json
from openai import OpenAI
import tools as inventory_tools
import rag

# Configure the standard OpenAI SDK to point to your local Ollama instance.
# Note: For tool calling to work perfectly, you need an Ollama model that supports it,
# like "llama3.1", "llama3.2", "qwen2.5", or "mistral". We default to "llama3.1".
client = OpenAI(
    base_url='http://localhost:11434/v1',
    api_key='ollama',  # required by the SDK but not verified by Ollama
)

OLLAMA_MODEL = "llama3.1"

# Define the JSON schemas for the tools we want to make available to the LLM.
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
                        "description": "The name of the product, e.g., 'Laptops' or 'Wireless Mice'"
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
            "description": "Perform a semantic vector search on unstructured company knowledge, manuals, policies, or detailed textual descriptions of products.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "The exact natural language search phrase you want to embed and retrieve context for."
                    }
                },
                "required": ["query"]
            }
        }
    }
]

def run_agent(user_message: str, message_history: list = None) -> str:
    """
    Executes the conversational agent loop.
    1. Sends the user's message and tools to the LLM.
    2. Checks if the LLM decided to call a tool.
    3. Executes the local Python tool.
    4. Submits the tool result back to the LLM for a final natural language answer.
    """
    if message_history is None:
        message_history = []
        
    messages = [
        {"role": "system", "content": "You are an intelligent inventory assistant. Answer queries using the database tools provided. If a tool returns an error, explain it gracefully to the user."}
    ]
    messages.extend(message_history)
    messages.append({"role": "user", "content": user_message})

    # First LLM call
    try:
        response = client.chat.completions.create(
            model=OLLAMA_MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,
            temperature=0.0
        )
    except Exception as e:
        return f"Error connecting to Ollama: {str(e)}. Please make sure Ollama is running (`ollama run {OLLAMA_MODEL}`)."

    response_message = response.choices[0].message
    tool_calls = response_message.tool_calls

    # Check if the LLM wants to call a function
    if tool_calls:
        messages.append(response_message)
        
        # We handle multiple tool calls if the model requests them in sequence
        for tool_call in tool_calls:
            function_name = tool_call.function.name
            function_args = json.loads(tool_call.function.arguments)
            
            # Map the LLM's requested function to our local Python module
            if hasattr(inventory_tools, function_name):
                function_to_call = getattr(inventory_tools, function_name)
                function_response = function_to_call(**function_args)
            elif hasattr(rag, function_name):
                function_to_call = getattr(rag, function_name)
                function_response = function_to_call(**function_args)
            else:
                function_response = {"error": f"Tool '{function_name}' not found in any internal systems."}
                
            # Append the result of the tool to the conversation history
            messages.append({
                "tool_call_id": tool_call.id,
                "role": "tool",
                "name": function_name,
                "content": json.dumps(function_response),
            })
            
        # Second LLM call: LLM sees the tool output and drafts a final response
        try:
            second_response = client.chat.completions.create(
                model=OLLAMA_MODEL,
                messages=messages,
                temperature=0.2
            )
            return second_response.choices[0].message.content
        except Exception as e:
            return f"Error parsing tool output with Ollama: {str(e)}"
            
    # If no tool was called, return the direct LLM response
    return response_message.content
