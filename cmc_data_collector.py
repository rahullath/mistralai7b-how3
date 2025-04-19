import pandas as pd
import requests
import json
import os
import logging
import time
from dotenv import load_dotenv

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()

# Configuration
CMC_API_KEY = os.getenv("CMC_API_KEY")
CMC_URL = "https://pro-api.coinmarketcap.com/v1/cryptocurrency/quotes/latest"
OUTPUT_FILE = "cmcdata.json"

# Symbol mapping for known CoinMarketCap discrepancies
SYMBOL_MAPPING = {
    "aptos": "APT",
    "sonic labs (prev. fantom)": "FTM",
    "sky (formerly makerdao)": "SKY",
    "benqi liquid staked avax": "QI",
    "venus usdt": "VUSDT"
}

def fetch_cmc_data(symbol):
    if not isinstance(symbol, str):
        if isinstance(symbol, float):
            logger.warning(f"Invalid symbol type (float): {symbol}")
            return None
        else:
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
        response = requests.get(CMC_URL, headers=headers, params=parameters, verify=False)
        response.raise_for_status()
        
        # Handle rate limiting
        if response.status_code == 429:
            logger.warning(f"Rate limit hit for {symbol}, waiting 60 seconds")
            time.sleep(60)
            response = requests.get(CMC_URL, headers=headers, params=parameters, verify=False)
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

def main():
    try:
        # Read CSV
        df = pd.read_csv("how3.io score sheet - Score Sheet (Master).csv")
        logger.info(f"Loaded CSV with {len(df)} rows")
        
        # Collect CMC data
        cmc_data = {}
        error_count = 0
        
        for i, row in df.iterrows():
            try:
                symbol = row["Symbol"].lower()
                name = row["Project"]
                
                logger.info(f"Fetching CMC data for {name} ({symbol})")
                data = fetch_cmc_data(symbol)
                if data:
                    cmc_data[symbol] = data
                else:
                    logger.warning(f"Could not fetch CMC data for {name} ({symbol})")
                    error_count += 1
                
                time.sleep(3)
            except Exception as e:
                logger.error(f"Error processing {row['Project']}: {e}")
                error_count += 1
                continue
        
        # Save CMC data to JSON file
        with open(OUTPUT_FILE, "w") as f:
            json.dump(cmc_data, f, indent=4)
        
        logger.info(f"Successfully fetched CMC data for {len(cmc_data)} projects")
        logger.info(f"Failed to fetch CMC data for {error_count} projects")
    
    except Exception as e:
        logger.error(f"Fatal error in main: {str(e)}")

if __name__ == "__main__":
    main()
