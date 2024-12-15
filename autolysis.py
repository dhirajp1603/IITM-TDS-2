# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "seaborn",
#   "pandas",
#   "matplotlib",
#   "httpx",
#   "chardet",
#   "ipykernel",
#   "openai",
#   "numpy",
#   "scipy",
# ]
# ///

import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import httpx
import chardet
from pathlib import Path
import asyncio
import scipy.stats as stats
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"

# Ensure token is retrieved from environment variable
def get_token():
    try:
        return os.environ["AIPROXY_TOKEN"]
    except KeyError as e:
        print(f"Error: Environment variable '{e.args[0]}' not set.")
        raise

async def load_data(file_path):
    """Load CSV data with encoding detection."""
    if not os.path.isfile(file_path):
        raise FileNotFoundError(f"Error: File '{file_path}' not found.")

    with open(file_path, 'rb') as f:
        result = chardet.detect(f.read())
    encoding = result['encoding']
    print(f"Detected file encoding: {encoding}")
    return pd.read_csv(file_path, encoding=encoding or 'utf-8')

async def async_post_request(headers, data):
    """Async function to make HTTP requests."""
    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(API_URL, headers=headers, json=data, timeout=30.0)
            response.raise_for_status()
            response.encoding = 'utf-8'
            return response.json()['choices'][0]['message']['content']
        except httpx.HTTPStatusError as e:
            print(f"HTTP error occurred: {e}")
            raise
        except Exception as e:
            print(f"Error during request: {e}")
            raise

async def generate_dynamic_prompt(df, analysis, user_input):
    """Generate a dynamic prompt based on user input and data."""
    prompt = (
        f"You are a data analyst. Based on the following dataset and user input, provide an insightful analysis. "
        f"User's Request: {user_input}\n\n"
        f"Columns: {list(df.columns)}\n"
        f"Data Types: {df.dtypes.to_dict()}\n"
        f"Summary Statistics: {analysis['summary']}\n"
        f"Missing Values: {analysis['missing_values']}\n"
        f"Correlation Matrix: {analysis['correlation']}\n"
        "Make recommendations for further analysis, visualization, and predictive modeling techniques. "
        "Take into account potential limitations and suggest ways to handle missing data and outliers."
    )
    return prompt

async def analyze_and_generate_narrative(df, token, user_input):
    """Analyze data, generate prompts dynamically based on user input, and generate narrative."""
    if df.empty:
        raise ValueError("Error: Dataset is empty.")

    numeric_df = df.select_dtypes(include=['number'])
    analysis = {
        'summary': df.describe(include='all').to_dict(),
        'missing_values': df.isnull().sum().to_dict(),
        'correlation': numeric_df.corr().to_dict() if not numeric_df.empty else {}
    }

    # Generate dynamic prompt based on user input
    prompt = await generate_dynamic_prompt(df, analysis, user_input)

    headers = {
        'Authorization': f'Bearer {token}',
        'Content-Type': 'application/json'
    }

    data = {
        "model": "gpt-4o-mini",
        "messages": [{"role": "user", "content": prompt}]
    }

    try:
        narrative = await async_post_request(headers, data)
    except Exception as e:
        narrative = f"Error generating narrative: {e}"

    print("Analysis and narrative generation complete.")
    return analysis, narrative

async def visualize_data_with_integration(df, output_dir, analysis):
    """Generate visualizations and integrate them into the narrative."""
    sns.set(style="whitegrid")
    numeric_columns = df.select_dtypes(include=['number']).columns

    # Select main columns for distribution based on importance
    selected_columns = numeric_columns[:3] if len(numeric_columns) >= 3 else numeric_columns

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Visualize distribution and correlations
    for column in selected_columns:
        plt.figure(figsize=(6, 6))
        sns.histplot(df[column].dropna(), kde=True, color='skyblue')
        plt.title(f'Distribution of {column}')
        plt.xlabel(column)
        plt.ylabel('Frequency')
        file_name = output_dir / f'{column}_distribution.png'
        plt.savefig(file_name, dpi=100)
        plt.close()

    if len(numeric_columns) > 1:
        plt.figure(figsize=(8, 8))
        corr = df[numeric_columns].corr()
        sns.heatmap(corr, annot=True, cmap='coolwarm', square=True)
        plt.title('Correlation Heatmap')
        file_name = output_dir / 'correlation_heatmap.png'
        plt.savefig(file_name, dpi=100)
        plt.close()

    # Integrating visuals with the narrative in the README
    readme_content = f"### Visualizations:\n"
    for img in output_dir.glob('*.png'):
        readme_content += f"![{img.name}]({img.name})\n"
    return readme_content

async def save_narrative_and_visuals(narrative, output_dir, readme_content):
    """Save narrative and visualizations into a README file."""
    readme_path = output_dir / 'README.md'
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(narrative + "\n\n" + readme_content)
    print(f"Narrative with visuals successfully written to {readme_path}")


async def main(file_path):
    print("Starting autolysis process...")

    # Ensure input file exists
    file_path = Path(file_path)
    if not file_path.is_file():
        print(f"Error: File '{file_path}' does not exist.")
        sys.exit(1)

    # Load token
    try:
        token = get_token()
    except Exception as e:
        print(e)
        sys.exit(1)

    # Load dataset
    try:
        df = await load_data(file_path)
    except FileNotFoundError as e:
        print(e)
        sys.exit(1)
    print("Dataset loaded successfully.")

    # Analyze data with LLM insights
    print("Analyzing data...")
    try:
        analysis, suggestions = await analyze_and_generate_narrative(df, token, "Provide analysis and suggestions")
    except ValueError as e:
        print(e)
        sys.exit(1)

    # Create output directory
    output_dir = Path(file_path.stem)
    output_dir.mkdir(exist_ok=True)

    # Generate visualizations with LLM suggestions
    print("Generating visualizations...")
    readme_content = await visualize_data_with_integration(df, output_dir, analysis)

    # Generate narrative
    print("Generating narrative using LLM...")
    narrative = await analyze_and_generate_narrative(df, token, file_path)

    if narrative != "Narrative generation failed due to an error.":
        await save_narrative_and_visuals(narrative, output_dir, readme_content)
    else:
        print("Narrative generation failed.")

# Execute script
if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: python script.py <file_path>")
        sys.exit(1)
    asyncio.run(main(sys.argv[1]))

