import pandas as pd
import requests
import os
import time
import logging
from datetime import datetime
from huggingface_hub import InferenceClient
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Configuration
CMC_API_KEY = os.getenv("CMC_API_KEY")
HF_API_KEY = os.getenv("HF_API_KEY")
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
HF_MODEL = "meta-llama/Llama-3.2-3B-Instruct"  # Smaller model, 4.7GB
OUTPUT_DIR = "project_content"

# Symbol mapping for CoinMarketCap
SYMBOL_MAPPING = {
    "aptos": "APT",
    "sonic labs (prev. fantom)": "FTM",
    "sky (formerly makerdao)": "SKY",
    "benqi liquid staked avax": "QI",
    "venus usdt": "VUSDT"
}

# List of projects to process (exactly 44)
PROJECTS = [
    "Convex Finance", "Algorand", "Aptos", "Avalanche", "BNB Chain", "Celo", "Cosmos",
    "Ethereum", "Filecoin", "Injective", "Internet Computer", "MultiversX", "NEAR Protocol",
    "Polkadot", "RedStone", "Ronin Network", "Solana", "Sonic Labs (prev. Fantom)",
    "TRON", "Arbitrum", "Gravity", "Immutable X", "zkSync", "GMX", "Pendle", "Synthetix",
    "Aerodrome Finance", "Curve DAO Token", "Ethena", "Mocaverse", "PancakeSwap",
    "Sushiswap", "Chainlink", "Aave", "BENQI Liquid Staked AVAX", "Compound",
    "Maple Finance", "Vechain", "Venus USDT", "Jito Labs", "Lido DAO", "Stader ETHx",
    "Entangle", "OriginTrail", "Sky (formerly MakerDAO)"
]

# Initialize Hugging Face Inference Client
hf_client = InferenceClient(token=HF_API_KEY)

# Prompt for Llama-3.2-3B-Instruct
HF_PROMPT = """
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
     - Top Security: Aave has never been hacked, which builds trust. Its careful design keeps user money safe.
     - Lots of Options: Aave lets users lend or borrow many types of crypto. This variety makes it more useful than other platforms.
     - New Ideas: Aave created features like flash loans that others now copy. Its innovation keeps it ahead in crypto.

8. **Weaknesses (3 weaknesses, each with a title and 2 sentences)**:
   - List 3 potential concerns for investors.
   - Example:
     - Hard to Understand: Aave’s platform can be tricky for beginners. Terms like ‘collateral’ confuse new users.
     - Market Risks: If crypto prices crash, Aave’s loans could face problems. This makes it sensitive to market swings.
     - Regulation Worries: Governments might make new rules for crypto lending. This could limit how Aave works in some places.

9. **Whitepaper Summary (100-200 words)**:
   - Summarize the project’s core idea, innovation, token use, and problem solved.
   - Use an analogy to make it relatable.
   - Example: "Aave’s platform is like a digital bank where anyone can lend or borrow crypto without paperwork. Instead of dealing with a bank, users add their crypto to shared pools, and others can borrow from them instantly. The AAVE token lets people vote on how the platform runs and share its profits. Aave’s big idea is ‘flash loans,’ where you can borrow and repay in one go without upfront money. It solves the problem of slow, complicated loans by making everything fast and open to everyone. Think of it like a vending machine for loans – pop in your crypto, get cash, and it’s all automatic and secure."

**Output Format**:
Provide the content as plain text with each section clearly labeled using the headings below. Separate sections with a line of dashes (---).

Value Generation
---
[Your text here]

Market Position
---
[Your text here]

Project Size
---
[Your text here]

Real World Impact
---
[Your text here]

Founders
---
[Your text here]

Problem Solving
---
[Your text here]

Strengths
---
- [Title]: [2 sentences]
- [Title]: [2 sentences]
- [Title]: [2 sentences]

Weaknesses
---
- [Title]: [2 sentences]
- [Title]: [2 sentences]
- [Title]: [2 sentences]

Whitepaper Summary
---
[Your text here]
"""

# Create output directory
if not os.path.exists(OUTPUT_DIR):
    os.makedirs(OUTPUT_DIR)

# Function to fetch data from CoinMarketCap
def fetch_cmc_data(symbol):
    if not isinstance(symbol, str):
        logger.warning(f"Invalid symbol type: {symbol}")
        return None
    cmc_symbol = SYMBOL_MAPPING.get(symbol.lower(), symbol.upper())
    try:
        parameters = {
            'symbol': cmc_symbol,
            'convert': 'USD'
        }
        headers = {
            'Accepts': 'application/json',
            'X-CMC_PRO_API_KEY': CMC_API_KEY
        }
        response = requests.get(CMC_URL, headers=headers, params=parameters)
        response.raise_for_status()
        data = response.json()
        
        if cmc_symbol in data['data']:
            coin_data = data['data'][cmc_symbol]
            quote = coin_data['quote']['USD']
            market_cap = "${:.2f} billion".format(quote['market_cap'] / 1e9) if quote['market_cap'] else "N/A"
            volume_24h = "${:.2f} million (24h)".format(quote['volume_24h'] / 1e6) if quote['volume_24h'] else "N/A"
            circulating_supply = "{:.2f} million {}".format(coin_data['circulating_supply'] / 1e6, cmc_symbol) if coin_data['circulating_supply'] else "N/A"
            total_supply = "{:.2f} million {}".format(coin_data['total_supply'] / 1e6, cmc_symbol) if coin_data['total_supply'] else "N/A"
            
            return {
                "marketCap": market_cap,
                "tradingVolume": volume_24h,
                "circulatingSupply": circulating_supply,
                "totalSupply": total_supply
            }
        else:
            logger.warning(f"Symbol not found in CMC response: {cmc_symbol}")
            return None
    except Exception as e:
        logger.error(f"Error fetching CMC data for {symbol}: {str(e)}")
        return None

# Function to generate content with Hugging Face model
def generate_hf_content(name, symbol, sector, description):
    try:
        prompt = HF_PROMPT.format(
            name=name,
            symbol=symbol.upper(),
            sector=sector,
            description=description
        )
        
        response = hf_client.text_generation(
            prompt=prompt,
            model=HF_MODEL,
            max_new_tokens=4000,
            temperature=0.1,
            repetition_penalty=1.2,
            do_sample=True,
            return_full_text=False
        )
        
        # Log raw response for debugging
        logger.debug(f"Raw response for {name}: {response[:200]}...")
        
        # Save raw response to a debug file
        with open(os.path.join(OUTPUT_DIR, f"debug_{name.lower().replace(' ', '_')}.txt"), "w", encoding="utf-8") as f:
            f.write(response)
        
        return response
    except Exception as e:
        logger.error(f"Error generating HF content for {name}: {str(e)}")
        return None

# Main function
def main():
    try:
        # Read CSV
        df = pd.read_csv("how3.io score sheet - Score Sheet (Master).csv")
        logger.info(f"Loaded CSV with {len(df)} rows")
        
        # Filter for the specified projects and remove duplicates
        df = df[df["Project"].isin(PROJECTS)].drop_duplicates(subset=["Project"])
        logger.info(f"Filtered to {len(df)} unique projects with symbols")
        
        if len(df) != len(PROJECTS):
            logger.warning(f"Expected {len(PROJECTS)} projects, but found {len(df)}. Check CSV for missing or duplicate entries.")
            logger.debug(f"Found projects: {df['Project'].tolist()}")
        
        success_count = 0
        error_count = 0
        
        for i, row in df.iterrows():
            try:
                name = row["Project"]
                symbol = row.get("Symbol")
                
                # Validate symbol
                if pd.isna(symbol) or not isinstance(symbol, str):
                    logger.warning(f"Skipping {name}: Invalid or missing symbol ({symbol})")
                    error_count += 1
                    continue
                
                symbol = symbol.lower()
                sector = row.get("Market Sector", "Unknown")
                
                logger.info(f"Processing {name} ({symbol})")
                
                # Get description
                description = f"{name} is a decentralized protocol in the {sector} sector, offering innovative solutions for decentralized applications and services."
                
                # Generate content
                content = generate_hf_content(name, symbol, sector, description)
                if not content:
                    logger.warning(f"No content generated for {name}, skipping")
                    error_count += 1
                    continue
                
                # Fetch CoinMarketCap data
                market_data = fetch_cmc_data(symbol) or {
                    "marketCap": "N/A",
                    "tradingVolume": "N/A",
                    "circulatingSupply": "N/A",
                    "totalSupply": "N/A"
                }
                
                # Get scores
                ugs = float(row.get("UGS", 0)) if pd.notna(row.get("UGS")) else 0
                eqs = float(row.get("EQS", 0)) if pd.notna(row.get("EQS")) else 0
                fvs = float(row.get("FVS", 0)) if pd.notna(row.get("FVS")) else 0
                ss = float(row.get("SS", 0)) if pd.notna(row.get("SS")) else 0
                
                # Save content to .txt file
                output_file = os.path.join(OUTPUT_DIR, f"{name.lower().replace(' ', '_')}.txt")
                with open(output_file, "w", encoding="utf-8") as f:
                    f.write(f"Project: {name}\n")
                    f.write(f"Symbol: {symbol.upper()}\n")
                    f.write(f"Sector: {sector}\n")
                    f.write(f"Description: {description}\n")
                    f.write("---\n")
                    f.write(content)
                    f.write("---\n")
                    f.write("Market Data:\n")
                    f.write(f"- Market Cap: {market_data['marketCap']}\n")
                    f.write(f"- Trading Volume: {market_data['tradingVolume']}\n")
                    f.write(f"- Circulating Supply: {market_data['circulatingSupply']}\n")
                    f.write(f"- Total Supply: {market_data['totalSupply']}\n")
                    f.write("---\n")
                    f.write("Scores:\n")
                    f.write(f"- Growth (UGS): {ugs}\n")
                    f.write(f"- Earning (EQS): {eqs}\n")
                    f.write(f"- Fair Value (FVS): {fvs}\n")
                    f.write(f"- Safety (SS): {ss}\n")
                
                logger.info(f"Saved content for {name} to {output_file}")
                success_count += 1
                
                # Delay to avoid rate limits
                time.sleep(3)
                
            except Exception as e:
                logger.error(f"Error processing {name}: {str(e)}")
                error_count += 1
                continue
        
        logger.info(f"Successfully generated content for {success_count} projects")
        logger.info(f"Failed to process {error_count} projects")
        
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")
        raise

if __name__ == "__main__":
    main()