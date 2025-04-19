import pandas as pd
import requests
import json
import os
import time
import re
import logging
import traceback
import copy
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(
    level=logging.INFO, 
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler("content_generator.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CMC_DATA_FILE = "cmcdata.json"
GEMINI_MODEL = "gemini-2.0-flash"
OUTPUT_DIR = "project_content"
PLACEHOLDER_PROJECT_ID = "placeholder-project-id"
PLACEHOLDER_COIN_ID = "placeholder-coin-id"

# Create output directory if it doesn't exist
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# Prompt for Gemini - Using plain text format to avoid JSON parsing issues
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
   Format each as: **Title**: Description.

8. **Weaknesses**:
   List 3 potential concerns, each with a title and 2 sentences of description.
   Format each as: **Title**: Description.

9. **Whitepaper Summary (100-200 words)**:
   Summarize the project's core idea, innovation, token use, and problem solved.

FORMAT YOUR RESPONSE WITH CLEAR SECTION HEADERS.
"""

# Default structure for fallback
DEFAULT_CONTENT = {
    "valueGeneration": {
        "description": "This project generates value by providing a valuable service in the cryptocurrency ecosystem. Users benefit from its utility while token holders receive a portion of the fees generated.",
        "title": "Value Generation", 
        "heading": "How {symbol} Generates Value", 
        "readTime": 3, 
        "dificultyTag": "Beginner friendly"
    },
    "marketPosition": {
        "description": "The project is known for innovation in its sector. It addresses key challenges and offers unique solutions that differentiate it from competitors in the blockchain space.",
        "title": "Market Position", 
        "heading": "What is {symbol} Best Known For", 
        "readTime": 3, 
        "dificultyTag": "Beginner friendly"
    },
    "projectSize": {
        "description": "This project has established itself as a notable player in the cryptocurrency ecosystem. It has gained recognition for its technology and utility.",
        "title": "Project Size", 
        "heading": "How Significant is {symbol} in the Crypto Space", 
        "readTime": 3, 
        "dificultyTag": "Beginner friendly"
    },
    "RealWorldImpact": {
        "description": "The project has applications across various geographic regions and industries. It provides solutions to real-world problems and has influenced the broader blockchain ecosystem.",
        "title": "Real World Impact", 
        "heading": "Where Does {symbol} Have Influence", 
        "readTime": 3, 
        "dificultyTag": "Beginner friendly"
    },
    "founders": {
        "description": "The project was created by a team of blockchain experts with backgrounds in technology and finance. They launched the project with a vision to address key challenges in the sector.",
        "title": "Founders", 
        "heading": "Who Created {symbol}", 
        "readTime": 3, 
        "dificultyTag": "Beginner friendly"
    },
    "problemSolving": {
        "description": "This project solves fundamental challenges in the blockchain space by providing innovative solutions. Its approach addresses inefficiencies and creates new opportunities for users.",
        "title": "Problem Solving", 
        "heading": "What challenges does {symbol} solve?", 
        "readTime": 3, 
        "dificultyTag": "Beginner friendly"
    },
    "strengths": [
        {"title": "Technical Innovation", "description": "The project utilizes cutting-edge technology to deliver its services. This technical foundation provides a competitive advantage in the market."},
        {"title": "Strong Community", "description": "The project has built a dedicated user base that supports its development. This community engagement helps drive adoption and improvement."},
        {"title": "Practical Utility", "description": "The project offers real-world applications that solve tangible problems. This utility creates sustainable demand for its services."}
    ],
    "weaknesses": [
        {"title": "Market Competition", "description": "The project faces competition from established players in the space. This competitive landscape could impact its growth potential."},
        {"title": "Technical Complexity", "description": "Some aspects of the project may be difficult for beginners to understand. This complexity could limit mainstream adoption."},
        {"title": "Regulatory Considerations", "description": "The project operates in an evolving regulatory environment. Changes in regulations could affect its operations in certain regions."}
    ],
    "whitepaper": {
        "summary": "The project provides a blockchain-based solution that addresses key challenges in its sector. It utilizes innovative technology to create value for users and token holders while maintaining security and efficiency.",
        "lastUpdated": datetime.now().strftime("%Y-%m-%d"),
        "readTime": 5,
        "dificultyTag": "Intermediate"
    }
}

def load_cmc_data():
    """Load market data from CMC data file."""
    try:
        with open(CMC_DATA_FILE, 'r') as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading CMC data: {str(e)}")
        return {}

def extract_section(text, section_name, next_section=None):
    """Extract content between section_name and next_section (or end of text)."""
    # Create regex pattern for section headers
    pattern = rf"(?:{section_name}|{section_name.upper()}).*?:(.*?)"
    
    # If next_section is provided, look for that, otherwise match until the end
    if next_section:
        pattern += rf"(?:{next_section}|{next_section.upper()})"
    else:
        pattern += r"$"
    
    # Search for the pattern
    match = re.search(pattern, text, re.DOTALL | re.IGNORECASE)
    
    if match:
        return match.group(1).strip()
    return None

def extract_strengths_weaknesses(text, section_name):
    """Extract strengths or weaknesses as a list of dictionaries."""
    result = []
    default_items = []
    
    # Set default items based on section name
    if section_name.lower() == "strengths":
        default_items = [
            {"title": "Strong Ecosystem Integration", "description": "The project effectively integrates with other blockchain protocols. This connectivity enhances its utility and user experience."},
            {"title": "Active Development", "description": "The project maintains an active development roadmap with regular updates. This ongoing development helps keep the technology relevant."},
            {"title": "User-Focused Design", "description": "The platform is designed with user experience as a priority. This user-centric approach helps drive adoption and retention."}
        ]
    else:  # weaknesses
        default_items = [
            {"title": "Market Competition", "description": "The project faces competition from other protocols in the same space. This competitive environment could limit growth potential."},
            {"title": "Technical Complexity", "description": "Some aspects of the system may be difficult for new users to understand. This learning curve could slow mainstream adoption."},
            {"title": "Regulatory Uncertainty", "description": "Like many blockchain projects, it operates in an evolving regulatory landscape. Future regulatory changes could impact operations."}
        ]
    
    # Extract the section first
    section_content = extract_section(text, section_name)
    if not section_content:
        logger.warning(f"Could not find {section_name} section, using defaults")
        return default_items
    
    # Try multiple patterns to extract items
    patterns = [
        # Format: **Title**: Description
        r'(?:\*\*([^:]*?)\*\*:?\s*(.*?)(?=\n\s*\*\*|$))',
        # Format: 1. **Title**: Description or 1. Title: Description
        r'(?:\d+\.\s*(?:\*\*)?([^:]*?)(?:\*\*)?:?\s*(.*?)(?=\n\s*\d+\.|$))',
        # Format: - **Title**: Description or - Title: Description
        r'(?:-\s*(?:\*\*)?([^:]*?)(?:\*\*)?:?\s*(.*?)(?=\n\s*-\s*|$))'
    ]
    
    # Try each pattern until we find matches
    items = []
    for pattern in patterns:
        items = re.findall(pattern, section_content, re.DOTALL)
        if items:
            break
    
    # Process matched items
    for title, desc in items:
        title = re.sub(r'\*\*', '', title).strip()
        desc = desc.strip()
        
        if title and desc:  # Only add if both are non-empty
            result.append({
                "title": title,
                "description": desc
            })
    
    # If we didn't get enough items, try paragraph-based extraction
    if len(result) < 3:
        paragraphs = re.split(r'\n\s*\n', section_content)
        for para in paragraphs:
            if len(result) >= 3:
                break
                
            # Skip if this paragraph is already captured
            if any(item["description"] in para for item in result):
                continue
                
            # Try to split into title and description
            parts = para.split(':', 1)
            if len(parts) == 2:
                title = parts[0].strip().replace('*', '')
                desc = parts[1].strip()
            else:
                # If no colon, use first sentence as title, rest as description
                sentences = re.split(r'(?<=[.!?])\s+', para)
                if len(sentences) > 1:
                    title = sentences[0].strip()
                    desc = ' '.join(sentences[1:]).strip()
                else:
                    # If only one sentence, use first few words as title
                    words = para.split()
                    if len(words) > 4:
                        title = ' '.join(words[:3])
                        desc = ' '.join(words[3:])
                    else:
                        continue  # Skip if too short
            
            title = re.sub(r'\*\*', '', title).strip()
            desc = desc.strip()
            
            if title and desc and not any(item["title"] == title for item in result):
                result.append({
                    "title": title,
                    "description": desc
                })
    
    # If we still don't have enough items, add defaults to make up 3
    while len(result) < 3 and default_items:
        result.append(default_items.pop(0))
    
    return result[:3]  # Limit to exactly 3 items

def parse_text_to_sections(text, symbol):
    """Parse the raw text content into structured sections."""
    # Define section names and their corresponding next sections
    sections = [
        ("Value Generation", "Market Position"),
        ("Market Position", "Project Size"),
        ("Project Size", "Real World Impact"),
        ("Real World Impact", "Founders"),
        ("Founders", "Problem Solving"),
        ("Problem Solving", "Strengths"),
        ("Strengths", "Weaknesses"),
        ("Weaknesses", "Whitepaper Summary"),
        ("Whitepaper Summary", None)  # Last section
    ]
    
    # Initialize result structure
    result = copy.deepcopy(DEFAULT_CONTENT)
    
    # Format all headings with the correct symbol
    for key in result:
        if isinstance(result[key], dict) and 'heading' in result[key]:
            result[key]['heading'] = result[key]['heading'].format(symbol=symbol.upper())
    
    # Extract text content for each section
    for section_name, next_section in sections:
        content = extract_section(text, section_name, next_section)
        
        if content:
            # Map section names to keys in result structure
            if section_name == "Value Generation":
                result["valueGeneration"]["description"] = content
            elif section_name == "Market Position":
                result["marketPosition"]["description"] = content
            elif section_name == "Project Size":
                result["projectSize"]["description"] = content
            elif section_name == "Real World Impact":
                result["RealWorldImpact"]["description"] = content
            elif section_name == "Founders":
                result["founders"]["description"] = content
            elif section_name == "Problem Solving":
                result["problemSolving"]["description"] = content
            elif section_name == "Whitepaper Summary":
                result["whitepaper"]["summary"] = content
    
    # Extract strengths and weaknesses
    result["strengths"] = extract_strengths_weaknesses(text, "Strengths")
    result["weaknesses"] = extract_strengths_weaknesses(text, "Weaknesses")
    
    return result

def generate_gemini_content(name, symbol, sector, description):
    """Generate content using Gemini API."""
    try:
        # Format the prompt with project details
        formatted_prompt = GEMINI_PROMPT.format(
            name=name,
            symbol=symbol.upper(),
            sector=sector,
            description=description
        )
        
        # Generate text with conservative settings - Fixed API call format
        response = model.generate_content(
            contents=formatted_prompt,  # Changed from 'prompt' to 'contents'
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
        
        return content
    except Exception as e:
        logger.error(f"Error generating content for {name}: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")
        return None

def create_project_json(content, symbol, name, cmc_data=None, scores=None):
    """Create the complete project JSON structure."""
    # Use provided scores or defaults
    growth_score = scores.get("growth", 50) if scores else 50
    earning_score = scores.get("earning", 50) if scores else 50
    fair_value_score = scores.get("fairValue", 50) if scores else 50
    safety_score = scores.get("safety", 50) if scores else 50
    
    # Get market data
    market_data = cmc_data.get(symbol, {}) if cmc_data else {}
    
    # Create a description
    description = f"{name} is a cryptocurrency project in the {content.get('marketPosition', {}).get('description', 'blockchain')[:50]}..."
    
    # Build the project JSON
    project = {
        "id": PLACEHOLDER_PROJECT_ID,
        "coinId": PLACEHOLDER_COIN_ID,
        "name": name,
        "title": f"{name} Analysis for how3.io",
        "logo": f"https://cryptologos.cc/logos/{name.lower().replace(' ', '-')}-{symbol}-logo.svg",
        "description": description,
        "assetOverview": {
            "valueGeneration": content["valueGeneration"],
            "marketPosition": content["marketPosition"],
            "projectSize": {
                **content["projectSize"],
                "keyStats": market_data
            },
            "RealWorldImpact": content["RealWorldImpact"]
        },
        "projectNarrative": {
            "founders": content["founders"],
            "problemSolving": content["problemSolving"]
        },
        "researchAnalysis": {
            "strengths": content["strengths"],
            "weaknesses": content["weaknesses"]
        },
        "benchmarkScores": {
            "growth": growth_score,
            "earning": earning_score,
            "fairValue": fair_value_score,
            "safety": safety_score,
            "barData": [
                {"label": "User Growth", "value": growth_score, "color": "#4CAF50"},
                {"label": "Earnings Quality", "value": earning_score, "color": "#2196F3"},
                {"label": "Fair Value", "value": fair_value_score, "color": "#FFC107"},
                {"label": "Safety Score", "value": safety_score, "color": "#9C27B0"}
            ]
        },
        "whitepaper": content["whitepaper"],
        "marketBenchmarkScores": {
            "description": f"These scores compare {name}'s growth, revenue generation, valuation, and financial health to the overall cryptocurrency market. Higher scores indicate better performance and show {name}'s percentile in these areas. Compare scores across different cryptocurrencies to identify more attractive investments!"
        }
    }
    
    return project

def format_cvx_example():
    """Create a formatted example JSON for Convex Finance."""
    try:
        # Load the sample CVX data from paste.txt if it exists
        cvx_data = None
        try:
            with open("paste.txt", 'r', encoding='utf-8') as f:
                cvx_data = json.load(f)
        except:
            logger.warning("Could not load sample CVX data from paste.txt")
        
        if cvx_data and "cvx" in cvx_data:
            # Extract and print for reference
            logger.info("Sample CVX data structure loaded successfully")
            return cvx_data["cvx"]
        else:
            logger.warning("Sample CVX data not found or invalid structure")
            return None
    except Exception as e:
        logger.error(f"Error formatting CVX example: {str(e)}")
        return None

def main():
    try:
        # Load CMC data
        cmc_data = load_cmc_data()
        logger.info(f"Loaded CMC data with {len(cmc_data)} entries")
        
        # Read CSV with project data
        df = pd.read_csv("how3.io score sheet - Score Sheet (Master).csv")
        logger.info(f"Loaded CSV with {len(df)} rows")
        
        # Create a dictionary of scores
        scores_data = {}
        for _, row in df.iterrows():
            try:
                # Handle numeric symbols by converting to string
                if pd.isna(row.get("Symbol")):
                    continue  # Skip rows with missing symbols
                
                # Convert any numeric symbols to strings
                symbol_val = row["Symbol"]
                if isinstance(symbol_val, (int, float)):
                    symbol = str(int(symbol_val)).lower()
                else:
                    symbol = str(symbol_val).lower()
                
                scores_data[symbol] = {
                    "growth": float(row.get("UGS", 50)) if not pd.isna(row.get("UGS")) else 50,
                    "earning": float(row.get("EQS", 50)) if not pd.isna(row.get("EQS")) else 50,
                    "fairValue": float(row.get("FVS", 50)) if not pd.isna(row.get("FVS")) else 50,
                    "safety": float(row.get("SS", 50)) if not pd.isna(row.get("SS")) else 50
                }
            except Exception as e:
                logger.warning(f"Error processing scores for row with Symbol={row.get('Symbol')}: {str(e)}")
                continue
        
        # Filter the DataFrame to only include rows with valid symbols
        filtered_df = df.dropna(subset=["Symbol"])
        logger.info(f"Filtered to {len(filtered_df)} rows with valid symbols")
        
        # Process all projects
        all_projects = {}
        success_count = 0
        error_count = 0
        
        # For debugging/testing, limit to a smaller set
        # filtered_df = filtered_df.head(5)  # Comment this out for full processing
        logger.info(f"Testing with first 5 projects")
        
        for i, row in filtered_df.iterrows():
            try:
                # Extract project details
                name = row["Project"]
                
                # Handle numeric symbols by converting to string
                symbol_val = row["Symbol"]
                if isinstance(symbol_val, (int, float)):
                    symbol = str(int(symbol_val)).lower()
                else:
                    symbol = str(symbol_val).lower()
                
                sector = str(row.get("Market Sector", "Cryptocurrency"))
                description = f"{name} is a decentralized protocol in the {sector} sector."
                
                logger.info(f"Processing project {i+1}/{len(filtered_df)}: {name} ({symbol})")
                
                # 1. Generate content with Gemini
                raw_content = generate_gemini_content(name, symbol, sector, description)
                
                # 2. Save the raw content for reference
                raw_file = os.path.join(OUTPUT_DIR, f"{symbol}_raw.txt")
                with open(raw_file, "w", encoding="utf-8") as f:
                    f.write(raw_content if raw_content else "Error generating content")
                
                # 3. Parse the content into structured sections
                if raw_content:
                    structured_content = parse_text_to_sections(raw_content, symbol)
                    
                    # 4. Create full project JSON
                    project_json = create_project_json(
                        structured_content,
                        symbol,
                        name,
                        cmc_data,
                        scores_data.get(symbol)
                    )
                    
                    # 5. Save individual project JSON
                    json_file = os.path.join(OUTPUT_DIR, f"{symbol}.json")
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(project_json, f, indent=2)
                    
                    # 6. Add to combined data
                    all_projects[symbol] = project_json
                    
                    logger.info(f"Successfully processed {name}")
                    success_count += 1
                else:
                    # If content generation failed, use default structure
                    logger.warning(f"Using default content for {name}")
                    default_content = copy.deepcopy(DEFAULT_CONTENT)
                    
                    # Format headings with symbol
                    for key in default_content:
                        if isinstance(default_content[key], dict) and 'heading' in default_content[key]:
                            default_content[key]['heading'] = default_content[key]['heading'].format(symbol=symbol.upper())
                    
                    # Create and save project JSON with default content
                    project_json = create_project_json(
                        default_content,
                        symbol,
                        name,
                        cmc_data,
                        scores_data.get(symbol)
                    )
                    
                    json_file = os.path.join(OUTPUT_DIR, f"{symbol}.json")
                    with open(json_file, "w", encoding="utf-8") as f:
                        json.dump(project_json, f, indent=2)
                    
                    all_projects[symbol] = project_json
                    logger.warning(f"Saved default content for {name}")
                    error_count += 1
                
                # Save the combined data periodically
                if (i + 1) % 5 == 0 or i == len(filtered_df) - 1:
                    with open(os.path.join(OUTPUT_DIR, "all_projects.json"), "w", encoding="utf-8") as f:
                        json.dump({"projects": all_projects}, f, indent=2)
                    logger.info(f"Saved combined data with {len(all_projects)} projects")
                
                # Add delay to avoid rate limits
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error processing {row.get('Project', 'Unknown')}: {str(e)}")
                logger.error(f"Exception traceback: {traceback.format_exc()}")
                error_count += 1
                continue
        
        # Final statistics
        logger.info(f"Processing complete: {success_count} successes, {error_count} errors")
        logger.info(f"Results saved to {OUTPUT_DIR} directory")
    
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        logger.error(f"Exception traceback: {traceback.format_exc()}")

if __name__ == "__main__":
    import re  # Import here to avoid issues
    
    # Check for '--example' flag
    import sys
    if len(sys.argv) > 1 and sys.argv[1] == '--example':
        # Just format the CVX example
        cvx_example = format_cvx_example()
        if cvx_example:
            with open(os.path.join(OUTPUT_DIR, "cvx_example.json"), "w", encoding="utf-8") as f:
                json.dump(cvx_example, f, indent=2)
            logger.info("Saved CVX example to cvx_example.json")
    else:
        # Run the normal content generation
        main()