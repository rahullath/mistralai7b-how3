import json
import re
import os
import logging
import pandas as pd

# Set up logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Output JSON file
OUTPUT_FILE = "crypto_data.json"

def parse_project_text(file_path):
    """Read and parse project JSONs from a text file."""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Split by project names followed by JSON
        # Matches project name (e.g., "AAVE", "Uniswap") followed by JSON
        pattern = r'(\w+(?:\s+\w+)*)\n\s*(\{[\s\S]*?\})(?=\n\s*\w+(?:\s+\w+)*\n\s*\{|\Z)'
        matches = re.finditer(pattern, content, re.MULTILINE)
        
        projects = []
        for match in matches:
            project_name = match.group(1).strip()
            json_str = match.group(2).strip()
            try:
                project_data = json.loads(json_str)
                projects.append((project_name, project_data))
            except json.JSONDecodeError as e:
                logger.error(f"Invalid JSON for {project_name}: {str(e)}")
                continue
        
        logger.info(f"Parsed {len(projects)} projects from {file_path}")
        return projects
    except Exception as e:
        logger.error(f"Error reading {file_path}: {str(e)}")
        return []

def validate_project_data(project_name, project_data):
    """Validate project JSON and extract token key."""
    try:
        # Assume the top-level key is the token (e.g., "aave", "uni")
        token = next(iter(project_data))
        if not token or not isinstance(project_data[token], dict):
            logger.error(f"Invalid structure for {project_name}: Missing or invalid token key")
            return None, None
        
        # Basic validation: check required fields
        required_sections = ["assetOverview", "projectNarrative", "researchAnalysis", "benchmarkScores", "whitepaper"]
        for section in required_sections:
            if section not in project_data[token]:
                logger.warning(f"{project_name} missing section: {section}")
        
        return token, project_data[token]
    except Exception as e:
        logger.error(f"Error validating {project_name}: {str(e)}")
        return None, None

def load_existing_json(output_file):
    """Load existing JSON file if it exists."""
    if os.path.exists(output_file):
        try:
            with open(output_file, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Error loading {output_file}: {str(e)}")
            return {}
    return {}

def save_json(data, output_file):
    """Save JSON data to file."""
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)
        logger.info(f"Saved {len(data)} projects to {output_file}")
    except Exception as e:
        logger.error(f"Error saving {output_file}: {str(e)}")

# Function to validate and update benchmark scores from CSV data
def validate_benchmark_scores(project_data, scores_df):
    """
    Check if benchmark scores in project_data match those in the CSV.
    If not, update them with correct values from CSV.
    """
    try:
        # Find the matching row in scores_df based on Symbol
        symbol = next(iter(project_data))
        
        # Get both uppercase and lowercase versions to try matching
        symbol_upper = symbol.upper()
        
        # Try to find match by uppercase symbol
        matching_row = scores_df[scores_df['Symbol'].str.upper() == symbol_upper]
        
        if matching_row.empty:
            # Try matching by project name
            project = project_data[symbol]
            if 'name' in project:
                project_name = project['name'].replace('-', ' ').title()
                matching_row = scores_df[scores_df['Project'].str.lower() == project_name.lower()]
        
        if matching_row.empty:
            logger.warning(f"No matching row found in CSV for symbol: {symbol_upper}")
            return project_data, False
        
        # If we have multiple matches, take the first one
        if len(matching_row) > 1:
            logger.warning(f"Multiple matches found for {symbol_upper}, using first match")
            matching_row = matching_row.iloc[[0]]
        
        # Extract score values from CSV (handle potential NaN values)
        csv_scores = {}
        for key, csv_key in [("growth", "UGS"), ("earning", "EQS"), ("fairValue", "FVS"), ("safety", "SS")]:
            if pd.notna(matching_row[csv_key].values[0]):
                csv_scores[key] = float(matching_row[csv_key].values[0])
            else:
                logger.warning(f"Missing {csv_key} value for {symbol_upper}")
                csv_scores[key] = 0.0
        
        # Check benchmark scores in project_data
        project = project_data[symbol]
        if "benchmarkScores" not in project:
            logger.warning(f"benchmarkScores section missing for {symbol}, adding it")
            project["benchmarkScores"] = {
                "growth": csv_scores["growth"],
                "earning": csv_scores["earning"],
                "fairValue": csv_scores["fairValue"],
                "safety": csv_scores["safety"],
                "barData": [
                    {"label": "Growth", "value": csv_scores["growth"], "color": "#4CAF50"},
                    {"label": "Earning", "value": csv_scores["earning"], "color": "#2196F3"},
                    {"label": "Fair Value", "value": csv_scores["fairValue"], "color": "#FFC107"},
                    {"label": "Safety", "value": csv_scores["safety"], "color": "#9C27B0"}
                ]
            }
            return project_data, True
        
        # Check and update individual scores
        scores_changed = False
        benchmarkScores = project["benchmarkScores"]
        
        for key in ["growth", "earning", "fairValue", "safety"]:
            if key in csv_scores:  # Only update if we have the CSV value
                if key not in benchmarkScores or abs(benchmarkScores[key] - csv_scores[key]) > 0.01:
                    logger.info(f"Updating {key} score for {symbol} from {benchmarkScores.get(key, 'None')} to {csv_scores[key]}")
                    benchmarkScores[key] = csv_scores[key]
                    scores_changed = True
        
        # Update barData if scores changed
        if scores_changed and "barData" in benchmarkScores:
            for item in benchmarkScores["barData"]:
                if item["label"] == "Growth" and "growth" in csv_scores:
                    item["value"] = csv_scores["growth"]
                elif item["label"] == "Earning" and "earning" in csv_scores:
                    item["value"] = csv_scores["earning"]
                elif item["label"] == "Fair Value" and "fairValue" in csv_scores:
                    item["value"] = csv_scores["fairValue"]
                elif item["label"] == "Safety" and "safety" in csv_scores:
                    item["value"] = csv_scores["safety"]
        elif scores_changed:
            # Create barData if missing but scores changed
            benchmarkScores["barData"] = [
                {"label": "Growth", "value": csv_scores.get("growth", 0), "color": "#4CAF50"},
                {"label": "Earning", "value": csv_scores.get("earning", 0), "color": "#2196F3"},
                {"label": "Fair Value", "value": csv_scores.get("fairValue", 0), "color": "#FFC107"},
                {"label": "Safety", "value": csv_scores.get("safety", 0), "color": "#9C27B0"}
            ]
        
        return project_data, scores_changed
    
    except Exception as e:
        logger.error(f"Error validating benchmark scores for {symbol}: {str(e)}")
        import traceback
        logger.error(traceback.format_exc())
        return project_data, False

# Modified main function
def main(input_file, scores_csv_file):
    """Main function to process projects and generate/append JSON."""
    # Load scores from CSV
    try:
        import pandas as pd
        scores_df = pd.read_csv(scores_csv_file)
        logger.info(f"Loaded scores data for {len(scores_df)} projects from {scores_csv_file}")
    except Exception as e:
        logger.error(f"Error loading scores CSV: {str(e)}")
        scores_df = None
    
    if scores_df is not None:
        logger.info(f"CSV columns: {list(scores_df.columns)}")
        logger.info(f"First few symbols in CSV: {list(scores_df['Symbol'].head())}")
    
    # Parse projects from input file
    projects = parse_project_text(input_file)
    if not projects:
        logger.error("No valid projects found. Exiting.")
        return
    
    # Load existing JSON
    existing_data = load_existing_json(OUTPUT_FILE)
    
    # Process each project
    new_data = existing_data.copy()
    success_count = 0
    error_count = 0
    score_updates = 0
    
    for project_name, project_data in projects:
        token, validated_data = validate_project_data(project_name, project_data)
        if token and validated_data:
            project_data = {token: validated_data}
            
            # Validate and update benchmark scores if CSV data is available
            if scores_df is not None:
                project_data, scores_changed = validate_benchmark_scores(project_data, scores_df)
                if scores_changed:
                    score_updates += 1
            
            # Add/update project data
            if token in new_data:
                logger.warning(f"{project_name} ({token}) already exists. Overwriting.")
            new_data[token] = project_data[token]
            success_count += 1
            logger.info(f"Processed {project_name} ({token})")
        else:
            error_count += 1
    
    # Save updated JSON
    save_json(new_data, OUTPUT_FILE)
    logger.info(f"Completed: {success_count} successful, {error_count} errors, {score_updates} score updates")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2 or len(sys.argv) > 3:
        print("Usage: python googledoctojson.py <input_file> [scores_csv_file]")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} does not exist")
        sys.exit(1)
    
    scores_csv_file = sys.argv[2] if len(sys.argv) == 3 else "how3.io score sheet - Score Sheet (Master).csv"
    if not os.path.exists(scores_csv_file):
        logger.warning(f"Scores CSV file {scores_csv_file} does not exist, proceeding without score validation")
        scores_csv_file = None
    
    main(input_file, scores_csv_file)