import pandas as pd
import requests
import json
import os
import time
import logging
import traceback
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
GEMINI_MODEL = "gemini-pro"
OUTPUT_DIR = "generated_content"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# Prompt for Gemini - Simplified to avoid JSON formatting issues
GEMINI_PROMPT = """
You are creating content for how3.io, a crypto analytics platform for retail investors transitioning from traditional finance. Generate jargon-free, beginner-friendly content for a cryptocurrency project. Use simple language, avoid technical terms, and make it engaging.

**Project Details**:
- Name: {name}
- Symbol: {symbol}
- Sector: {sector}
- Description: {description}

For each section below, provide concise and informative content:

1. **Value Generation (50-70 words)**:
   Explain how the project makes money or creates value for its users and token holders.

2. **Market Position (70-100 words)**:
   Highlight what the project is best known for and its main innovation.

3. **Project Size (70-100 words)**:
   Describe the project's importance in the crypto space (e.g., market rank, adoption).

4. **Real World Impact (70-100 words)**:
   Explain where the project is used (regions, industries) and its influence.

5. **Founders (70-100 words)**:
   Describe who created the project, when, and their background.

6. **Problem Solving (70-100 words)**:
   Explain the main problem the project solves and why it matters.

7. **Strengths**:
   List 3 key strengths, each with a title and 2 sentences of description.

8. **Weaknesses**:
   List 3 potential concerns, each with a title and 2 sentences of description.

9. **Whitepaper Summary (100-200 words)**:
   Summarize the project's core idea, innovation, token use, and problem solved.

FORMAT YOUR RESPONSE WITH CLEAR SECTION HEADERS.
"""

def generate_gemini_content(name, symbol, sector, description):
    try:
        # Format the prompt with project details
        prompt = GEMINI_PROMPT.format(
            name=name,
            symbol=symbol.upper(),
            sector=sector,
            description=description
        )
        
        # Generate text with conservative settings
        response = model.generate_content(
            prompt=prompt,
            generation_config=genai.GenerationConfig(
                temperature=0.2,
                top_p=0.95,
                top_k=40,
                max_output_tokens=4000
            ),
        )
        
        # Get the raw text content
        content = response.text
        
        # Log a snippet of the response
        logger.info(f"Generated content for {name} (first 100 chars): {content[:100]}...")
        
        # Return the plain text content
        return content
    except Exception as e:
        logger.error(f"Error generating content for {name}: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        return None

def parse_text_to_sections(text):
    """Parse the text content into sections. This is a simple version that can be expanded."""
    sections = {}
    
    # Find Value Generation section
    value_gen_match = re.search(r'(?:Value Generation|VALUE GENERATION).*?:(.*?)(?:Market Position|MARKET POSITION)', text, re.DOTALL | re.IGNORECASE)
    if value_gen_match:
        sections['valueGeneration'] = {
            "description": value_gen_match.group(1).strip(),
            "title": "Value Generation",
            "heading": "How Project Generates Value",
            "readTime": 3,
            "dificultyTag": "Beginner friendly"
        }
    
    # Add more section parsing as needed...
    # This is a simplified example - expand for all sections
    
    return sections

def main():
    try:
        # Read CSV
        df = pd.read_csv("project_data.csv")
        logger.info(f"Loaded CSV with {len(df)} rows")
        
        # For testing, just use a couple of rows
        test_df = df.head(2)  # Just process the first 2 rows for testing
        logger.info(f"Processing {len(test_df)} projects for testing")
        
        success_count = 0
        error_count = 0
        
        for i, row in test_df.iterrows():
            try:
                name = row["Project"]
                symbol = row["Symbol"].lower()
                sector = row.get("Market Sector", "Unknown")
                description = f"{name} is a decentralized protocol in the {sector} sector."
                
                # Generate plain text content
                content = generate_gemini_content(name, symbol, sector, description)
                
                if content:
                    # Save the raw text content for manual verification
                    output_file = os.path.join(OUTPUT_DIR, f"{symbol}_raw_content.txt")
                    with open(output_file, "w", encoding="utf-8") as f:
                        f.write(content)
                    
                    logger.info(f"Saved raw content for {name} to {output_file}")
                    success_count += 1
                else:
                    logger.warning(f"No content generated for {name}")
                    error_count += 1
                
                # Delay to avoid rate limits
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error processing {row.get('Project', 'Unknown')}: {str(e)}")
                error_count += 1
                continue
        
        logger.info(f"Successfully generated content for {success_count} projects")
        logger.info(f"Failed to process {error_count} projects")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import re  # Import here to avoid issues
    main()