import os
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import openai
import json
from sklearn.preprocessing import LabelEncoder
from sklearn.cluster import KMeans
from sklearn.impute import SimpleImputer
import numpy as np
import chardet

# Set your API key for OpenAI
openai.api_key = "eyJhbGciOiJIUzI1NiJ9.eyJlbWFpbCI6IjIzZjEwMDEyOTNAZHMuc3R1ZHkuaWl0bS5hYy5pbiJ9.4fR3QAcCsv_E53vfMn6AO1XHtcLS58pVx8al4ADjlPk"

def load_data(file_path):
    rawdata = open(file_path, 'rb').read()
    result = chardet.detect(rawdata)
    encoding = result['encoding']
    """Load the CSV dataset with detected encoding."""
    return pd.read_csv(file_path, encoding=encoding)

def analyze_data(df):
    """Analyze the dataset by calculating summary statistics and identifying missing values."""
    summary = df.describe(include='all').transpose()
    missing_values = df.isnull().sum()
    return summary, missing_values

def correlation_matrix(df):
    """Calculate the correlation matrix for numerical features, ignoring non-numeric columns."""
    # Select only numeric columns
    df_numeric = df.select_dtypes(include=[np.number])

    # If no numeric columns are found, return an empty DataFrame
    if df_numeric.empty:
        print("No numeric columns found for correlation calculation.")
        return pd.DataFrame()

    return df_numeric.corr()


def plot_correlation_matrix(corr_matrix, filename="correlation_matrix.png"):
    """Plot and save the correlation matrix as a heatmap."""
    plt.figure(figsize=(10, 8))
    sns.heatmap(corr_matrix, annot=True, cmap='coolwarm', fmt=".2f", linewidths=0.5)
    plt.title("Correlation Matrix")
    plt.savefig(filename, format="png")
    plt.close()

def cluster_analysis(df, n_clusters=3):
    """Perform K-means clustering and return the labels."""
    # Select numeric columns for clustering
    df_numeric = df.select_dtypes(include=[np.number])
    
    # Handle missing values (impute with mean)
    imputer = SimpleImputer(strategy='mean')  # Imputes missing values with the mean
    df_numeric = pd.DataFrame(imputer.fit_transform(df_numeric), columns=df_numeric.columns)
    
    # Perform KMeans clustering
    kmeans = KMeans(n_clusters=n_clusters, random_state=42)
    clusters = kmeans.fit_predict(df_numeric)
    
    # Add the cluster labels to the original dataframe
    df['Cluster'] = clusters
    return df, kmeans

def plot_clusters(df, filename="clusters.png"):
    """Plot the clusters based on the first two numerical columns."""
    plt.figure(figsize=(8, 6))
    sns.scatterplot(data=df, x=df.columns[0], y=df.columns[1], hue='Cluster', palette='Set2', s=100)
    plt.title("Cluster Analysis")
    plt.xlabel(df.columns[0])
    plt.ylabel(df.columns[1])
    plt.savefig(filename, format="png")
    plt.close()

def generate_markdown_report(df, summary, missing_values, corr_matrix, analysis_results):
    """Generate the README markdown report with the analysis results."""
    report = f"# Automated Data Analysis\n\n"
    report += f"## Dataset Overview\n\n"
    report += f"Dataset contains {len(df)} rows and {df.shape[1]} columns.\n\n"
    
    report += f"## Summary Statistics\n\n{summary.to_markdown()}\n\n"
    
    report += f"## Missing Values\n\n{missing_values.to_frame().to_markdown()}\n\n"
    
    report += f"## Correlation Matrix\n\n{corr_matrix.to_markdown()}\n\n"
    
    report += f"## Cluster Analysis\n\nThe data has been divided into clusters. See the cluster visualization below.\n\n"
    
    report += f"## Insights & Implications\n\n{analysis_results}\n"
    
    return report

def call_llm_for_narrative(df, summary, missing_values, corr_matrix, analysis_results):
    """Use OpenAI's LLM to generate a narrative based on the analysis."""
    prompt = f"""
    The following data was analyzed:
    - Dataset: {json.dumps(df.head().to_dict())}
    - Summary statistics: {json.dumps(summary.to_dict())}
    - Missing values: {json.dumps(missing_values.to_dict())}
    - Correlation matrix: {json.dumps(corr_matrix.to_dict())}
    - Insights & Implications: {analysis_results}

    Please summarize the findings and provide a story-like narrative about the dataset, its analysis, and any relevant implications.
    """
    
    response = openai.Completion.create(
        model="gpt-3.5-turbo",
        prompt=prompt,
        max_tokens=1500,
        temperature=0.7,
    )

    return response.choices[0].text.strip()

def save_report(report, output_file="README.md"):
    """Save the markdown report to a file."""
    with open(output_file, 'w') as f:
        f.write(report)

def main(file_path):
    """Main function to run the analysis and create the output files."""
    # Load the dataset
    df = load_data(file_path)
    
    # Analyze the data
    summary, missing_values = analyze_data(df)
    corr_matrix = correlation_matrix(df)
    
    # Plot visualizations
    plot_correlation_matrix(corr_matrix)
    df_with_clusters, kmeans = cluster_analysis(df)
    plot_clusters(df_with_clusters)
    
    # Generate insights and use LLM for narrative
    analysis_results = "The clustering identified distinct groups based on the features. Further analysis could help tailor strategies."
    narrative = call_llm_for_narrative(df, summary, missing_values, corr_matrix, analysis_results)
    
    # Generate markdown report
    report = generate_markdown_report(df, summary, missing_values, corr_matrix, narrative)
    
    # Save the report and images
    save_report(report)
    
    print("Analysis complete. Check the README.md and PNG files for results.")

if __name__ == "__main__":
    import sys
    if len(sys.argv) < 2:
        print("Usage: python autolysis.py <file_path>")
        exit(1)

    file_path = sys.argv[1]
    main(file_path)
