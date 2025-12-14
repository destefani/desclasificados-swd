"""Unit tests for app.visualizations.financial_dashboard module."""

import pytest
from collections import Counter

from app.visualizations.financial_dashboard import (
    prepare_financial_timeline_data,
    build_financial_flow_network,
    generate_financial_summary_cards,
    generate_financial_timeline,
    generate_financial_flow_network,
    generate_financial_purposes_chart,
    generate_financial_actors_chart,
    FINANCIAL_COLORS,
    PURPOSE_COLORS,
)


class TestPrepareFinancialTimelineData:
    """Tests for prepare_financial_timeline_data function."""

    def test_empty_data(self):
        """Should handle empty input."""
        result = prepare_financial_timeline_data({})
        assert result["labels"] == []
        assert result["datasets"] == []

    def test_aggregates_by_year(self):
        """Should sum normalized_usd by year."""
        data = {
            "1970": [
                {"normalized_usd": 1000000},
                {"normalized_usd": 500000},
            ],
            "1971": [
                {"normalized_usd": 2000000},
            ],
        }
        result = prepare_financial_timeline_data(data)
        assert "1970" in result["labels"]
        assert "1971" in result["labels"]
        # First dataset should have USD totals
        assert result["datasets"][0]["label"] == "Total USD"
        # Check 1970 total is 1.5M
        idx_1970 = result["labels"].index("1970")
        assert result["datasets"][0]["data"][idx_1970] == 1500000

    def test_handles_null_amounts(self):
        """Should count documents with null normalized_usd."""
        data = {
            "1970": [
                {"normalized_usd": None, "value": "unknown"},
                {"normalized_usd": 1000000},
            ],
        }
        result = prepare_financial_timeline_data(data)
        # Should have both USD dataset and unknown dataset
        assert len(result["datasets"]) == 2
        # Check unknown count for 1970
        idx_1970 = result["labels"].index("1970")
        assert result["datasets"][1]["data"][idx_1970] == 1  # 1 unknown

    def test_excludes_unknown_year(self):
        """Should exclude 'Unknown' year from timeline."""
        data = {
            "1970": [{"normalized_usd": 1000000}],
            "Unknown": [{"normalized_usd": 500000}],
        }
        result = prepare_financial_timeline_data(data)
        assert "Unknown" not in result["labels"]
        assert "1970" in result["labels"]

    def test_sorts_years_chronologically(self):
        """Should sort years in chronological order."""
        data = {
            "1975": [{"normalized_usd": 100}],
            "1970": [{"normalized_usd": 100}],
            "1973": [{"normalized_usd": 100}],
        }
        result = prepare_financial_timeline_data(data)
        assert result["labels"] == ["1970", "1973", "1975"]


class TestBuildFinancialFlowNetwork:
    """Tests for build_financial_flow_network function."""

    def test_creates_bipartite_graph(self):
        """Should create nodes for actors and purposes."""
        actors = Counter({"CIA": 5, "STATE DEPT": 3})
        purposes = Counter({"POLITICAL ACTION": 4, "PROPAGANDA": 2})
        links = [
            {"actor": "CIA", "purpose": "POLITICAL ACTION", "doc_id": "1"},
            {"actor": "CIA", "purpose": "PROPAGANDA", "doc_id": "2"},
        ]

        result = build_financial_flow_network(actors, purposes, links)

        assert len(result["nodes"]) == 4  # 2 actors + 2 purposes
        assert len(result["edges"]) >= 2

    def test_empty_data(self):
        """Should handle empty input."""
        result = build_financial_flow_network(Counter(), Counter(), [])
        assert result["nodes"] == []
        assert result["edges"] == []

    def test_filters_by_min_mentions(self):
        """Should filter actors/purposes by minimum mentions."""
        actors = Counter({"CIA": 5, "MINOR_ACTOR": 1})
        purposes = Counter({"POLITICAL ACTION": 4})
        links = []

        result = build_financial_flow_network(
            actors, purposes, links, min_mentions=2
        )

        node_labels = [n["label"] for n in result["nodes"]]
        assert "CIA" in node_labels
        assert "MINOR_ACTOR" not in node_labels

    def test_limits_nodes(self):
        """Should limit total number of nodes."""
        actors = Counter({f"ACTOR_{i}": i for i in range(100)})
        purposes = Counter({f"PURPOSE_{i}": i for i in range(100)})
        links = []

        result = build_financial_flow_network(
            actors, purposes, links, max_nodes=10
        )

        # Should have at most 10 nodes total (actors + purposes)
        assert len(result["nodes"]) <= 10

    def test_edge_count_aggregation(self):
        """Should aggregate edge counts from multiple links."""
        actors = Counter({"CIA": 5})
        purposes = Counter({"POLITICAL ACTION": 5})
        links = [
            {"actor": "CIA", "purpose": "POLITICAL ACTION", "doc_id": "1"},
            {"actor": "CIA", "purpose": "POLITICAL ACTION", "doc_id": "2"},
            {"actor": "CIA", "purpose": "POLITICAL ACTION", "doc_id": "3"},
        ]

        result = build_financial_flow_network(actors, purposes, links)

        # Should have one edge with value 3
        assert len(result["edges"]) == 1
        assert result["edges"][0]["value"] == 3


class TestGenerateFinancialSummaryCards:
    """Tests for generate_financial_summary_cards function."""

    def test_returns_html(self):
        """Should return valid HTML string."""
        html = generate_financial_summary_cards(
            docs_with_financial=10,
            total_docs=100,
            financial_amounts=[{"normalized_usd": 1000}],
            financial_actors_count=Counter({"CIA": 5}),
            financial_purposes_count=Counter({"PROPAGANDA": 3}),
        )
        assert "<div" in html
        assert "10" in html  # docs count

    def test_formats_large_numbers(self):
        """Should format large USD amounts correctly."""
        html = generate_financial_summary_cards(
            docs_with_financial=10,
            total_docs=100,
            financial_amounts=[
                {"normalized_usd": 1000000},
                {"normalized_usd": 500000},
            ],
            financial_actors_count=Counter({"CIA": 5}),
            financial_purposes_count=Counter({"PROPAGANDA": 3}),
        )
        # Should contain formatted amount like $1.5M
        assert "$" in html

    def test_handles_zero_totals(self):
        """Should handle zero total docs without division error."""
        html = generate_financial_summary_cards(
            docs_with_financial=0,
            total_docs=0,
            financial_amounts=[],
            financial_actors_count=Counter(),
            financial_purposes_count=Counter(),
        )
        assert "0%" in html

    def test_shows_top_purpose(self):
        """Should show the most common purpose."""
        html = generate_financial_summary_cards(
            docs_with_financial=10,
            total_docs=100,
            financial_amounts=[],
            financial_actors_count=Counter({"CIA": 5}),
            financial_purposes_count=Counter({"PROPAGANDA": 5, "ELECTION SUPPORT": 3}),
        )
        assert "PROPAGANDA" in html


class TestGenerateFinancialTimeline:
    """Tests for generate_financial_timeline function."""

    def test_returns_html_with_chartjs(self):
        """Should return HTML with Chart.js script."""
        html = generate_financial_timeline(
            financial_amounts_by_year={"1970": [{"normalized_usd": 1000}]},
        )
        assert "Chart" in html
        assert "canvas" in html

    def test_empty_data_returns_message(self):
        """Should return message for empty data."""
        html = generate_financial_timeline(
            financial_amounts_by_year={},
        )
        assert "No financial timeline data available" in html

    def test_includes_container_id(self):
        """Should use the specified container ID."""
        html = generate_financial_timeline(
            financial_amounts_by_year={"1970": [{"normalized_usd": 1000}]},
            container_id="test-timeline",
        )
        assert 'id="test-timeline"' in html


class TestGenerateFinancialFlowNetwork:
    """Tests for generate_financial_flow_network function."""

    def test_returns_html_with_visjs(self):
        """Should return HTML with vis.js script."""
        html = generate_financial_flow_network(
            financial_actors_count=Counter({"CIA": 1}),
            financial_purposes_count=Counter({"PROPAGANDA": 1}),
            financial_actor_purpose_links=[
                {"actor": "CIA", "purpose": "PROPAGANDA", "doc_id": "1"}
            ],
        )
        assert "vis" in html.lower() or "network" in html.lower()

    def test_empty_data_returns_message(self):
        """Should return message for empty data."""
        html = generate_financial_flow_network(
            financial_actors_count=Counter(),
            financial_purposes_count=Counter(),
            financial_actor_purpose_links=[],
        )
        assert "No financial network data available" in html

    def test_includes_container_id(self):
        """Should use the specified container ID."""
        html = generate_financial_flow_network(
            financial_actors_count=Counter({"CIA": 1}),
            financial_purposes_count=Counter({"PROPAGANDA": 1}),
            financial_actor_purpose_links=[
                {"actor": "CIA", "purpose": "PROPAGANDA", "doc_id": "1"}
            ],
            container_id="test-network",
        )
        assert 'id="test-network"' in html


class TestGenerateFinancialPurposesChart:
    """Tests for generate_financial_purposes_chart function."""

    def test_returns_html_with_chartjs(self):
        """Should return HTML with Chart.js doughnut chart."""
        html = generate_financial_purposes_chart(
            financial_purposes_count=Counter({"PROPAGANDA": 5, "ELECTION SUPPORT": 3}),
        )
        assert "doughnut" in html
        assert "canvas" in html

    def test_empty_data_returns_message(self):
        """Should return message for empty data."""
        html = generate_financial_purposes_chart(
            financial_purposes_count=Counter(),
        )
        assert "No funding purpose data available" in html

    def test_includes_all_purposes(self):
        """Should include all purposes in the chart."""
        html = generate_financial_purposes_chart(
            financial_purposes_count=Counter({
                "PROPAGANDA": 5,
                "ELECTION SUPPORT": 3,
                "MEDIA FUNDING": 2,
            }),
        )
        assert "PROPAGANDA" in html
        assert "ELECTION SUPPORT" in html
        assert "MEDIA FUNDING" in html


class TestGenerateFinancialActorsChart:
    """Tests for generate_financial_actors_chart function."""

    def test_returns_html_with_chartjs(self):
        """Should return HTML with Chart.js horizontal bar chart."""
        html = generate_financial_actors_chart(
            financial_actors_count=Counter({"CIA": 10, "STATE DEPT": 5}),
        )
        assert "bar" in html
        assert "canvas" in html

    def test_empty_data_returns_message(self):
        """Should return message for empty data."""
        html = generate_financial_actors_chart(
            financial_actors_count=Counter(),
        )
        assert "No financial actor data available" in html

    def test_limits_items(self):
        """Should limit items to max_items parameter."""
        actors = Counter({f"ACTOR_{i}": i for i in range(50)})
        html = generate_financial_actors_chart(
            financial_actors_count=actors,
            max_items=5,
        )
        # Should only include top 5 actors
        assert "ACTOR_49" in html  # Highest count
        assert "ACTOR_48" in html
        # Lower count actors should not be in labels (they're filtered)


class TestColorConstants:
    """Tests for color constants."""

    def test_financial_colors_exist(self):
        """Should have primary financial colors defined."""
        assert "primary" in FINANCIAL_COLORS
        assert "secondary" in FINANCIAL_COLORS
        assert "accent" in FINANCIAL_COLORS
        assert "neutral" in FINANCIAL_COLORS

    def test_purpose_colors_exist(self):
        """Should have colors for all standard purposes."""
        expected_purposes = [
            "ELECTION SUPPORT",
            "OPPOSITION SUPPORT",
            "PROPAGANDA",
            "MEDIA FUNDING",
            "POLITICAL ACTION",
            "INTELLIGENCE OPERATIONS",
            "MILITARY AID",
            "ECONOMIC DESTABILIZATION",
            "LABOR UNION SUPPORT",
            "CIVIC ACTION",
            "OTHER",
        ]
        for purpose in expected_purposes:
            assert purpose in PURPOSE_COLORS
