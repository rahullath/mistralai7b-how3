import json
import re
import os
import logging

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

def main(input_file):
    """Main function to process projects and generate/append JSON."""
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
    
    for project_name, project_data in projects:
        token, validated_data = validate_project_data(project_name, project_data)
        if token and validated_data:
            if token in new_data:
                logger.warning(f"{project_name} ({token}) already exists. Overwriting.")
            new_data[token] = validated_data
            success_count += 1
            logger.info(f"Processed {project_name} ({token})")
        else:
            error_count += 1
    
    # Save updated JSON
    save_json(new_data, OUTPUT_FILE)
    logger.info(f"Completed: {success_count} successful, {error_count} errors")

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python generate_crypto_json.py <input_file>")
        sys.exit(1)
    
    input_file = sys.argv[1]
    if not os.path.exists(input_file):
        logger.error(f"Input file {input_file} does not exist")
        sys.exit(1)
    
    main(input_file)