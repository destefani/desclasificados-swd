#!/usr/bin/env python3
import os
import json
import glob
import argparse
import collections
from dateutil import parser as date_parser  # pip install python-dateutil
import matplotlib.pyplot as plt

def process_documents(directory):
    """
    Process all JSON files in the given directory and aggregate metadata statistics.
    Returns a dictionary with:
      - total_docs: total documents processed
      - timeline: documents per date (string format)
      - people_count: frequency of each person mentioned
      - places_count: frequency of each place mentioned
      - keywords_count: frequency of each keyword
      - recipients_count: frequency of each recipient
      - doc_type_count: frequency of each document type
    """
    files = glob.glob(os.path.join(directory, "*.json"))
    
    timeline = collections.Counter()
    people_count = collections.Counter()
    places_count = collections.Counter()
    keywords_count = collections.Counter()
    recipients_count = collections.Counter()
    doc_type_count = collections.Counter()
    total_docs = 0

    for file in files:
        try:
            with open(file, 'r', encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error reading {file}: {e}")
            continue

        total_docs += 1
        metadata = data.get("metadata", {})
        
        # Process document date
        doc_date_str = metadata.get("document_date", "Unknown")
        try:
            date_obj = date_parser.parse(doc_date_str)
            date_str = date_obj.strftime("%Y-%m-%d")
        except Exception:
            date_str = doc_date_str
        timeline[date_str] += 1

        # Process people mentioned
        for person in metadata.get("people_mentioned", []):
            people_count[person] += 1

        # Process places mentioned
        for place in metadata.get("places_mentioned", []):
            places_count[place] += 1

        # Process keywords
        for keyword in metadata.get("keywords", []):
            keywords_count[keyword] += 1

        # Process recipients
        for recipient in metadata.get("recipients", []):
            recipients_count[recipient] += 1

        # Process document type
        doc_type = metadata.get("document_type", "Unknown")
        doc_type_count[doc_type] += 1

    return {
        "total_docs": total_docs,
        "timeline": timeline,
        "people_count": people_count,
        "places_count": places_count,
        "keywords_count": keywords_count,
        "recipients_count": recipients_count,
        "doc_type_count": doc_type_count,
    }

def plot_timeline(timeline, output_image='timeline.png'):
    """
    Create and save a bar chart representing the number of documents per date.
    """
    dates = []
    counts = []
    for date_str, count in timeline.items():
        try:
            dates.append(date_parser.parse(date_str))
            counts.append(count)
        except Exception:
            print(f"Skipping non-standard date: {date_str}")
    
    if dates:
        sorted_pairs = sorted(zip(dates, counts))
        sorted_dates, sorted_counts = zip(*sorted_pairs)
        sorted_date_strs = [d.strftime("%Y-%m-%d") for d in sorted_dates]

        plt.figure(figsize=(10, 6))
        plt.bar(sorted_date_strs, sorted_counts)
        plt.xlabel("Document Date")
        plt.ylabel("Number of Documents")
        plt.title("Timeline of Documents")
        plt.xticks(rotation=45)
        plt.tight_layout()
        plt.savefig(output_image)
        plt.close()
    else:
        print("No valid dates available for plotting.")

def generate_html_report(results, timeline_image="timeline.png", output_file="final_report.html"):
    """
    Create an HTML report summarizing the document analysis with embedded images and tables.
    """
    def create_table(counter):
        # Create a basic HTML table from a Counter object
        rows = "".join(f"<tr><td>{k}</td><td>{v}</td></tr>" for k, v in sorted(counter.items(), key=lambda x: x[1], reverse=True))
        return f"<table border='1' cellspacing='0' cellpadding='5'><tr><th>Item</th><th>Count</th></tr>{rows}</table>"

    # Build the HTML content
    html_content = f"""
    <html>
    <head>
      <meta charset="UTF-8">
      <title>Document Analysis Report</title>
      <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; margin-bottom: 20px; }}
        th, td {{ padding: 8px 12px; }}
        h2 {{ border-bottom: 1px solid #ccc; padding-bottom: 5px; }}
      </style>
    </head>
    <body>
      <h1>Declassified Document Analysis Report</h1>
      <p><strong>Total Documents Processed:</strong> {results['total_docs']}</p>

      <h2>Timeline (Documents per Date)</h2>
      <img src="{timeline_image}" alt="Timeline Chart" style="max-width:100%; height:auto;"><br>
      <h3>Timeline Data</h3>
      {create_table(results['timeline'])}

      <h2>People Mentioned</h2>
      {create_table(results['people_count'])}

      <h2>Places Mentioned</h2>
      {create_table(results['places_count'])}

      <h2>Keywords Frequency</h2>
      {create_table(results['keywords_count'])}

      <h2>Recipients Frequency</h2>
      {create_table(results['recipients_count'])}

      <h2>Document Types</h2>
      {create_table(results['doc_type_count'])}

      <p>This report is generated for an analysis of declassified CIA documents about the Chilean dictatorship, aiming to help build the narrative from the CIA perspective.</p>
    </body>
    </html>
    """

    with open(output_file, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"Report saved to {output_file}")

def main():
    parser = argparse.ArgumentParser(
        description="Analyze declassified CIA documents (JSON format) and generate a visual HTML report."
    )
    parser.add_argument("directory", help="Directory containing JSON document files")
    parser.add_argument("--output", default="final_report.html", help="Output HTML report file")
    args = parser.parse_args()

    results = process_documents(args.directory)
    # Save timeline plot as an image file
    plot_timeline(results["timeline"], output_image="timeline.png")
    # Generate the final HTML report
    generate_html_report(results, timeline_image="timeline.png", output_file=args.output)

if __name__ == "__main__":
    main()
