import google.generativeai as genai
from dotenv import load_dotenv
import os
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configure Gemini
api_key = os.getenv("GEMINI_API_KEY")
genai.configure(api_key=api_key)

def main():
    try:
        # List available models
        print("Listing available models...")
        for m in genai.list_models():
            print(f"Model Name: {m.name}")
            print(f"  Display Name: {m.display_name}")
            print(f"  Description: {m.description}")
            print(f"  Supported Generation Methods: {m.supported_generation_methods}")
            print()

        # Get specific model details
        model_name = None
        for m in genai.list_models():
            if 'generateContent' in m.supported_generation_methods and 'gemini' in m.name.lower():
                model_name = m.name
                print(f"Found suitable model: {model_name}")
                print(f"This model supports generateContent and has 'gemini' in its name.")
                break
        
        if not model_name:
            print("Could not find a suitable Gemini model that supports generateContent.")
            return
        
        # Test the found model
        model = genai.GenerativeModel(model_name)
        
        # Try a simple generation
        response = model.generate_content("Say hello")
        print("\nTest response:", response.text)
        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    main()