# /// script
# requires-python = ">=3.11"
# dependencies = [
#   "httpx",
#   "pandas",
#   "seaborn",
#   "matplotlib",
#   "scikit-learn",
# ]
# ///

import os
import sys
import httpx
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from sklearn.ensemble import IsolationForest
from sklearn.cluster import KMeans
from sklearn.preprocessing import StandardScaler
from sklearn.impute import SimpleImputer

# Constants
API_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
API_TOKEN = os.getenv("AIPROXY_TOKEN")  # Fetch API token from environment variable

# Function to read CSV files
def read_csv_file(filename):
    for encoding in ["utf-8", "ISO-8859-1"]:
        try:
            return pd.read_csv(filename, encoding=encoding)
        except UnicodeDecodeError:
            continue
    raise ValueError("Failed to decode the file with supported encodings.")

# Perform data analysis
def analyze_data(df):
    numeric_df = df.select_dtypes(include=["number"])
    non_numeric_df = df.select_dtypes(exclude=["number"])

    # Impute missing values
    numeric_imputer = SimpleImputer(strategy='mean')
    df[numeric_df.columns] = numeric_imputer.fit_transform(numeric_df)

    non_numeric_imputer = SimpleImputer(strategy='most_frequent')
    df[non_numeric_df.columns] = non_numeric_imputer.fit_transform(non_numeric_df)

    return {
        "summary": df.describe(include="all").to_dict(),
        "missing_values": df.isnull().sum().to_dict(),
        "correlation": numeric_df.corr().to_dict(),
        "outliers": detect_outliers(numeric_df),
        "clusters": cluster_analysis(numeric_df),
    }

# Detect outliers using Isolation Forest
def detect_outliers(numeric_df):
    if numeric_df.empty:
        return "No numeric data available for outlier detection."

    clf = IsolationForest(contamination=0.05, random_state=42)
    outliers = clf.fit_predict(numeric_df)
    return {"outliers": (outliers == -1).sum(), "inliers": (outliers != -1).sum()}

# Perform clustering analysis
def cluster_analysis(numeric_df):
    if numeric_df.shape[0] > 1 and numeric_df.shape[1] > 1:
        scaler = StandardScaler()
        scaled_data = scaler.fit_transform(numeric_df)
        kmeans = KMeans(n_clusters=3, random_state=42, n_init=10)
        clusters = kmeans.fit_predict(scaled_data)

        return {
            "cluster_counts": pd.Series(clusters).value_counts().to_dict(),
            "centroids": pd.DataFrame(kmeans.cluster_centers_, columns=numeric_df.columns).to_dict(orient="list")
        }
    return "Insufficient numeric data for clustering."

# Generate visualizations
def generate_visualizations(df, output_dir):
    charts = []
    numeric_df = df.select_dtypes(include=["number"])

    # Correlation heatmap
    if numeric_df.shape[1] > 1:
        plt.figure(figsize=(10, 6))
        sns.heatmap(numeric_df.corr(), annot=True, cmap="coolwarm")
        plt.title("Correlation Matrix")
        correlation_file = os.path.join(output_dir, "correlation_matrix.png")
        plt.savefig(correlation_file)
        charts.append(correlation_file)
        plt.close()

    # Distribution plots
    for col in numeric_df.columns:
        plt.figure(figsize=(8, 5))
        sns.histplot(numeric_df[col].dropna(), kde=True)
        plt.title(f"Distribution of {col}")
        dist_file = os.path.join(output_dir, f"{col}_distribution.png")
        plt.savefig(dist_file)
        charts.append(dist_file)
        plt.close()

    # Missing values heatmap
    if df.isnull().sum().any():
        plt.figure(figsize=(10, 6))
        sns.heatmap(df.isnull(), cbar=False, cmap="viridis")
        plt.title("Missing Values Heatmap")
        missing_file = os.path.join(output_dir, "missing_values_heatmap.png")
        plt.savefig(missing_file)
        charts.append(missing_file)
        plt.close()

    return charts

# Send data to LLM
def send_to_llm(messages):
    if not API_TOKEN:
        raise ValueError("API token is not set in the environment variables.")

    headers = {
        "Authorization": f"Bearer {API_TOKEN}",
        "Content-Type": "application/json",
    }

    try:
        response = httpx.post(API_URL, json=messages, headers=headers, timeout=30.0)
        response.raise_for_status()
        return response.json()["choices"][0]["message"]["content"]
    except httpx.RequestError as exc:
        raise RuntimeError(f"An error occurred while making a request: {exc}")

# Narrate story based on analysis
def narrate_story(analysis, charts, output_dir):
    prompt = f"""
    Create a README.md narrating this analysis:
    Data Summary: {analysis['summary']}
    Missing Values: {analysis['missing_values']}
    Correlation Matrix: {analysis['correlation']}
    Outlier Detection: {analysis['outliers']}
    Clustering Analysis: {analysis['clusters']}
    Attach these charts: {charts}.
    """

    messages = {
        "model": "gpt-4o-mini",
        "messages": [
            {"role": "system", "content": "You are a Markdown writer."},
            {"role": "user", "content": prompt}
        ],
    }

    story = send_to_llm(messages)
    readme_path = os.path.join(output_dir, "README.md")
    with open(readme_path, "w", encoding="utf-8") as file:
        file.write(story)

# Main function
def main():
    if len(sys.argv) != 2:
        print("Usage: python autolysis.py <dataset.csv>")
        sys.exit(1)

    dataset_path = sys.argv[1]
    if not os.path.isfile(dataset_path):
        print(f"Error: The file '{dataset_path}' does not exist.")
        sys.exit(1)

    output_dir = os.path.splitext(os.path.basename(dataset_path))[0]
    os.makedirs(output_dir, exist_ok=True)

    try:
        df = read_csv_file(dataset_path)
        analysis = analyze_data(df)
        charts = generate_visualizations(df, output_dir)
        narrate_story(analysis, charts, output_dir)
        print(f"Analysis complete. See the '{output_dir}' directory for results.")
    except Exception as e:
        print(f"An error occurred: {e}")

if __name__ == "__main__":
    main()
