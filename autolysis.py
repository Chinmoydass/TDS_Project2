import os
import sys
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
import json
import requests

AIPROXY_TOKEN = os.environ.get("AIPROXY_TOKEN")
if not AIPROXY_TOKEN:
    raise EnvironmentError("AIPROXY_TOKEN environment variable not set.")

PROXY_URL = "https://aiproxy.sanand.workers.dev/openai/v1/chat/completions"
HEADERS = {
    "Authorization": f"Bearer {AIPROXY_TOKEN}",
    "Content-Type": "application/json"
}

def load_data(filename):
    try:
        # Try reading with utf-8 encoding first
        df = pd.read_csv(filename, encoding='utf-8')
        return df
    except UnicodeDecodeError:
        # If utf-8 fails, try reading with ISO-8859-1 encoding
        print(f"UTF-8 decoding failed. Trying ISO-8859-1 encoding for {filename}.")
        try:
            df = pd.read_csv(filename, encoding='ISO-8859-1')
            return df
        except Exception as e:
            print(f"Error loading file with ISO-8859-1 encoding: {e}")
            return None
    except Exception as e:
        print(f"Error loading file: {e}")
        return None

def create_visualizations(df, output_dir):
    # Generate up to 3 visualizations and save them as PNG files.
    os.makedirs(output_dir, exist_ok=True)

    numeric_cols = df.select_dtypes(include=["number"]).columns
    if numeric_cols.empty:
        print("No numeric columns found for visualizations.")
        return

    # Function to ensure saved images are 512x512 pixels
    def save_plot(fig, output_path):
        # Save with a fixed DPI to ensure 512x512 resolution
        fig.savefig(output_path, dpi=100)  # DPI = 100 ensures 5.12 inches = 512 pixels
        plt.close(fig)

    # Generate a histogram for the first numeric column
    if len(numeric_cols) >= 1:
        fig, ax = plt.subplots(figsize=(5.12, 5.12))  # Size in inches
        sns.histplot(df[numeric_cols[0]].dropna(), kde=True, ax=ax)
        ax.set_title(f"Histogram of {numeric_cols[0]}")
        save_plot(fig, f"{output_dir}/{numeric_cols[0]}_histogram.png")

    # Generate a box plot for the second numeric column if available
    if len(numeric_cols) >= 2:
        fig, ax = plt.subplots(figsize=(5.12, 5.12))  # Size in inches
        sns.boxplot(x=df[numeric_cols[1]].dropna(), ax=ax)
        ax.set_title(f"Box Plot of {numeric_cols[1]}")
        save_plot(fig, f"{output_dir}/{numeric_cols[1]}_boxplot.png")

    # Generate a heatmap of correlations
    if len(numeric_cols) > 1:  # Correlation heatmap requires at least 2 numeric columns
        fig, ax = plt.subplots(figsize=(5.12, 5.12))  # Size in inches
        sns.heatmap(df.corr(numeric_only=True), annot=True, fmt=".2f", cmap="coolwarm", ax=ax)
        ax.set_title("Correlation Heatmap")
        save_plot(fig, f"{output_dir}/correlation_heatmap.png")

def query_llm(prompt):
    try:
        # Construct the payload
        payload = {
            "model": "gpt-4o-mini",
            "messages": [
                {"role": "user", "content": prompt}
            ]
        }

        # Make the POST request
        response = requests.post(PROXY_URL, headers=HEADERS, json=payload)

        # Handle the response
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        else:
            print(f"Error: {response.status_code}, {response.text}")
            return "Error querying LLM."
    except Exception as e:
        print(f"Error querying LLM: {e}")
        return "Error querying LLM."

def generate_markdown_story(df_summary, output_dir):
    # Modify the prompt to ask for a detailed and insightful analysis
    prompt = (
        "You are an expert data scientist. Based on the following data analysis summary, "
        "provide a detailed and insightful narrative in Markdown format. "
        "Focus on the key insights, patterns, trends, correlations, and any significant findings from the data. "
        "Also, highlight any missing data and suggest possible reasons for it. "
        "Provide interpretations of the visualizations and how they relate to the data's characteristics.\n\n"
        f"{json.dumps(df_summary, indent=2)}"
    )

    # Send the refined prompt to the AI model
    narrative = query_llm(prompt)

    # Save the generated markdown story to the README.md file
    with open(f"{output_dir}/README.md", "w") as file:
        file.write(narrative)

def analyze_data(df):
    # Perform basic data analysis
    summary_stats = df.describe(include="all").to_dict()
    for col, stats in summary_stats.items():
        for stat, value in stats.items():
            if pd.isnull(value):
                summary_stats[col][stat] = None

    summary = {
        "columns": list(df.columns),
        "types": {col: str(dtype) for col, dtype in df.dtypes.items()},
        "missing_values": df.isnull().sum().to_dict(),
        "summary_stats": summary_stats,
        "correlation_matrix": df.corr(numeric_only=True).fillna(0).to_dict(),
    }
    return summary

def run_analysis(input_file):
    # Process the dataset
    try:
        if not os.path.exists(input_file):
            print(f"File not found: {input_file}")
            return

        dataset_name = os.path.splitext(os.path.basename(input_file))[0]
        output_dir = dataset_name

        df = load_data(input_file)
        if df is None:
            return

        summary = analyze_data(df)
        create_visualizations(df, output_dir)
        generate_markdown_story(summary, output_dir)

        print(f"Analysis complete. Outputs saved in {output_dir}/")
    except Exception as e:
        print(f"An error occurred: {e}")

# Command-line argument handling
def main():
    if len(sys.argv) != 2:
        print("Usage: python script.py <dataset.csv>")
        sys.exit(1)

    input_file = sys.argv[1]
    run_analysis(input_file)

if __name__ == "__main__":
    main()

