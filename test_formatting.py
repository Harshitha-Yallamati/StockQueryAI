"""Test script to verify enhanced response formatting"""
import requests
import json

BASE_URL = "http://localhost:8081"

def test_formatting():
    """Test different formatting options"""
    
    test_cases = [
        "Show all products in a table",
        "Give me a summary of all products", 
        "List all products with bullets",
        "Compare the first two products",
        "Show all products in sentences",
    ]
    
    for query in test_cases:
        print(f"\n{'='*60}")
        print(f"Testing: {query}")
        print('='*60)
        
        try:
            response = requests.post(
                f"{BASE_URL}/ask",
                json={"question": query, "session_id": "test_session"}
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"Response: {result.get('answer', 'No answer')}")
            else:
                print(f"Error: {response.status_code} - {response.text}")
        except Exception as e:
            print(f"Exception: {e}")

if __name__ == "__main__":
    test_formatting()
