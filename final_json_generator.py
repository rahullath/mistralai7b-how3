import pandas as pd
import requests
import json
import uuid
import os
import time
import re
import logging
from datetime import datetime
import google.generativeai as genai
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration
CMC_API_KEY = os.getenv("CMC_API_KEY")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
GEMINI_MODEL = "gemini-pro"
PLACEHOLDER_COIN_ID = "00000000-0000-0000-0000-000000000000"
OUTPUT_FILE = "crypto_data.json"

# Symbol mapping for known CoinMarketCap discrepancies
SYMBOL_MAPPING = {
    "aptos": "APT",
    "sonic labs (prev. fantom)": "FTM",
    "sky (formerly makerdao)": "SKY",
    "benqi liquid staked avax": "QI",
    "venus usdt": "VUSDT"
}

# Configure Gemini
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel(GEMINI_MODEL)

# Prompt for Gemini
GEMINI_PROMPT = """
You are creating content for how3.io, a crypto analytics platform for retail investors transitioning from traditional finance. Generate jargon-free, beginner-friendly content for a cryptocurrency project. Use simple language, avoid technical terms, and make it engaging. Below are the project details and the sections to generate.

**Project Details**:
- Name: {name}
- Symbol: {symbol}
- Sector: {sector}
- Description: {description}

**Sections to Generate**:
1. **Value Generation (50-70 words)**:
   - Explain how the project makes money or creates value for its users and token holders.
   - Example: "Aave makes money by taking a small cut of the interest paid by borrowers on its lending platform. This interest is shared with lenders and the Aave team to keep the platform running and reward token holders."

2. **Market Position (70-100 words)**:
   - Highlight what the project is best known for and its main innovation.
   - Example: "Uniswap is famous for letting people trade crypto without a middleman using 'liquidity pools.' Unlike regular exchanges, anyone can swap tokens instantly, making trading open to everyone. Its automated system is a game-changer for decentralized finance."

3. **Project Size (70-100 words)**:
   - Describe the project's importance in the crypto space (e.g., market rank, adoption).
   - Do not include specific stats (these will be added separately).
   - Example: "Aave is a top player in decentralized finance, known for its lending platform. It’s one of the biggest projects by the amount of money it manages, making it a trusted name in crypto."

4. **Real World Impact (70-100 words)**:
   - Explain where the project is used (regions, industries) and its influence.
   - Example: "Aave is popular in places like the US, Europe, and Asia, where people use it to lend and borrow crypto. It’s a leader in decentralized finance, helping people access loans without banks."

5. **Founders (70-100 words)**:
   - Describe who created the project, when, and their background (use generic info if specific details are unavailable).
   - Example: "Aave was started by Stani Kulechov in 2017, first as ETHLend. He’s a tech innovator who saw a need for better crypto lending. The team later grew, and now Aave is run by a community of token holders."

6. **Problem Solving (70-100 words)**:
   - Explain the main problem the project solves and why it matters.
   - Example: "Aave makes crypto useful by letting people earn interest on their coins or borrow without selling them. Unlike old-school loans, Aave’s system is fast and doesn’t need a bank, making it easier for anyone to manage their money."

7. **Strengths (3 strengths, each with a title and 2 sentences)**:
   - List 3 key strengths that make the project appealing to investors.
   - Example:
     - **Top Security**: Aave has never been hacked, which builds trust. Its careful design keeps user money safe.
     - **Lots of Options**: Aave lets users lend or borrow many types of crypto. This variety makes it more useful than other platforms.
     - **New Ideas**: Aave created features like flash loans that others now copy. Its innovation keeps it ahead in crypto.

8. **Weaknesses (3 weaknesses, each with a title and 2 sentences)**:
   - List 3 potential concerns for investors.
   - Example:
     - **Hard to Understand**: Aave’s platform can be tricky for beginners. Terms like ‘collateral’ confuse new users.
     - **Market Risks**: If crypto prices crash, Aave’s loans could face problems. This makes it sensitive to market swings.
     - **Regulation Worries**: Governments might make new rules for crypto lending. This could limit how Aave works in some places.

9. **Whitepaper Summary (100-200 words)**:
   - Summarize the project’s core idea, innovation, token use, and problem solved.
   - Use an analogy to make it relatable.
   - Example: "Aave’s platform is like a digital bank where anyone can lend or borrow crypto without paperwork. Instead of dealing with a bank, users add their crypto to shared pools, and others can borrow from them instantly. The AAVE token lets people vote on how the platform runs and share its profits. Aave’s big idea is ‘flash loans,’ where you can borrow and repay in one go without upfront money. It solves the problem of slow, complicated loans by making everything fast and open to everyone. Think of it like a vending machine for loans – pop in your crypto, get cash, and it’s all automatic and secure."

**Output Format**:
Return a JSON object with the following structure:
```json
{
  "valueGeneration": {"description": "...", "title": "Value Generation", "heading": "How {symbol} Generates Value", "readTime": 3, "dificultyTag": "Beginner friendly"},
  "marketPosition": {"description": "...", "title": "Market Position", "heading": "What is {symbol} Best Known For", "readTime": 3, "dificultyTag": "Beginner friendly"},
  "projectSize": {"description": "...", "title": "Project Size", "heading": "How Significant is {symbol} in the Crypto Space", "readTime": 3, "dificultyTag": "Beginner friendly"},
  "RealWorldImpact": {"description": "...", "title": "Real World Impact", "heading": "Where Does {symbol} Have Influence", "readTime": 3, "dificultyTag": "Beginner friendly"},
  "founders": {"description": "...", "title": "Founders", "heading": "Who Created {symbol}", "readTime": 3, "dificultyTag": "Beginner friendly"},
  "problemSolving": {"description": "...", "title": "Problem Solving", "heading": "What challenges does {symbol} solve?", "readTime": 3, "dificultyTag": "Beginner friendly"},
  "strengths": [
    {"title": "...", "description": "..."},
    ...
  ],
  "weaknesses": [
    {"title": "...", "description": "..."},
    ...
  ],
  "whitepaper": {"summary": "...", "title": "Whitepaper Summary", "lastUpdated": "2024-01-01", "readTime": 5, "dificultyTag": "Intermediate"}
}
```
"""

# Default content for fallback
DEFAULT_HF_CONTENT = {
    "valueGeneration": {"description": "N/A", "title": "Value Generation", "heading": "How {symbol} Generates Value", "readTime": 3, "dificultyTag": "Beginner friendly"},
    "marketPosition": {"description": "N/A", "title": "Market Position", "heading": "What is {symbol} Best Known For", "readTime": 3, "dificultyTag": "Beginner friendly"},
    "projectSize": {"description": "N/A", "title": "Project Size", "heading": "How Significant is {symbol} in the Crypto Space", "readTime": 3, "dificultyTag": "Beginner friendly"},
    "RealWorldImpact": {"description": "N/A", "title": "Real World Impact", "heading": "Where Does {symbol} Have Influence", "readTime": 3, "dificultyTag": "Beginner friendly"},
    "founders": {"description": "N/A", "title": "Founders", "heading": "Who Created {symbol}", "readTime": 3, "dificultyTag": "Beginner friendly"},
    "problemSolving": {"description": "N/A", "title": "Problem Solving", "heading": "What challenges does {symbol} solve?", "readTime": 3, "dificultyTag": "Beginner friendly"},
    "strengths": [],
    "weaknesses": [],
    "whitepaper": {"summary": "N/A", "title": "Whitepaper Summary", "lastUpdated": "2024-01-01", "readTime": 5, "dificultyTag": "Intermediate"}
}

# Function to clean and extract JSON from response
def extract_json_from_response(response):
    try:
        # Remove any leading/trailing whitespace and common markdown markers
        response = response.strip()
        response = re.sub(r'```json\n|```', '', response)

        # Attempt to extract JSON using regex
        json_match = re.search(r'\{[\s\S]*?\}', response, re.DOTALL)
        if json_match:
            json_str = json_match.group(0)
            try:
                # Attempt to parse the JSON string
                return json.loads(json_str)
            except json.JSONDecodeError as e:
                logger.warning(f"Failed to parse JSON: {e}. Attempting to fix and retry.")
                # Attempt to fix common JSON errors
                json_str = re.sub(r',\s*([\]}])', r'\1', json_str)  # Remove trailing commas
                json_str = re.sub(r'\\([\'"])', r'\1', json_str)  # Remove escaping backslashes
                try:
                    return json.loads(json_str)
                except json.JSONDecodeError as e2:
                    logger.error(f"Failed to parse JSON after fix: {e2}")
                    logger.debug(f"Problematic JSON string: {json_str[:500]}...")
                    return None
        else:
            logger.warning("No JSON object found in response.")
            logger.debug(f"Response content: {response[:500]}...")
            return None

    except Exception as e:
        logger.error(f"Unexpected error in JSON extraction: {str(e)}")
        return None

def generate_gemini_content(name, symbol, sector, description):
    # Format the prompt with project details
    prompt = GEMINI_PROMPT.format(
        name=name,
        symbol=symbol.upper(),
        sector=sector,
        description=description
    )

    try:
        # Generate content with Gemini
        response = model.generate_content(prompt)

        # Log the raw response for debugging
        logger.debug(f"Raw response for {name}: {response.text[:200]}...")

        # Extract and parse JSON
        content = extract_json_from_response(response.text)
        if content:
            # Update headings with correct symbol
            for key in ['valueGeneration', 'marketPosition', 'projectSize', 'RealWorldImpact', 'founders', 'problemSolving']:
                if key in content and isinstance(content[key], dict) and 'heading' in content[key]:
                    content[key]['heading'] = content[key]['heading'].format(symbol=symbol.upper())
            return content

        logger.warning(f"Failed to extract valid JSON for {name}, using default content")
        default_content = DEFAULT_HF_CONTENT.copy()
        for key in ['valueGeneration', 'marketPosition', 'projectSize', 'RealWorldImpact', 'founders', 'problemSolving']:
            if isinstance(default_content[key], dict) and 'heading' in default_content[key]:
                default_content[key]['heading'] = default_content[key]['heading'].format(symbol=symbol.upper())
        return default_content

    except Exception as e:
        logger.error(f"Error generating Gemini content for {name}: {str(e)}")
        return DEFAULT_HF_CONTENT.copy()

def main():
    try:
        # Read CSV
        df = pd.read_csv("project_data.csv")
        logger.info(f"Loaded CSV with {len(df)} rows")

        # Load CMC data
        with open("cmcdata.json", "r") as f:
            cmc_data = json.load(f)
        logger.info(f"Loaded CMC data for {len(cmc_data)} projects")

        # Generate JSON
        result = {}
        success_count = 0
        error_count = 0

        for i, row in df.iterrows():
            try:
                symbol = row["Symbol"].lower()
                name = row["Project"]
                sector = row.get("Market Sector", "Unknown")
                description = f"{name} is a decentralized protocol in the {sector} sector, offering innovative solutions for decentralized applications and services."
                project_id = str(uuid.uuid4())
                coin_id = PLACEHOLDER_COIN_ID

                # Get CMC data
                market_data = cmc_data.get(symbol) or {
                    "marketCap": "N/A",
                    "tradingVolume": "N/A",
                    "circulatingSupply": "N/A",
                    "totalSupply": "N/A"
                }

        # Generate content with Gemini
        hf_content = generate_gemini_content(name, symbol, sector, description)

        # Use scores from the CSV with fallback to 0
        ugs = float(row.get("UGS", 0)) if pd.notna(row.get("UGS")) else 0
        eqs = float(row.get("EQS", 0)) if pd.notna(row.get("EQS")) else 0
        fvs = float(row.get("FVS", 0)) if pd.notna(row.get("FVS")) else 0
        ss = float(row.get("SS", 0)) if pd.notna(row.get("SS")) else 0

        # Check if hf_content is the default content
        is_default_content = hf_content == DEFAULT_HF_CONTENT

        # Generate JSON structure
        project = {
            "id": project_id,
            "coinId": coin_id,
            "name": name.lower().replace(" ", "-"),
            "title": f"{name} Analysis for how3.io",
            "logo": f"https://cryptologos.cc/logos/{name.lower().replace(' ', '-')}-{symbol}-logo.svg",
            "description": description,
            "assetOverview": {
                "valueGeneration": hf_content["valueGeneration"] if not is_default_content else DEFAULT_HF_CONTENT["valueGeneration"],
                "marketPosition": hf_content["marketPosition"] if not is_default_content else DEFAULT_HF_CONTENT["marketPosition"],
                "projectSize": {
                    **hf_content["projectSize"] if not is_default_content else DEFAULT_HF_CONTENT["projectSize"],
                    "keyStats": market_data
                },
                "RealWorldImpact": hf_content["RealWorldImpact"] if not is_default_content else DEFAULT_HF_CONTENT["RealWorldImpact"]
            },
            "projectNarrative": {
                "founders": hf_content["founders"] if not is_default_content else DEFAULT_HF_CONTENT["founders"],
                "problemSolving": hf_content["problemSolving"] if not is_default_content else DEFAULT_HF_CONTENT["problemSolving"]
            },
            "researchAnalysis": {
                "strengths": hf_content["strengths"] if not is_default_content else DEFAULT_HF_CONTENT["strengths"],
                "weaknesses": hf_content["weaknesses"] if not is_default_content else DEFAULT_HF_CONTENT["weaknesses"]
            },
            "benchmarkScores": {
                "growth": ugs,
                "earning": eqs,
                "fairValue": fvs,
                "safety": ss,
                "barData": [
                    {"label": "Growth", "value": ugs, "color": "#4CAF50"},
                    {"label": "Earning", "value": eqs, "color": "#2196F3"},
                    {"label": "Fair Value", "value": fvs, "color": "#FFC107"},
                    {"label": "Safety", "value": ss, "color": "#9C27B0"}
                ]
            },
            "whitepaper": hf_content["whitepaper"] if not is_default_content else DEFAULT_HF_CONTENT["whitepaper"],
            "marketBenchmarkScores": {
                "description": f"These scores compare {name}'s growth, revenue generation, valuation, and financial health to the overall cryptocurrency market. Higher scores indicate better performance and show {name}'s percentile in these areas. Compare scores across different cryptocurrencies to identify more attractive investments!"
            }
        }
        result[symbol] = project

        logger.info(f"Processed {i+1}/{len(df)} - {symbol}")
        success_count += 1

            except Exception as e:
                logger.error(f"Error processing row {i} ({row.get('Project', 'Unknown')}): {str(e)}")
                error_count += 1
                continue

        # Save final output
        with open(OUTPUT_FILE, "w") as f:
            json.dump(result, f, indent=4)

        logger.info(f"Successfully generated data for {success_count} cryptocurrencies")
        logger.info(f"Failed to process {error_count} cryptocurrencies")

    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")

if __name__ == "__main__":
    main()
