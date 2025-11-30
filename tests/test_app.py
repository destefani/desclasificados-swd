import streamlit as st
import os
import json
import glob
import collections
from dateutil import parser as date_parser  # pip install python-dateutil
import plotly.express as px
import pandas as pd
import datetime

TRANSCRIPTS_DIR = "/Users/marcelo/code/documents/desclasificados/data/generated_transcripts"

def process_documents_from_directory(directory):
    """
    Process all JSON files from a given local directory and aggregate metadata statistics.
    
    Returns a dictionary with:
      - total_docs: total number of documents processed
      - timeline: documents per date (no grouping applied yet)
      - people_count: frequency count of people mentioned
      - places_count: frequency count of places mentioned
      - keywords_count: frequency count of keywords
      - recipients_count: frequency count of recipients
      - doc_type_count: frequency count of document types
    """
    timeline = collections.Counter()
    people_count = collections.Counter()
    places_count = collections.Counter()
    keywords_count = collections.Counter()
    recipients_count = collections.Counter()
    doc_type_count = collections.Counter()
    total_docs = 0

    # Look for JSON files in the given directory.
    json_files = glob.glob(os.path.join(directory, "*.json"))
    for filename in json_files:
        try:
            with open(filename, 'r', encoding="utf-8") as f:
                data = json.load(f)
            total_docs += 1
            metadata = data.get("metadata", {})

            # Process document date using ISO 8601 (YYYY-MM-DD) if possible
            doc_date_str = metadata.get("document_date", "Unknown")
            try:
                date_obj = date_parser.parse(doc_date_str)
                # Store the date in ISO 8601 string format for now
                date_str = date_obj.strftime("%Y-%m-%d")
            except Exception:
                date_str = "Unknown"
            timeline[date_str] += 1

            # Aggregate people mentioned
            for person in metadata.get("people_mentioned", []):
                people_count[person] += 1

            # Aggregate places mentioned
            for place in metadata.get("places_mentioned", []):
                places_count[place] += 1

            # Aggregate keywords
            for keyword in metadata.get("keywords", []):
                keywords_count[keyword] += 1

            # Aggregate recipients
            for recipient in metadata.get("recipients", []):
                recipients_count[recipient] += 1

            # Aggregate document types
            doc_type = metadata.get("document_type", "Unknown")
            doc_type_count[doc_type] += 1

        except Exception as e:
            st.error(f"Error reading {filename}: {e}")

    return {
        "total_docs": total_docs,
        "timeline": timeline,
        "people_count": people_count,
        "places_count": places_count,
        "keywords_count": keywords_count,
        "recipients_count": recipients_count,
        "doc_type_count": doc_type_count,
    }

def group_dates(timeline, grouping):
    """
    Convert the 'timeline' counter (which is keyed by date_str in ISO8601) into
    a new Counter with grouping by 'day', 'month', or 'year'.
    """
    grouped_timeline = collections.Counter()
    for date_str, count in timeline.items():
        if date_str == "Unknown":
            # Keep unknown date separate
            grouped_timeline["Unknown"] += count
            continue
        try:
            dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
        except ValueError:
            # If date doesn't parse, treat as unknown
            grouped_timeline["Unknown"] += count
            continue
        
        if grouping == "day":
            key = dt.strftime("%Y-%m-%d")
        elif grouping == "month":
            key = dt.strftime("%Y-%m")
        elif grouping == "year":
            key = dt.strftime("%Y")
        else:
            key = dt.strftime("%Y-%m-%d")
        grouped_timeline[key] += count
    return grouped_timeline

def build_dataframe(timeline, ignore_outliers=True):
    """
    Build a DataFrame from the timeline Counter.
    Convert valid date strings to actual datetime objects, ignoring or including outliers.
    """
    rows = []
    for date_str, count in timeline.items():
        if date_str == "Unknown":
            # Keep unknown as NaN or None
            rows.append((None, "Unknown", count))
        else:
            try:
                dt = datetime.datetime.strptime(date_str, "%Y-%m-%d")
                # Optionally ignore out-of-range dates
                if ignore_outliers and (dt.year < 1900 or dt.year > 2100):
                    continue
                rows.append((dt, date_str, count))
            except ValueError:
                # If cannot parse, treat as unknown
                rows.append((None, date_str, count))
    df = pd.DataFrame(rows, columns=["DateTime", "DateStr", "Count"])
    # Sort by actual DateTime
    df_valid = df[df["DateTime"].notna()].sort_values("DateTime")
    df_invalid = df[df["DateTime"].isna()]
    df = pd.concat([df_valid, df_invalid], ignore_index=True)
    return df

def create_interactive_bar_chart(df, title="Timeline of Documents"):
    """
    Create a Plotly bar chart with a date axis, enabling a range slider for zoom/pan.
    """
    # We'll rely on 'DateTime' for a proper date axis
    fig = px.bar(
        df,
        x="DateTime",
        y="Count",
        title=title,
        hover_data=["DateStr", "Count"],
    )
    fig.update_layout(
        xaxis_title="Document Date",
        yaxis_title="Number of Documents",
        xaxis=dict(
            rangeselector=dict(
                buttons=list([
                    dict(count=1, label="1m", step="month", stepmode="backward"),
                    dict(count=6, label="6m", step="month", stepmode="backward"),
                    dict(count=1, label="1y", step="year", stepmode="backward"),
                    dict(step="all")
                ])
            ),
            rangeslider=dict(visible=True),
            type="date"
        )
    )
    return fig

def display_counter(counter, title):
    """
    Convert a Counter object to a sorted Pandas DataFrame and display it in Streamlit.
    """
    st.subheader(title)
    if counter:
        df = pd.DataFrame(counter.items(), columns=["Item", "Count"]).sort_values("Count", ascending=False)
        st.dataframe(df, use_container_width=True)
    else:
        st.write("No data available.")

def main():
    st.title("Declassified CIA Documents Explorer (Improved Plotly Version)")
    st.write(
        "This app processes JSON files from a local directory and displays an **interactive** timeline chart "
        "with optional grouping, outlier date filtering, and a range slider for easy navigation."
    )

    # Sidebar for configuration
    st.sidebar.header("Configuration")
    directory = st.sidebar.text_input("Local JSON Directory", value=TRANSCRIPTS_DIR)
    grouping = st.sidebar.radio(
        "Group Dates By",
        options=["day", "month", "year"],
        index=0,
        help="Select how you want to group the dates in the timeline chart."
    )
    ignore_outliers = st.sidebar.checkbox(
        "Ignore Out-of-Range Dates (Before 1900 or After 2100)",
        value=True
    )
    reprocess = st.sidebar.button("Reprocess Data")

    # Use session_state to cache processed data
    if "data_processed" not in st.session_state or reprocess:
        st.session_state.data_processed = process_documents_from_directory(directory)

    results = st.session_state.data_processed
    st.write(f"### Total Documents Processed: {results['total_docs']}")

    # Group and build a DataFrame
    grouped_timeline = group_dates(results["timeline"], grouping)
    df_timeline = build_dataframe(grouped_timeline, ignore_outliers=ignore_outliers)

    # Plotly interactive chart
    st.subheader("Timeline (Interactive)")
    if not df_timeline.empty:
        fig = create_interactive_bar_chart(df_timeline)
        st.plotly_chart(fig, use_container_width=True)
    else:
        st.write("No valid timeline data to display.")

    # Show timeline data in a table
    st.subheader("Timeline Data Table")
    if not df_timeline.empty:
        st.dataframe(df_timeline[["DateStr", "Count"]], use_container_width=True)
    else:
        st.write("No timeline data.")

    # Display additional aggregated results
    display_counter(results["people_count"], "People Mentioned")
    display_counter(results["places_count"], "Places Mentioned")
    display_counter(results["keywords_count"], "Keywords Frequency")
    display_counter(results["recipients_count"], "Recipients Frequency")
    display_counter(results["doc_type_count"], "Document Types")

if __name__ == '__main__':
    main()
