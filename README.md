# how3.io Project Content Generator

A tool for generating structured content for cryptocurrency projects using the Gemini AI API. This script creates detailed, beginner-friendly project descriptions and analysis for how3.io.

## Overview

This script takes a CSV of cryptocurrency projects, generates content for each project using Gemini AI, and outputs structured JSON files that include:

- Value Generation analysis
- Market Position overview
- Project Size and adoption analysis
- Real World Impact
- Founder information
- Problem-Solving approach
- Strengths and Weaknesses analysis
- Whitepaper Summary
- Benchmark scores

## Requirements

- Python 3.6+
- pandas
- google-generativeai
- python-dotenv

## Installation

1. Clone this repository
2. Install required packages:
   ```
   pip install pandas google-generativeai python-dotenv
   ```
3. Create a `.env` file with your Gemini API key:
   ```
   GEMINI_API_KEY=your_api_key_here
   ```

## Input Files Required

1. **CSV Data File**: `how3.io score sheet - Score Sheet (Master).csv` containing project details and scores
2. **CMC Data**: `cmcdata.json` containing market data from CoinMarketCap

## Usage

Run the script to generate content for all target cryptocurrency projects:

```
python complete_content_generator.py
```

For faster testing with just a few projects, uncomment the line:
```python
target_df = target_df.head(2)  # Process just 2 projects for testing
```

### Output

The script generates:

1. Individual JSON files for each cryptocurrency in the `project_content` directory
2. A combined `all_projects.json` file containing data for all projects
3. Raw text files with the unprocessed AI-generated content

## Project Structure

```
├── fixed_content_generator.py  # Main script
├── .env                        # Environment variables (API key)
├── how3.io score sheet - Score Sheet (Master).csv  # Project data
├── cmcdata.json                # CoinMarketCap data
└── project_content/            # Generated output directory
    ├── all_projects.json       # Combined output
    ├── cvx.json                # Individual project files
    ├── algo.json
    ├── etc...
    ├── cvx_raw.txt             # Raw AI responses
    └── etc...
```

## Customization

- Modify the `target_symbols` list in the script to focus on specific cryptocurrencies
- Adjust the `GEMINI_PROMPT` to change the content instructions
- Update `DEFAULT_CONTENT` to change the default fallback content

## Troubleshooting

- **API Key Issues**: Ensure your Gemini API key is valid and properly set in the `.env` file
- **Model Not Found**: The script uses "gemini-2.0-flash" - if this changes, update the model name
- **Rate Limits**: The script adds a delay between API calls to avoid rate limiting

## Credits

Created for how3.io, a crypto analytics platform for retail investors transitioning from traditional finance.
