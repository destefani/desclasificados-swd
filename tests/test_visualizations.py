"""Tests for the visualizations module."""
import json
from collections import Counter

import pytest

from app.visualizations.historical_events import (
    HISTORICAL_EVENTS,
    HistoricalEvent,
    get_events_for_year_range,
    get_major_events,
    events_to_json,
)
from app.visualizations.interactive_timeline import (
    prepare_timeline_data,
    prepare_event_annotations,
    generate_interactive_timeline,
    generate_timeline_with_monthly_detail,
    CLASSIFICATION_COLORS,
)
from app.visualizations.network_graph import (
    compute_cooccurrence,
    prepare_network_data,
    generate_network_graph,
    generate_people_network,
    generate_organization_network,
    NODE_COLORS,
)
from app.visualizations.geographic_map import (
    geocode_location,
    aggregate_locations,
    generate_geographic_map,
    get_detention_centers_from_docs,
    LOCATION_COORDS,
    COUNTRY_COORDS,
    DETENTION_CENTERS,
    OPERATION_CONDOR_COUNTRIES,
)
from app.visualizations.sensitive_content import (
    prepare_sensitive_timeline_data,
    generate_sensitive_timeline,
    build_perpetrator_victim_network,
    generate_perpetrator_victim_network,
    generate_incident_types_chart,
    generate_sensitive_summary_cards,
    SENSITIVE_COLORS,
)
from app.visualizations.keyword_cloud import (
    prepare_wordcloud_data,
    generate_keyword_cloud,
    generate_keyword_bar_chart,
    KEYWORD_COLORS,
)


class TestHistoricalEvents:
    """Tests for historical events database."""

    def test_historical_events_not_empty(self):
        """Verify HISTORICAL_EVENTS contains data."""
        assert len(HISTORICAL_EVENTS) > 0

    def test_historical_events_have_required_fields(self):
        """Verify each event has all required fields."""
        for event in HISTORICAL_EVENTS:
            assert isinstance(event, HistoricalEvent)
            assert event.date
            assert event.name
            assert event.description
            assert event.category in ("major", "moderate", "minor")
            assert event.period

    def test_historical_events_dates_are_valid(self):
        """Verify event dates are in ISO format YYYY-MM-DD."""
        import re
        date_pattern = re.compile(r"^\d{4}-\d{2}-\d{2}$")
        for event in HISTORICAL_EVENTS:
            assert date_pattern.match(event.date), f"Invalid date format: {event.date}"

    def test_major_events_include_key_dates(self):
        """Verify key historical dates are included as major events."""
        major_dates = [e.date for e in HISTORICAL_EVENTS if e.category == "major"]
        # The coup
        assert "1973-09-11" in major_dates
        # Letelier assassination
        assert "1976-09-21" in major_dates
        # Plebiscite
        assert "1988-10-05" in major_dates

    def test_get_events_for_year_range(self):
        """Test filtering events by year range."""
        events = get_events_for_year_range(1973, 1973)
        # Should include coup and caravan of death at minimum
        assert len(events) >= 2
        for event in events:
            year = int(event.date[:4])
            assert 1973 <= year <= 1973

    def test_get_events_for_year_range_empty(self):
        """Test year range with no events."""
        events = get_events_for_year_range(2020, 2025)
        assert len(events) == 0

    def test_get_major_events(self):
        """Test getting only major events."""
        major_events = get_major_events()
        assert len(major_events) > 0
        for event in major_events:
            assert event.category == "major"

    def test_events_to_json(self):
        """Test converting events to JSON-serializable format."""
        json_events = events_to_json()
        assert isinstance(json_events, list)
        assert len(json_events) == len(HISTORICAL_EVENTS)
        for event in json_events:
            assert "date" in event
            assert "name" in event
            assert "description" in event
            assert "category" in event
            assert "period" in event
        # Verify it's actually JSON serializable
        json_str = json.dumps(json_events)
        assert len(json_str) > 0


class TestPrepareTimelineData:
    """Tests for timeline data preparation."""

    def test_simple_timeline_data(self):
        """Test preparing simple timeline data without classification breakdown."""
        timeline_yearly = Counter({"1975": 10, "1976": 20, "1977": 15})
        data = prepare_timeline_data(timeline_yearly)

        assert "labels" in data
        assert "datasets" in data
        assert data["stacked"] is False
        assert data["labels"] == ["1975", "1976", "1977"]
        assert data["datasets"][0]["data"] == [10, 20, 15]

    def test_timeline_excludes_unknown(self):
        """Test that 'Unknown' years are excluded from labels."""
        timeline_yearly = Counter({"1975": 10, "Unknown": 5, "1976": 20})
        data = prepare_timeline_data(timeline_yearly)

        assert "Unknown" not in data["labels"]
        assert len(data["labels"]) == 2

    def test_stacked_timeline_data(self):
        """Test preparing stacked timeline data with classification breakdown."""
        timeline_yearly = Counter({"1975": 10, "1976": 20})
        classification_by_year = {
            "1975": Counter({"SECRET": 5, "UNCLASSIFIED": 5}),
            "1976": Counter({"SECRET": 10, "CONFIDENTIAL": 5, "UNCLASSIFIED": 5}),
        }
        data = prepare_timeline_data(timeline_yearly, classification_by_year=classification_by_year)

        assert data["stacked"] is True
        assert len(data["datasets"]) >= 2  # At least SECRET and UNCLASSIFIED


class TestPrepareEventAnnotations:
    """Tests for event annotation preparation."""

    def test_annotations_structure(self):
        """Test that annotations have correct structure."""
        annotations = prepare_event_annotations(major_only=False)

        assert len(annotations) == len(HISTORICAL_EVENTS)
        for ann in annotations:
            assert ann["type"] == "line"
            assert "xMin" in ann
            assert "xMax" in ann
            assert "borderColor" in ann
            assert "label" in ann

    def test_major_only_annotations(self):
        """Test filtering to only major events."""
        all_annotations = prepare_event_annotations(major_only=False)
        major_annotations = prepare_event_annotations(major_only=True)

        assert len(major_annotations) < len(all_annotations)


class TestGenerateInteractiveTimeline:
    """Tests for interactive timeline HTML generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        timeline_yearly = Counter({"1975": 10, "1976": 20})
        html = generate_interactive_timeline(timeline_yearly)

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<canvas" in html
        assert "<script" in html

    def test_includes_chartjs_cdns(self):
        """Test that Chart.js CDN scripts are included."""
        timeline_yearly = Counter({"1975": 10})
        html = generate_interactive_timeline(timeline_yearly)

        assert "chart.js" in html.lower()
        assert "chartjs-plugin-zoom" in html.lower()
        assert "chartjs-plugin-annotation" in html.lower()

    def test_custom_container_id(self):
        """Test using custom container ID."""
        timeline_yearly = Counter({"1975": 10})
        html = generate_interactive_timeline(timeline_yearly, container_id="my-custom-chart")

        assert 'id="my-custom-chart"' in html
        assert "resetZoom_my_custom_chart" in html

    def test_without_events(self):
        """Test generating timeline without event annotations."""
        timeline_yearly = Counter({"1975": 10})
        html = generate_interactive_timeline(timeline_yearly, include_events=False)

        assert "annotations" in html
        # Annotations object should be empty (JavaScript const declaration)
        assert "const annotations = {};" in html

    def test_with_classification_breakdown(self):
        """Test timeline with classification breakdown."""
        timeline_yearly = Counter({"1975": 10, "1976": 20})
        classification_by_year = {
            "1975": Counter({"SECRET": 5, "UNCLASSIFIED": 5}),
            "1976": Counter({"SECRET": 10, "UNCLASSIFIED": 10}),
        }
        html = generate_interactive_timeline(
            timeline_yearly,
            classification_by_year=classification_by_year
        )

        assert "SECRET" in html
        assert "UNCLASSIFIED" in html
        assert "stacked: true" in html.lower() or '"stacked": true' in html.lower()


class TestGenerateTimelineWithMonthlyDetail:
    """Tests for timeline with monthly detail toggle."""

    def test_generates_html_with_toggle(self):
        """Test that monthly toggle buttons are generated."""
        timeline_yearly = Counter({"1975": 10})
        timeline_monthly = Counter({"1975-01": 3, "1975-02": 7})

        html = generate_timeline_with_monthly_detail(
            timeline_yearly,
            timeline_monthly,
        )

        assert "Yearly" in html
        assert "Monthly" in html
        assert "showYearly" in html
        assert "showMonthly" in html

    def test_includes_both_datasets(self):
        """Test that both yearly and monthly data are included."""
        timeline_yearly = Counter({"1975": 10, "1976": 20})
        timeline_monthly = Counter({"1975-01": 3, "1975-02": 7, "1976-01": 10, "1976-02": 10})

        html = generate_timeline_with_monthly_detail(
            timeline_yearly,
            timeline_monthly,
        )

        assert "yearlyData" in html
        assert "monthlyData" in html
        assert "1975" in html
        assert "1975-01" in html


class TestClassificationColors:
    """Tests for classification color constants."""

    def test_all_classifications_have_colors(self):
        """Verify all standard classifications have assigned colors."""
        required = ["TOP SECRET", "SECRET", "CONFIDENTIAL", "UNCLASSIFIED"]
        for classification in required:
            assert classification in CLASSIFICATION_COLORS
            assert CLASSIFICATION_COLORS[classification].startswith("#")


class TestIntegration:
    """Integration tests for visualization in reports."""

    def test_classification_by_year_in_process_documents(self):
        """Test that classification_by_year is returned by process_documents."""
        import tempfile
        import os
        from app.analyze_documents import process_documents

        # Create a temp directory with a sample transcript
        with tempfile.TemporaryDirectory() as tmpdir:
            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "classification_level": "SECRET",
                    "document_type": "TELEGRAM",
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(tmpdir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(tmpdir)

            assert "classification_by_year" in results
            assert "1976" in results["classification_by_year"]
            assert results["classification_by_year"]["1976"]["SECRET"] == 1

    def test_full_report_includes_interactive_timeline(self):
        """Test that full report includes interactive timeline HTML."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "classification_level": "SECRET",
                    "document_type": "TELEGRAM",
                    "page_count": 1,
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(transcripts_dir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir)

            report_path = os.path.join(tmpdir, "report_full.html")
            assert os.path.exists(report_path)

            with open(report_path, "r") as f:
                content = f.read()

            # Check for interactive timeline elements
            assert "chart.js" in content.lower()
            assert "timeline-chart-full" in content
            assert "Yearly" in content
            assert "Monthly" in content


class TestComputeCooccurrence:
    """Tests for co-occurrence computation."""

    def test_counts_entity_frequency(self):
        """Test that entity frequencies are correctly counted."""
        documents = [
            {"metadata": {"document_id": "doc1", "people_mentioned": ["PERSON A", "PERSON B"]}},
            {"metadata": {"document_id": "doc2", "people_mentioned": ["PERSON A", "PERSON C"]}},
            {"metadata": {"document_id": "doc3", "people_mentioned": ["PERSON A"]}},
        ]
        entity_count, _ = compute_cooccurrence(documents, field="people_mentioned", min_occurrences=1)

        assert entity_count["PERSON A"] == 3
        assert entity_count["PERSON B"] == 1
        assert entity_count["PERSON C"] == 1

    def test_filters_by_min_occurrences(self):
        """Test filtering entities by minimum occurrences."""
        documents = [
            {"metadata": {"document_id": "doc1", "people_mentioned": ["PERSON A", "PERSON B"]}},
            {"metadata": {"document_id": "doc2", "people_mentioned": ["PERSON A"]}},
        ]
        entity_count, _ = compute_cooccurrence(documents, field="people_mentioned", min_occurrences=2)

        assert "PERSON A" in entity_count
        assert "PERSON B" not in entity_count

    def test_computes_cooccurrence_pairs(self):
        """Test that co-occurrence pairs are correctly computed."""
        documents = [
            {"metadata": {"document_id": "doc1", "people_mentioned": ["PERSON A", "PERSON B"]}},
            {"metadata": {"document_id": "doc2", "people_mentioned": ["PERSON A", "PERSON B"]}},
        ]
        entity_count, cooccurrence = compute_cooccurrence(documents, field="people_mentioned", min_occurrences=1)

        pair = tuple(sorted(["PERSON A", "PERSON B"]))
        assert pair in cooccurrence
        assert len(cooccurrence[pair]) == 2  # Both documents

    def test_handles_empty_documents(self):
        """Test handling of empty document list."""
        entity_count, cooccurrence = compute_cooccurrence([], field="people_mentioned")

        assert len(entity_count) == 0
        assert len(cooccurrence) == 0


class TestPrepareNetworkData:
    """Tests for network data preparation."""

    def test_creates_nodes(self):
        """Test that nodes are created for entities."""
        entity_count = Counter({"PERSON A": 10, "PERSON B": 5})
        cooccurrence = {("PERSON A", "PERSON B"): ["doc1", "doc2"]}

        data = prepare_network_data(entity_count, cooccurrence, max_nodes=10)

        assert "nodes" in data
        assert len(data["nodes"]) == 2
        labels = [n["label"] for n in data["nodes"]]
        assert "PERSON A" in labels
        assert "PERSON B" in labels

    def test_creates_edges(self):
        """Test that edges are created for co-occurrences."""
        entity_count = Counter({"PERSON A": 10, "PERSON B": 5})
        cooccurrence = {("PERSON A", "PERSON B"): ["doc1", "doc2"]}

        data = prepare_network_data(entity_count, cooccurrence, max_nodes=10, min_edge_weight=1)

        assert "edges" in data
        assert len(data["edges"]) == 1
        assert data["edges"][0]["value"] == 2

    def test_limits_nodes(self):
        """Test that max_nodes parameter limits output."""
        entity_count = Counter({f"PERSON {i}": 10 - i for i in range(10)})
        cooccurrence = {}

        data = prepare_network_data(entity_count, cooccurrence, max_nodes=5)

        assert len(data["nodes"]) == 5

    def test_filters_edges_by_weight(self):
        """Test that min_edge_weight filters weak edges."""
        entity_count = Counter({"PERSON A": 10, "PERSON B": 5})
        cooccurrence = {("PERSON A", "PERSON B"): ["doc1"]}  # Only 1 shared doc

        data = prepare_network_data(entity_count, cooccurrence, max_nodes=10, min_edge_weight=2)

        assert len(data["edges"]) == 0  # Edge should be filtered out


class TestGenerateNetworkGraph:
    """Tests for network graph HTML generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        entity_count = Counter({"PERSON A": 10, "PERSON B": 5})
        cooccurrence = {("PERSON A", "PERSON B"): ["doc1", "doc2"]}

        html = generate_network_graph(entity_count, cooccurrence)

        assert isinstance(html, str)
        assert len(html) > 0
        assert "vis-network" in html.lower()

    def test_includes_visjs_cdn(self):
        """Test that vis.js CDN script is included."""
        entity_count = Counter({"PERSON A": 10})
        cooccurrence = {}

        html = generate_network_graph(entity_count, cooccurrence)

        assert "unpkg.com/vis-network" in html

    def test_custom_container_id(self):
        """Test using custom container ID."""
        entity_count = Counter({"PERSON A": 10})
        cooccurrence = {}

        html = generate_network_graph(entity_count, cooccurrence, container_id="my-network")

        assert 'id="my-network"' in html
        assert "resetNetwork_my_network" in html

    def test_includes_node_data(self):
        """Test that node data is included in the output."""
        entity_count = Counter({"PERSON A": 10, "PERSON B": 5})
        cooccurrence = {}

        html = generate_network_graph(entity_count, cooccurrence)

        assert "PERSON A" in html
        assert "PERSON B" in html


class TestGeneratePeopleNetwork:
    """Tests for people network generation."""

    def test_generates_people_network(self):
        """Test generating network from document data."""
        documents = [
            {"metadata": {"document_id": "doc1", "people_mentioned": ["PERSON A", "PERSON B"]}},
            {"metadata": {"document_id": "doc2", "people_mentioned": ["PERSON A", "PERSON B"]}},
            {"metadata": {"document_id": "doc3", "people_mentioned": ["PERSON A", "PERSON B", "PERSON C"]}},
        ]

        html = generate_people_network(documents, min_occurrences=2)

        assert "vis-network" in html.lower()
        assert "PERSON A" in html
        assert "PERSON B" in html


class TestGenerateOrganizationNetwork:
    """Tests for organization network generation."""

    def test_generates_org_network(self):
        """Test generating network from organization data."""
        documents = [
            {"metadata": {
                "document_id": "doc1",
                "organizations_mentioned": [
                    {"name": "CIA", "type": "GOVERNMENT"},
                    {"name": "DINA", "type": "GOVERNMENT"}
                ]
            }},
            {"metadata": {
                "document_id": "doc2",
                "organizations_mentioned": [
                    {"name": "CIA", "type": "GOVERNMENT"},
                    {"name": "DINA", "type": "GOVERNMENT"}
                ]
            }},
            {"metadata": {
                "document_id": "doc3",
                "organizations_mentioned": [
                    {"name": "CIA", "type": "GOVERNMENT"}
                ]
            }},
        ]

        html = generate_organization_network(documents, min_occurrences=2)

        assert "vis-network" in html.lower()
        assert "CIA" in html
        assert "DINA" in html


class TestNodeColors:
    """Tests for node color constants."""

    def test_required_colors_exist(self):
        """Verify required node colors are defined."""
        required = ["high_frequency", "medium_frequency", "low_frequency", "default"]
        for color_name in required:
            assert color_name in NODE_COLORS
            assert NODE_COLORS[color_name].startswith("#")


class TestNetworkIntegration:
    """Integration tests for network graphs in full reports."""

    def test_full_report_includes_network_graphs(self):
        """Test that full report includes network graph sections."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            # Create documents with people and organizations
            for i in range(3):
                sample_doc = {
                    "metadata": {
                        "document_id": f"TEST{i:03d}",
                        "document_date": "1976-09-21",
                        "classification_level": "SECRET",
                        "document_type": "TELEGRAM",
                        "page_count": 1,
                        "people_mentioned": ["PERSON A", "PERSON B"],
                        "organizations_mentioned": [{"name": "CIA", "type": "GOVERNMENT"}],
                    },
                    "confidence": {"overall": 0.9, "concerns": []},
                }
                with open(os.path.join(transcripts_dir, f"test{i}.json"), "w") as f:
                    json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir)

            report_path = os.path.join(tmpdir, "report_full.html")
            with open(report_path, "r") as f:
                content = f.read()

            # Check for network graph elements
            assert "vis-network" in content.lower()
            assert "people-network-full" in content
            assert "org-network-full" in content
            assert "People Network" in content
            assert "Organization Network" in content


# ============================================================================
# Geographic Map Tests
# ============================================================================


class TestLocationCoords:
    """Tests for location coordinate data."""

    def test_location_coords_not_empty(self):
        """Verify LOCATION_COORDS contains data."""
        assert len(LOCATION_COORDS) > 0

    def test_chile_cities_included(self):
        """Verify major Chilean cities are included."""
        chile_cities = ["SANTIAGO", "VALPARAISO", "CONCEPCION", "ANTOFAGASTA", "TEMUCO"]
        for city in chile_cities:
            assert city in LOCATION_COORDS, f"Missing Chilean city: {city}"

    def test_coords_are_valid_tuples(self):
        """Verify all coordinates are (lat, lon) tuples with valid ranges."""
        for name, coords in LOCATION_COORDS.items():
            assert isinstance(coords, tuple), f"Invalid coord type for {name}"
            assert len(coords) == 2, f"Invalid coord length for {name}"
            lat, lon = coords
            assert -90 <= lat <= 90, f"Invalid latitude for {name}: {lat}"
            assert -180 <= lon <= 180, f"Invalid longitude for {name}: {lon}"

    def test_detention_centers_have_coords(self):
        """Verify known detention centers have coordinates."""
        detention_sites = ["VILLA GRIMALDI", "ESTADIO NACIONAL", "COLONIA DIGNIDAD"]
        for site in detention_sites:
            assert site in LOCATION_COORDS, f"Missing detention center: {site}"


class TestCountryCoords:
    """Tests for country coordinate data."""

    def test_operation_condor_countries_have_coords(self):
        """Verify all Operation Condor countries have coordinates."""
        for country in OPERATION_CONDOR_COUNTRIES:
            assert country in COUNTRY_COORDS, f"Missing country: {country}"

    def test_country_coords_are_valid(self):
        """Verify country coordinates are valid."""
        for name, coords in COUNTRY_COORDS.items():
            assert isinstance(coords, tuple)
            lat, lon = coords
            assert -90 <= lat <= 90
            assert -180 <= lon <= 180


class TestDetentionCenters:
    """Tests for detention center data."""

    def test_detention_centers_not_empty(self):
        """Verify detention centers list contains data."""
        assert len(DETENTION_CENTERS) > 0

    def test_detention_centers_have_required_fields(self):
        """Verify each detention center has required fields."""
        required_fields = ["name", "coords", "city", "description", "type"]
        for center in DETENTION_CENTERS:
            for field in required_fields:
                assert field in center, f"Missing field '{field}' in {center.get('name', 'unknown')}"

    def test_detention_center_types(self):
        """Verify detention center types are valid."""
        valid_types = ["torture_center", "detention", "prison_camp"]
        for center in DETENTION_CENTERS:
            assert center["type"] in valid_types, f"Invalid type for {center['name']}: {center['type']}"

    def test_known_centers_included(self):
        """Verify infamous detention centers are included."""
        known_centers = ["Villa Grimaldi", "Londres 38", "Estadio Nacional", "Colonia Dignidad"]
        center_names = [c["name"] for c in DETENTION_CENTERS]
        for center in known_centers:
            assert center in center_names, f"Missing known center: {center}"


class TestOperationCondorCountries:
    """Tests for Operation Condor country list."""

    def test_condor_countries_not_empty(self):
        """Verify Operation Condor countries list is not empty."""
        assert len(OPERATION_CONDOR_COUNTRIES) > 0

    def test_member_countries_included(self):
        """Verify the six founding members are included."""
        founding_members = ["CHILE", "ARGENTINA", "URUGUAY", "PARAGUAY", "BOLIVIA", "BRAZIL"]
        for country in founding_members:
            assert country in OPERATION_CONDOR_COUNTRIES


class TestGeocodeLocation:
    """Tests for geocode_location function."""

    def test_geocodes_exact_match(self):
        """Test geocoding with exact location name match."""
        coords = geocode_location("SANTIAGO")
        assert coords is not None
        assert isinstance(coords, tuple)
        assert len(coords) == 2

    def test_geocodes_case_insensitive(self):
        """Test that geocoding is case-insensitive."""
        coords1 = geocode_location("santiago")
        coords2 = geocode_location("SANTIAGO")
        coords3 = geocode_location("Santiago")
        assert coords1 == coords2 == coords3

    def test_returns_none_for_unknown(self):
        """Test that unknown locations return None."""
        coords = geocode_location("NONEXISTENT CITY XYZ")
        assert coords is None

    def test_geocodes_country(self):
        """Test geocoding country names."""
        coords = geocode_location("CHILE")
        assert coords is not None

    def test_partial_match(self):
        """Test partial matching for location names."""
        # "WASHINGTON D.C." contains "WASHINGTON"
        coords = geocode_location("WASHINGTON")
        assert coords is not None


class TestAggregateLocations:
    """Tests for aggregate_locations function."""

    def test_aggregates_cities(self):
        """Test aggregating city counts."""
        city_count = Counter({"SANTIAGO": 10, "VALPARAISO": 5})
        country_count = Counter()
        other_count = Counter()

        locations = aggregate_locations(city_count, country_count, other_count)

        assert len(locations) >= 2
        names = [loc["name"] for loc in locations]
        assert "SANTIAGO" in names
        assert "VALPARAISO" in names

    def test_includes_location_metadata(self):
        """Test that aggregated locations include required metadata."""
        city_count = Counter({"SANTIAGO": 10})
        locations = aggregate_locations(city_count, Counter(), Counter())

        if locations:
            loc = locations[0]
            assert "name" in loc
            assert "count" in loc
            assert "lat" in loc
            assert "lon" in loc
            assert "type" in loc

    def test_excludes_unknown_locations(self):
        """Test that unknown locations are excluded."""
        city_count = Counter({"UNKNOWN PLACE XYZ": 10})
        locations = aggregate_locations(city_count, Counter(), Counter())

        assert len(locations) == 0

    def test_deduplicates_by_coords(self):
        """Test that locations with same coords are deduplicated."""
        # VALPARAISO and VALPARAÍSO have same coords
        city_count = Counter({"VALPARAISO": 5, "VALPARAÍSO": 3})
        locations = aggregate_locations(city_count, Counter(), Counter())

        # Should only have one entry
        assert len(locations) == 1


class TestGetDetentionCentersFromDocs:
    """Tests for get_detention_centers_from_docs function."""

    def test_matches_detention_centers(self):
        """Test matching document mentions to known centers."""
        doc_centers = Counter({"Villa Grimaldi": 5, "Estadio Nacional": 3})
        centers = get_detention_centers_from_docs(doc_centers)

        # Should have all known centers
        assert len(centers) == len(DETENTION_CENTERS)

        # Check that matching centers have doc_count > 0
        villa_grimaldi = next(c for c in centers if c["name"] == "Villa Grimaldi")
        assert villa_grimaldi["doc_count"] == 5

    def test_returns_all_centers(self):
        """Test that all known centers are returned even without matches."""
        doc_centers = Counter()
        centers = get_detention_centers_from_docs(doc_centers)

        assert len(centers) == len(DETENTION_CENTERS)

    def test_centers_have_doc_count(self):
        """Test that all returned centers have doc_count field."""
        doc_centers = Counter({"Villa Grimaldi": 5})
        centers = get_detention_centers_from_docs(doc_centers)

        for center in centers:
            assert "doc_count" in center


class TestGenerateGeographicMap:
    """Tests for generate_geographic_map function."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        city_count = Counter({"SANTIAGO": 10})
        country_count = Counter({"CHILE": 50})

        html = generate_geographic_map(city_count, country_count)

        assert isinstance(html, str)
        assert len(html) > 0
        assert "leaflet" in html.lower()

    def test_includes_leaflet_cdn(self):
        """Test that Leaflet CDN scripts are included."""
        html = generate_geographic_map(Counter(), Counter())

        assert "unpkg.com/leaflet" in html
        assert "leaflet.css" in html.lower()
        assert "leaflet.js" in html.lower()

    def test_custom_container_id(self):
        """Test using custom container ID."""
        html = generate_geographic_map(Counter(), Counter(), container_id="my-map")

        assert 'id="my-map"' in html
        assert "resetMap_my_map" in html

    def test_includes_location_data(self):
        """Test that location data is included in output."""
        city_count = Counter({"SANTIAGO": 10})
        html = generate_geographic_map(city_count, Counter())

        assert "SANTIAGO" in html
        # Should have document mentions text
        assert "document" in html.lower()

    def test_includes_detention_centers(self):
        """Test that detention centers are included when enabled."""
        html = generate_geographic_map(
            Counter(), Counter(),
            torture_detention_centers=Counter({"Villa Grimaldi": 5}),
            show_detention_centers=True
        )

        assert "Villa Grimaldi" in html
        assert "detentionLayer" in html

    def test_includes_condor_countries(self):
        """Test that Operation Condor countries are highlighted."""
        html = generate_geographic_map(Counter(), Counter(), show_condor_countries=True)

        assert "condorLayer" in html
        assert "CHILE" in html
        assert "ARGENTINA" in html

    def test_layer_toggle_controls(self):
        """Test that layer toggle controls are included."""
        html = generate_geographic_map(Counter(), Counter())

        assert "checkbox" in html.lower()
        assert "Document Locations" in html
        assert "Detention Centers" in html
        assert "Operation Condor" in html

    def test_legend_included(self):
        """Test that map legend is included."""
        html = generate_geographic_map(Counter(), Counter())

        assert "legend" in html.lower() or "map-legend" in html


class TestGeographicMapIntegration:
    """Integration tests for geographic map in full reports."""

    def test_full_report_includes_geographic_map(self):
        """Test that full report includes geographic map section."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            # Create documents with location data
            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "classification_level": "SECRET",
                    "document_type": "TELEGRAM",
                    "page_count": 1,
                    "city": ["SANTIAGO", "VALPARAISO"],
                    "country": ["CHILE"],
                    "torture_references": {
                        "has_torture_content": True,
                        "detention_centers": ["Villa Grimaldi"],
                        "methods_mentioned": [],
                        "victims": [],
                        "perpetrators": [],
                    },
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(transcripts_dir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir)

            report_path = os.path.join(tmpdir, "report_full.html")
            with open(report_path, "r") as f:
                content = f.read()

            # Check for geographic map elements
            assert "leaflet" in content.lower()
            assert "geographic-map-full" in content
            assert "Geographic Map" in content

    def test_process_documents_collects_location_data(self):
        """Test that process_documents collects location data."""
        import tempfile
        import os
        from app.analyze_documents import process_documents

        with tempfile.TemporaryDirectory() as tmpdir:
            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "city": ["SANTIAGO", "VALPARAISO"],
                    "country": ["CHILE", "ARGENTINA"],
                    "other_place": ["Moneda Palace"],
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(tmpdir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(tmpdir)

            assert "city_count" in results
            assert "country_count" in results
            assert "other_place_count" in results
            assert results["city_count"]["SANTIAGO"] == 1
            assert results["country_count"]["CHILE"] == 1


# ============================================================================
# Sensitive Content Dashboard Tests
# ============================================================================


class TestSensitiveColors:
    """Tests for sensitive content color constants."""

    def test_required_colors_exist(self):
        """Verify required sensitive content colors are defined."""
        required = ["violence", "torture", "disappearance"]
        for color_name in required:
            assert color_name in SENSITIVE_COLORS
            assert SENSITIVE_COLORS[color_name].startswith("#")


class TestPrepareSensitiveTimelineData:
    """Tests for sensitive timeline data preparation."""

    def test_prepares_timeline_data(self):
        """Test preparing timeline data from yearly sensitive content."""
        sensitive_by_year = {
            "1975": {"violence": 10, "torture": 5, "disappearance": 3},
            "1976": {"violence": 20, "torture": 15, "disappearance": 8},
        }
        data = prepare_sensitive_timeline_data(sensitive_by_year)

        assert "labels" in data
        assert "datasets" in data
        assert data["labels"] == ["1975", "1976"]
        assert len(data["datasets"]) == 3  # violence, torture, disappearance

    def test_excludes_unknown_years(self):
        """Test that Unknown years are excluded."""
        sensitive_by_year = {
            "1975": {"violence": 10, "torture": 5, "disappearance": 3},
            "Unknown": {"violence": 5, "torture": 2, "disappearance": 1},
        }
        data = prepare_sensitive_timeline_data(sensitive_by_year)

        assert "Unknown" not in data["labels"]
        assert len(data["labels"]) == 1

    def test_handles_empty_data(self):
        """Test handling of empty data."""
        data = prepare_sensitive_timeline_data({})

        assert data["labels"] == []
        assert data["datasets"] == []


class TestGenerateSensitiveTimeline:
    """Tests for sensitive timeline HTML generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        sensitive_by_year = {
            "1975": {"violence": 10, "torture": 5, "disappearance": 3},
        }
        html = generate_sensitive_timeline(sensitive_by_year)

        assert isinstance(html, str)
        assert len(html) > 0
        assert "new Chart(" in html
        assert "<canvas" in html

    def test_includes_legend(self):
        """Test that legend is included."""
        sensitive_by_year = {"1975": {"violence": 10, "torture": 5, "disappearance": 3}}
        html = generate_sensitive_timeline(sensitive_by_year)

        assert "Violence" in html
        assert "Torture" in html
        assert "Disappearance" in html

    def test_custom_container_id(self):
        """Test using custom container ID."""
        sensitive_by_year = {"1975": {"violence": 10, "torture": 5, "disappearance": 3}}
        html = generate_sensitive_timeline(sensitive_by_year, container_id="my-timeline")

        assert 'id="my-timeline"' in html

    def test_handles_empty_data(self):
        """Test handling of empty data."""
        html = generate_sensitive_timeline({})

        assert "No sensitive content data" in html


class TestBuildPerpVictimNetwork:
    """Tests for perpetrator-victim network building."""

    def test_builds_network_nodes(self):
        """Test that nodes are created for victims and perpetrators."""
        violence_victims = Counter({"VICTIM A": 5, "VICTIM B": 3})
        violence_perps = Counter({"PERP X": 4, "PERP Y": 2})

        network = build_perpetrator_victim_network(
            violence_victims=violence_victims,
            violence_perpetrators=violence_perps,
            torture_victims=Counter(),
            torture_perpetrators=Counter(),
            disappearance_victims=Counter(),
            disappearance_perpetrators=Counter(),
            min_mentions=1,
        )

        assert "nodes" in network
        assert len(network["nodes"]) == 4
        labels = [n["label"] for n in network["nodes"]]
        assert "VICTIM A" in labels
        assert "PERP X" in labels

    def test_identifies_roles(self):
        """Test that roles are correctly identified."""
        violence_victims = Counter({"PERSON A": 5})
        violence_perps = Counter({"PERSON B": 4})

        network = build_perpetrator_victim_network(
            violence_victims=violence_victims,
            violence_perpetrators=violence_perps,
            torture_victims=Counter(),
            torture_perpetrators=Counter(),
            disappearance_victims=Counter(),
            disappearance_perpetrators=Counter(),
            min_mentions=1,
        )

        nodes_by_label = {n["label"]: n for n in network["nodes"]}
        assert nodes_by_label["PERSON A"]["role"] == "Victim"
        assert nodes_by_label["PERSON B"]["role"] == "Perpetrator"

    def test_identifies_dual_role(self):
        """Test that individuals in both roles are marked as 'Both'."""
        violence_victims = Counter({"PERSON A": 5})
        violence_perps = Counter({"PERSON A": 3})

        network = build_perpetrator_victim_network(
            violence_victims=violence_victims,
            violence_perpetrators=violence_perps,
            torture_victims=Counter(),
            torture_perpetrators=Counter(),
            disappearance_victims=Counter(),
            disappearance_perpetrators=Counter(),
            min_mentions=1,
        )

        nodes_by_label = {n["label"]: n for n in network["nodes"]}
        assert nodes_by_label["PERSON A"]["role"] == "Both"

    def test_filters_by_min_mentions(self):
        """Test filtering by minimum mentions."""
        violence_victims = Counter({"FREQUENT": 10, "RARE": 1})

        network = build_perpetrator_victim_network(
            violence_victims=violence_victims,
            violence_perpetrators=Counter(),
            torture_victims=Counter(),
            torture_perpetrators=Counter(),
            disappearance_victims=Counter(),
            disappearance_perpetrators=Counter(),
            min_mentions=5,
        )

        labels = [n["label"] for n in network["nodes"]]
        assert "FREQUENT" in labels
        assert "RARE" not in labels


class TestGeneratePerpVictimNetwork:
    """Tests for perpetrator-victim network HTML generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        html = generate_perpetrator_victim_network(
            violence_victims=Counter({"VICTIM A": 5}),
            violence_perpetrators=Counter({"PERP X": 4}),
            torture_victims=Counter(),
            torture_perpetrators=Counter(),
            disappearance_victims=Counter(),
            disappearance_perpetrators=Counter(),
            min_mentions=1,
        )

        assert isinstance(html, str)
        assert "vis-network" in html.lower()

    def test_includes_legend(self):
        """Test that legend is included."""
        html = generate_perpetrator_victim_network(
            violence_victims=Counter({"VICTIM A": 5}),
            violence_perpetrators=Counter({"PERP X": 4}),
            torture_victims=Counter(),
            torture_perpetrators=Counter(),
            disappearance_victims=Counter(),
            disappearance_perpetrators=Counter(),
            min_mentions=1,
        )

        assert "Perpetrator" in html
        assert "Victim" in html
        assert "Both" in html

    def test_handles_empty_data(self):
        """Test handling of empty data."""
        html = generate_perpetrator_victim_network(
            violence_victims=Counter(),
            violence_perpetrators=Counter(),
            torture_victims=Counter(),
            torture_perpetrators=Counter(),
            disappearance_victims=Counter(),
            disappearance_perpetrators=Counter(),
        )

        assert "No perpetrator-victim" in html


class TestGenerateIncidentTypesChart:
    """Tests for incident types chart generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        html = generate_incident_types_chart(
            violence_incident_types=Counter({"EXECUTION": 10, "ASSASSINATION": 5}),
            torture_methods=Counter({"ELECTRIC SHOCK": 8, "BEATING": 6}),
        )

        assert isinstance(html, str)
        assert "new Chart(" in html
        assert "<canvas" in html

    def test_includes_both_charts(self):
        """Test that both incident types and methods charts are included."""
        html = generate_incident_types_chart(
            violence_incident_types=Counter({"EXECUTION": 10}),
            torture_methods=Counter({"ELECTRIC SHOCK": 8}),
        )

        assert "Violence Incident Types" in html
        assert "Torture Methods" in html

    def test_handles_empty_data(self):
        """Test handling of empty data."""
        html = generate_incident_types_chart(
            violence_incident_types=Counter(),
            torture_methods=Counter(),
        )

        assert "No incident type data" in html


class TestGenerateSensitiveSummaryCards:
    """Tests for sensitive summary cards generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        html = generate_sensitive_summary_cards(
            docs_with_violence=100,
            docs_with_torture=50,
            docs_with_disappearance=25,
            total_docs=1000,
            violence_victims=Counter({"A": 1, "B": 2}),
            torture_victims=Counter({"C": 1}),
            disappearance_victims=Counter({"D": 1}),
            violence_perpetrators=Counter({"X": 1}),
            torture_perpetrators=Counter({"Y": 1}),
            disappearance_perpetrators=Counter({"Z": 1}),
        )

        assert isinstance(html, str)
        assert "100" in html  # violence count
        assert "50" in html   # torture count
        assert "25" in html   # disappearance count

    def test_includes_all_categories(self):
        """Test that all sensitive categories are shown."""
        html = generate_sensitive_summary_cards(
            docs_with_violence=100,
            docs_with_torture=50,
            docs_with_disappearance=25,
            total_docs=1000,
            violence_victims=Counter(),
            torture_victims=Counter(),
            disappearance_victims=Counter(),
            violence_perpetrators=Counter(),
            torture_perpetrators=Counter(),
            disappearance_perpetrators=Counter(),
        )

        assert "Violence" in html
        assert "Torture" in html
        assert "Disappearance" in html


class TestSensitiveContentIntegration:
    """Integration tests for sensitive content dashboard in full reports."""

    def test_process_documents_tracks_sensitive_by_year(self):
        """Test that process_documents tracks sensitive content by year."""
        import tempfile
        import os
        from app.analyze_documents import process_documents

        with tempfile.TemporaryDirectory() as tmpdir:
            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "violence_references": {
                        "has_violence_content": True,
                        "incident_types": ["EXECUTION"],
                        "victims": ["VICTIM A"],
                        "perpetrators": ["PERP X"],
                    },
                    "torture_references": {
                        "has_torture_content": True,
                        "detention_centers": [],
                        "methods_mentioned": ["ELECTRIC SHOCK"],
                        "victims": [],
                        "perpetrators": [],
                    },
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(tmpdir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(tmpdir)

            assert "sensitive_content_by_year" in results
            assert "1976" in results["sensitive_content_by_year"]
            assert results["sensitive_content_by_year"]["1976"]["violence"] == 1
            assert results["sensitive_content_by_year"]["1976"]["torture"] == 1

    def test_full_report_includes_sensitive_dashboard(self):
        """Test that full report includes sensitive content dashboard."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "classification_level": "SECRET",
                    "document_type": "TELEGRAM",
                    "page_count": 1,
                    "violence_references": {
                        "has_violence_content": True,
                        "incident_types": ["EXECUTION"],
                        "victims": ["VICTIM A"],
                        "perpetrators": ["PERP X"],
                    },
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(transcripts_dir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir)

            report_path = os.path.join(tmpdir, "report_full.html")
            with open(report_path, "r") as f:
                content = f.read()

            # Check for sensitive content dashboard elements
            assert "sensitive-dashboard" in content
            assert "Sensitive Content Dashboard" in content
            assert "sensitive-timeline-full" in content


# ============================================================================
# Keyword Cloud Tests
# ============================================================================


class TestKeywordColors:
    """Tests for keyword color constants."""

    def test_colors_not_empty(self):
        """Verify keyword colors list is not empty."""
        assert len(KEYWORD_COLORS) > 0

    def test_colors_are_valid_hex(self):
        """Verify all colors are valid hex codes."""
        for color in KEYWORD_COLORS:
            assert color.startswith("#")
            assert len(color) == 7


class TestPrepareWordcloudData:
    """Tests for wordcloud data preparation."""

    def test_prepares_word_list(self):
        """Test preparing word list from keyword counts."""
        keywords = Counter({"HUMAN RIGHTS": 50, "OPERATION CONDOR": 30, "COUP": 20})
        data = prepare_wordcloud_data(keywords, max_words=10, min_count=1)

        assert len(data) == 3
        # Each item should be [word, weight, count]
        assert len(data[0]) == 3
        words = [d[0] for d in data]
        assert "HUMAN RIGHTS" in words

    def test_filters_by_min_count(self):
        """Test filtering by minimum count."""
        keywords = Counter({"FREQUENT": 50, "RARE": 1})
        data = prepare_wordcloud_data(keywords, max_words=10, min_count=5)

        words = [d[0] for d in data]
        assert "FREQUENT" in words
        assert "RARE" not in words

    def test_limits_max_words(self):
        """Test limiting maximum words."""
        keywords = Counter({f"WORD{i}": 10 - i for i in range(20)})
        data = prepare_wordcloud_data(keywords, max_words=5, min_count=1)

        assert len(data) == 5

    def test_handles_empty_data(self):
        """Test handling of empty data."""
        data = prepare_wordcloud_data(Counter(), max_words=10, min_count=1)

        assert data == []

    def test_scales_weights(self):
        """Test that weights are scaled appropriately."""
        keywords = Counter({"HIGH": 100, "LOW": 10})
        data = prepare_wordcloud_data(keywords, max_words=10, min_count=1)

        # Higher frequency should have higher weight
        high_data = next(d for d in data if d[0] == "HIGH")
        low_data = next(d for d in data if d[0] == "LOW")
        assert high_data[1] > low_data[1]


class TestGenerateKeywordCloud:
    """Tests for keyword cloud HTML generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        keywords = Counter({"HUMAN RIGHTS": 50, "OPERATION CONDOR": 30})
        html = generate_keyword_cloud(keywords)

        assert isinstance(html, str)
        assert len(html) > 0
        assert "<canvas" in html
        assert "wordcloud" in html.lower()

    def test_includes_wordcloud2_cdn(self):
        """Test that wordcloud2.js CDN is included."""
        keywords = Counter({"HUMAN RIGHTS": 50})
        html = generate_keyword_cloud(keywords)

        assert "wordcloud" in html.lower()

    def test_custom_container_id(self):
        """Test using custom container ID."""
        keywords = Counter({"HUMAN RIGHTS": 50})
        html = generate_keyword_cloud(keywords, container_id="my-cloud")

        assert 'id="my-cloud"' in html

    def test_handles_empty_data(self):
        """Test handling of empty data."""
        html = generate_keyword_cloud(Counter())

        assert "No keyword data" in html

    def test_includes_tooltip(self):
        """Test that tooltip element is included."""
        keywords = Counter({"HUMAN RIGHTS": 50})
        html = generate_keyword_cloud(keywords)

        assert "tooltip" in html


class TestGenerateKeywordBarChart:
    """Tests for keyword bar chart generation."""

    def test_generates_html(self):
        """Test that function returns valid HTML."""
        keywords = Counter({"HUMAN RIGHTS": 50, "OPERATION CONDOR": 30})
        html = generate_keyword_bar_chart(keywords)

        assert isinstance(html, str)
        assert "new Chart(" in html
        assert "<canvas" in html

    def test_limits_keywords(self):
        """Test that max_keywords parameter limits output."""
        keywords = Counter({f"WORD{i}": 10 for i in range(50)})
        html = generate_keyword_bar_chart(keywords, max_keywords=10)

        # Should only include 10 keywords in data
        assert html.count('"WORD') <= 10

    def test_handles_empty_data(self):
        """Test handling of empty data."""
        html = generate_keyword_bar_chart(Counter())

        assert "No keyword data" in html


class TestKeywordCloudIntegration:
    """Integration tests for keyword cloud in full reports."""

    def test_full_report_includes_keyword_cloud(self):
        """Test that full report includes keyword cloud."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            # Create multiple documents so keywords appear more than once
            for i in range(3):
                sample_doc = {
                    "metadata": {
                        "document_id": f"TEST{i:03d}",
                        "document_date": "1976-09-21",
                        "classification_level": "SECRET",
                        "document_type": "TELEGRAM",
                        "page_count": 1,
                        "keywords": ["HUMAN RIGHTS", "OPERATION CONDOR", "POLITICAL REPRESSION"],
                    },
                    "confidence": {"overall": 0.9, "concerns": []},
                }
                with open(os.path.join(transcripts_dir, f"test{i}.json"), "w") as f:
                    json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir)

            report_path = os.path.join(tmpdir, "report_full.html")
            with open(report_path, "r") as f:
                content = f.read()

            # Check for keyword cloud elements
            assert "keyword-cloud-full" in content
            assert "wordcloud" in content.lower()


# =============================================================================
# PDF Viewer Tests
# =============================================================================

from app.visualizations.pdf_viewer import (
    generate_pdf_viewer_modal,
    generate_pdf_link_interceptor,
    PDFJS_CDN,
    PDFJS_WORKER_CDN,
)


class TestPdfJsCdnUrls:
    """Tests for PDF.js CDN URLs."""

    def test_pdfjs_cdn_url_format(self):
        """Test PDF.js CDN URL is valid."""
        assert PDFJS_CDN.startswith("https://")
        assert "pdf.js" in PDFJS_CDN.lower() or "pdf" in PDFJS_CDN.lower()

    def test_pdfjs_worker_cdn_url_format(self):
        """Test PDF.js worker CDN URL is valid."""
        assert PDFJS_WORKER_CDN.startswith("https://")
        assert "worker" in PDFJS_WORKER_CDN.lower()


class TestGeneratePdfViewerModal:
    """Tests for generate_pdf_viewer_modal function."""

    def test_returns_html_string(self):
        """Test function returns non-empty HTML string."""
        html = generate_pdf_viewer_modal()
        assert isinstance(html, str)
        assert len(html) > 0

    def test_contains_modal_element(self):
        """Test HTML contains modal container."""
        html = generate_pdf_viewer_modal()
        assert 'id="pdf-viewer-modal"' in html
        assert 'class="pdf-modal"' in html

    def test_contains_canvas(self):
        """Test HTML contains PDF canvas element."""
        html = generate_pdf_viewer_modal()
        assert 'id="pdf-canvas"' in html
        assert "<canvas" in html

    def test_contains_pdfjs_script(self):
        """Test HTML includes PDF.js library."""
        html = generate_pdf_viewer_modal()
        assert PDFJS_CDN in html
        assert PDFJS_WORKER_CDN in html

    def test_contains_navigation_controls(self):
        """Test HTML contains page navigation controls."""
        html = generate_pdf_viewer_modal()
        assert "pdfPrevPage" in html
        assert "pdfNextPage" in html
        assert 'id="pdf-page-input"' in html
        assert 'id="pdf-total-pages"' in html

    def test_contains_zoom_controls(self):
        """Test HTML contains zoom controls."""
        html = generate_pdf_viewer_modal()
        assert "pdfZoomIn" in html
        assert "pdfZoomOut" in html
        assert "pdfFitWidth" in html
        assert 'id="pdf-zoom-level"' in html

    def test_contains_close_functionality(self):
        """Test HTML contains close button and escape handler."""
        html = generate_pdf_viewer_modal()
        assert "closePdfViewer" in html
        assert "Escape" in html

    def test_contains_open_function(self):
        """Test HTML exports openPdfViewer function."""
        html = generate_pdf_viewer_modal()
        assert "window.openPdfViewer" in html

    def test_contains_loading_state(self):
        """Test HTML contains loading indicator."""
        html = generate_pdf_viewer_modal()
        assert 'id="pdf-loading"' in html
        assert "Loading PDF" in html

    def test_contains_error_state(self):
        """Test HTML contains error state."""
        html = generate_pdf_viewer_modal()
        assert 'id="pdf-error"' in html
        assert "Failed to load PDF" in html

    def test_contains_styles(self):
        """Test HTML includes CSS styles."""
        html = generate_pdf_viewer_modal()
        assert "<style>" in html
        assert ".pdf-modal" in html
        assert ".pdf-btn" in html


class TestGeneratePdfLinkInterceptor:
    """Tests for generate_pdf_link_interceptor function."""

    def test_returns_script_string(self):
        """Test function returns JavaScript script."""
        js = generate_pdf_link_interceptor()
        assert isinstance(js, str)
        assert "<script>" in js
        assert "</script>" in js

    def test_intercepts_pdf_links(self):
        """Test script intercepts PDF links."""
        js = generate_pdf_link_interceptor()
        assert 'href$=".pdf"' in js
        assert "openPdfViewer" in js

    def test_prevents_default(self):
        """Test script prevents default link behavior."""
        js = generate_pdf_link_interceptor()
        assert "preventDefault" in js

    def test_checks_same_origin(self):
        """Test script only intercepts same-origin links."""
        js = generate_pdf_link_interceptor()
        assert "window.location.origin" in js


class TestPdfViewerIntegration:
    """Integration tests for PDF viewer in reports."""

    def test_serve_mode_includes_pdf_viewer(self):
        """Test that serve mode includes PDF viewer modal."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            # Create a sample document
            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "classification_level": "SECRET",
                    "document_type": "TELEGRAM",
                    "page_count": 1,
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(transcripts_dir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir, serve_mode=True)

            report_path = os.path.join(tmpdir, "report_full.html")
            with open(report_path, "r") as f:
                content = f.read()

            # Check for PDF viewer elements
            assert 'id="pdf-viewer-modal"' in content
            assert PDFJS_CDN in content
            assert "openPdfViewer" in content

    def test_serve_mode_uses_server_urls(self):
        """Test that serve mode generates /pdf/ URLs."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            # Create a sample document
            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "classification_level": "SECRET",
                    "document_type": "TELEGRAM",
                    "page_count": 1,
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(transcripts_dir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir, serve_mode=True)

            report_path = os.path.join(tmpdir, "report_full.html")
            with open(report_path, "r") as f:
                content = f.read()

            # Check for server URLs (not file://)
            assert 'href="/pdf/' in content
            assert 'file://' not in content

    def test_non_serve_mode_uses_file_urls(self):
        """Test that non-serve mode generates file:// URLs."""
        import tempfile
        import os
        from app.analyze_documents import process_documents, generate_full_html_report

        with tempfile.TemporaryDirectory() as tmpdir:
            transcripts_dir = os.path.join(tmpdir, "transcripts")
            pdfs_dir = os.path.join(tmpdir, "pdfs")
            os.makedirs(transcripts_dir)
            os.makedirs(pdfs_dir)

            # Create a sample document
            sample_doc = {
                "metadata": {
                    "document_id": "TEST001",
                    "document_date": "1976-09-21",
                    "classification_level": "SECRET",
                    "document_type": "TELEGRAM",
                    "page_count": 1,
                },
                "confidence": {"overall": 0.9, "concerns": []},
            }
            with open(os.path.join(transcripts_dir, "test.json"), "w") as f:
                json.dump(sample_doc, f)

            results = process_documents(transcripts_dir, full_mode=True, pdf_dir=pdfs_dir)
            generate_full_html_report(results, tmpdir, serve_mode=False)

            report_path = os.path.join(tmpdir, "report_full.html")
            with open(report_path, "r") as f:
                content = f.read()

            # Check for file:// URLs (not server URLs)
            assert 'file://' in content
            # PDF viewer should NOT be included
            assert 'id="pdf-viewer-modal"' not in content
