import json
import glob
from pathlib import Path

import pandas as pd
import matplotlib.pyplot as plt

# --- Configuration: adjust this path to your generated JSON transcripts directory
DATA_DIR = Path(__file__).parent / 'data/generated_transcripts'

# --- Load and parse all JSON transcripts
json_files = sorted(DATA_DIR.glob('*.json'))
records = []
for file in json_files:
    try:
        with open(file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            records.append(data)
    except (json.JSONDecodeError, OSError) as e:
        print(f"Skipping invalid file {file.name}: {e}")

if not records:
    print("No valid JSON transcripts found in:", DATA_DIR)
    exit(1)

# --- Flatten nested metadata with pandas.json_normalize
# Use '_' as separator to avoid dots in column names
df = pd.json_normalize(records, sep='_')

# --- Rename relevant columns for convenience
rename_map = {
    'metadata.document_date': 'document_date',
    'metadata.classification_level': 'classification_level',
    'metadata.document_type': 'document_type',
    'metadata.language': 'language',
    'metadata.page_count': 'page_count',
    'metadata.keywords': 'keywords',
}
df = df.rename(columns=rename_map)

# --- Ensure 'keywords' exists and is list-typed
if 'keywords' in df.columns:
    df['keywords'] = df['keywords'].apply(lambda k: k if isinstance(k, list) else [])
else:
    df['keywords'] = []

# --- Parse 'document_date' into datetime, coerce invalids to NaT
if 'document_date' in df.columns:
    df['document_date'] = pd.to_datetime(
        df['document_date'], format='%Y-%m-%d', errors='coerce'
    )
else:
    print("Warning: 'document_date' column not found.")
    df['document_date'] = pd.NaT

# --- Plot 1: Classification Level Distribution
def plot_classification_distribution(df):
    if 'classification_level' not in df.columns:
        print("No 'classification_level' column to plot.")
        return

    counts = df['classification_level'].fillna('UNKNOWN').value_counts()
    plt.figure()
    counts.plot(kind='bar')
    plt.title('Document Classification Distribution')
    plt.xlabel('Classification Level')
    plt.ylabel('Number of Documents')
    plt.tight_layout()
    plt.show()

# --- Plot 2: Documents Over Time (by Year)
def plot_documents_over_time(df):
    if df['document_date'].isna().all():
        print("No valid 'document_date' values to plot.")
        return

    # group by year
    df['year'] = df['document_date'].dt.year
    counts = df.dropna(subset=['year'])['year'].astype(int).value_counts().sort_index()
    plt.figure()
    counts.plot()
    plt.title('Documents Over Time')
    plt.xlabel('Year')
    plt.ylabel('Number of Documents')
    plt.tight_layout()
    plt.show()

# --- Plot 3: Top Keywords
def plot_top_keywords(df, top_n=10):
    if 'keywords' not in df.columns:
        print("No 'keywords' column to plot.")
        return

    # explode and count
    exploded = df.explode('keywords')
    exploded['keywords'] = exploded['keywords'].fillna('')
    counts = exploded['keywords'].value_counts().drop('', errors='ignore').head(top_n)
    if counts.empty:
        print("No keywords to plot.")
        return

    plt.figure()
    counts.plot(kind='bar')
    plt.title(f'Top {top_n} Keywords')
    plt.xlabel('Keyword')
    plt.ylabel('Frequency')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.show()

# --- Main: run all
if __name__ == '__main__':
    plot_classification_distribution(df)
    plot_documents_over_time(df)
    plot_top_keywords(df, top_n=10)
