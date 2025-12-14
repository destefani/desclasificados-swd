"""
Keyword word cloud visualization using wordcloud2.js.

Generates interactive word clouds showing keyword frequency
from declassified documents.
"""

import json
from collections import Counter
from typing import Any


# wordcloud2.js CDN
WORDCLOUD2_CDN = "https://cdn.jsdelivr.net/npm/wordcloud@1.2.2/src/wordcloud2.min.js"

# Color palette for keywords (will cycle through these)
KEYWORD_COLORS = [
    "#DC2626",  # Red
    "#2563EB",  # Blue
    "#059669",  # Green
    "#7C3AED",  # Purple
    "#D97706",  # Amber
    "#0891B2",  # Cyan
    "#BE185D",  # Pink
    "#4F46E5",  # Indigo
]


def prepare_wordcloud_data(
    keyword_count: Counter,
    max_words: int = 100,
    min_count: int = 2,
) -> list[list[Any]]:
    """
    Prepare keyword data for wordcloud2.js.

    Args:
        keyword_count: Counter of keyword frequencies
        max_words: Maximum number of words to include
        min_count: Minimum frequency to include a word

    Returns:
        List of [word, weight] pairs for wordcloud2.js
    """
    # Filter and get top keywords
    filtered = {k: v for k, v in keyword_count.items() if v >= min_count and k}
    top_keywords = Counter(filtered).most_common(max_words)

    if not top_keywords:
        return []

    # Scale weights for better visualization
    # wordcloud2 works best with weights roughly in range 10-100
    max_count = top_keywords[0][1] if top_keywords else 1
    min_weight = 12
    max_weight = 80

    word_list = []
    for word, count in top_keywords:
        # Scale logarithmically for better distribution
        if max_count > 1:
            # Normalize to 0-1, then scale to weight range
            normalized = count / max_count
            weight = min_weight + (normalized * (max_weight - min_weight))
        else:
            weight = min_weight

        word_list.append([word, weight, count])  # Include original count for tooltip

    return word_list


def generate_keyword_cloud(
    keyword_count: Counter,
    container_id: str = "keyword-cloud",
    width: int = 800,
    height: int = 400,
    max_words: int = 80,
    min_count: int = 2,
) -> str:
    """
    Generate an interactive word cloud for keywords.

    Args:
        keyword_count: Counter of keyword frequencies
        container_id: HTML element ID
        width: Canvas width in pixels
        height: Canvas height in pixels
        max_words: Maximum words to display
        min_count: Minimum frequency to include

    Returns:
        HTML string with embedded JavaScript
    """
    word_data = prepare_wordcloud_data(keyword_count, max_words, min_count)

    if not word_data:
        return "<p><em>No keyword data available for word cloud</em></p>"

    # Prepare data for JS (just word and weight, store counts separately)
    word_list_json = json.dumps([[w[0], w[1]] for w in word_data])
    word_counts = {w[0]: w[2] for w in word_data}
    word_counts_json = json.dumps(word_counts)
    colors_json = json.dumps(KEYWORD_COLORS)

    func_name = container_id.replace('-', '_')

    html = f'''
<div class="wordcloud-section" style="max-width: 100%; overflow: hidden;">
    <div class="wordcloud-controls" style="margin-bottom: 10px; display: flex; gap: 10px; align-items: center; flex-wrap: wrap;">
        <button onclick="regenerateCloud_{func_name}()" class="cloud-btn">Regenerate Layout</button>
        <span style="color: #6B7280; font-size: 12px;">
            Hover over words to see document counts. Click "Regenerate" for a new arrangement.
        </span>
    </div>

    <div style="position: relative; width: 100%; max-width: {width}px; margin: 0 auto;">
        <canvas id="{container_id}" width="{width}" height="{height}" style="display: block; max-width: 100%; height: auto;"></canvas>
    </div>

    <div id="{container_id}-tooltip" style="
        position: fixed;
        background: #1F2937;
        color: white;
        padding: 6px 10px;
        border-radius: 4px;
        font-size: 12px;
        pointer-events: none;
        opacity: 0;
        transition: opacity 0.15s;
        z-index: 1000;
    "></div>
</div>

<style>
.cloud-btn {{
    padding: 6px 12px;
    background: #E5E7EB;
    color: #374151;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}}
.cloud-btn:hover {{
    background: #D1D5DB;
}}
</style>

<script src="{WORDCLOUD2_CDN}"></script>

<script>
(function() {{
    const wordList = {word_list_json};
    const wordCounts = {word_counts_json};
    const colors = {colors_json};
    const canvas = document.getElementById('{container_id}');
    const tooltip = document.getElementById('{container_id}-tooltip');

    function getColor(word, weight, fontSize, distance, theta) {{
        return colors[Math.floor(Math.random() * colors.length)];
    }}

    function drawCloud() {{
        WordCloud(canvas, {{
            list: wordList,
            gridSize: 8,
            weightFactor: 1,
            fontFamily: 'Arial, sans-serif',
            color: getColor,
            rotateRatio: 0.3,
            rotationSteps: 2,
            backgroundColor: '#FAFAFA',
            shuffle: true,
            hover: function(item, dimension, event) {{
                if (item) {{
                    const word = item[0];
                    const count = wordCounts[word] || 0;
                    tooltip.textContent = word + ': ' + count + ' documents';
                    tooltip.style.opacity = '1';
                    tooltip.style.left = (event.clientX + 10) + 'px';
                    tooltip.style.top = (event.clientY + 10) + 'px';
                }} else {{
                    tooltip.style.opacity = '0';
                }}
            }}
        }});
    }}

    // Initial draw
    drawCloud();

    // Regenerate function
    window.regenerateCloud_{func_name} = function() {{
        drawCloud();
    }};

    // Hide tooltip when leaving canvas
    canvas.addEventListener('mouseleave', function() {{
        tooltip.style.opacity = '0';
    }});
}})();
</script>
'''
    return html


def generate_keyword_bar_chart(
    keyword_count: Counter,
    container_id: str = "keyword-bars",
    height: str = "500px",
    max_keywords: int = 25,
) -> str:
    """
    Generate a horizontal bar chart for keywords (alternative to word cloud).

    Args:
        keyword_count: Counter of keyword frequencies
        container_id: HTML element ID
        height: CSS height
        max_keywords: Maximum keywords to show

    Returns:
        HTML string with embedded JavaScript
    """
    top_keywords = keyword_count.most_common(max_keywords)

    if not top_keywords:
        return "<p><em>No keyword data available</em></p>"

    labels = [k[0] for k in top_keywords]
    data = [k[1] for k in top_keywords]

    labels_json = json.dumps(labels)
    data_json = json.dumps(data)

    html = f'''
<div style="position: relative; height: {height}; width: 100%; max-width: 100%; overflow: hidden;">
    <canvas id="{container_id}"></canvas>
</div>

<script>
(function() {{
    const ctx = document.getElementById('{container_id}').getContext('2d');
    new Chart(ctx, {{
        type: 'bar',
        data: {{
            labels: {labels_json},
            datasets: [{{
                label: 'Documents',
                data: {data_json},
                backgroundColor: '#3B82F699',
                borderColor: '#3B82F6',
                borderWidth: 1
            }}]
        }},
        options: {{
            indexAxis: 'y',
            responsive: true,
            maintainAspectRatio: false,
            plugins: {{
                title: {{
                    display: true,
                    text: 'Top Keywords by Document Frequency',
                    font: {{ size: 14 }}
                }},
                legend: {{
                    display: false
                }}
            }},
            scales: {{
                x: {{
                    beginAtZero: true,
                    title: {{
                        display: true,
                        text: 'Number of Documents'
                    }}
                }}
            }}
        }}
    }});
}})();
</script>
'''
    return html
