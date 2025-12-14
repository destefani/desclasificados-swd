"""Unit tests for app.visualizations.geographic_map module."""

import pytest
from collections import Counter

from app.visualizations.geographic_map import (
    geocode_location,
    aggregate_locations,
    get_detention_centers_from_docs,
    generate_geocoding_stats_card,
    generate_geographic_map,
    LOCATION_COORDS,
    COUNTRY_COORDS,
    DETENTION_CENTERS,
    OPERATION_CONDOR_COUNTRIES,
)


class TestGeocodeLocation:
    """Tests for geocode_location function."""

    def test_exact_match_city(self):
        """Should find exact city matches."""
        result = geocode_location("SANTIAGO")
        assert result == (-33.4489, -70.6693)

    def test_case_insensitive(self):
        """Should match regardless of case."""
        assert geocode_location("santiago") == geocode_location("SANTIAGO")
        assert geocode_location("Santiago") == geocode_location("SANTIAGO")

    def test_with_accents(self):
        """Should handle accented characters."""
        assert geocode_location("VALPARAISO") == geocode_location("VALPARAÍSO")
        assert geocode_location("CONCEPCION") == geocode_location("CONCEPCIÓN")

    def test_country_match(self):
        """Should find country coordinates."""
        result = geocode_location("CHILE")
        assert result == (-35.6751, -71.5430)

    def test_partial_match(self):
        """Should find partial matches for cities."""
        # "WASHINGTON" should match even if full name varies
        result = geocode_location("WASHINGTON")
        assert result is not None

    def test_unmatched_returns_none(self):
        """Should return None for unknown locations."""
        result = geocode_location("UNKNOWNVILLE")
        assert result is None

    def test_whitespace_handling(self):
        """Should strip whitespace."""
        result = geocode_location("  SANTIAGO  ")
        assert result == (-33.4489, -70.6693)


class TestAggregateLocations:
    """Tests for aggregate_locations function."""

    def test_returns_tuple(self):
        """Should return tuple of (matched, unmatched)."""
        city_count = Counter({"SANTIAGO": 100})
        result = aggregate_locations(city_count, Counter(), Counter())
        assert isinstance(result, tuple)
        assert len(result) == 2

    def test_matched_locations_have_coords(self):
        """Matched locations should have lat/lon."""
        city_count = Counter({"SANTIAGO": 100, "BUENOS AIRES": 50})
        matched, _ = aggregate_locations(city_count, Counter(), Counter())
        assert len(matched) == 2
        for loc in matched:
            assert "lat" in loc
            assert "lon" in loc
            assert "count" in loc
            assert "name" in loc
            assert "type" in loc

    def test_unmatched_locations_tracked(self):
        """Unmatched locations should be returned in second element."""
        city_count = Counter({"UNKNOWNCITY": 50, "SANTIAGO": 100})
        matched, unmatched = aggregate_locations(city_count, Counter(), Counter())

        assert len(matched) == 1
        assert matched[0]["name"] == "SANTIAGO"

        assert len(unmatched) == 1
        assert unmatched[0]["name"] == "UNKNOWNCITY"
        assert unmatched[0]["count"] == 50

    def test_deduplicates_by_coordinates(self):
        """Should deduplicate locations with same coordinates."""
        # VALPARAISO and VALPARAÍSO have same coords
        city_count = Counter({"VALPARAISO": 100, "VALPARAÍSO": 50})
        matched, _ = aggregate_locations(city_count, Counter(), Counter())
        # Only one should be included (first one processed - highest count)
        assert len(matched) == 1

    def test_city_priority_over_country(self):
        """Cities should be processed before countries."""
        city_count = Counter({"SANTIAGO": 100})
        country_count = Counter({"CHILE": 200})
        matched, _ = aggregate_locations(city_count, country_count, Counter())

        # Santiago should be included, Chile should be skipped (different coords though)
        names = [loc["name"] for loc in matched]
        assert "SANTIAGO" in names

    def test_empty_input(self):
        """Should handle empty counters."""
        matched, unmatched = aggregate_locations(Counter(), Counter(), Counter())
        assert matched == []
        assert unmatched == []


class TestGetDetentionCentersFromDocs:
    """Tests for get_detention_centers_from_docs function."""

    def test_returns_all_centers(self):
        """Should return all known detention centers."""
        result = get_detention_centers_from_docs(Counter())
        assert len(result) == len(DETENTION_CENTERS)

    def test_includes_doc_count(self):
        """Should include doc_count for each center."""
        result = get_detention_centers_from_docs(Counter())
        for center in result:
            assert "doc_count" in center

    def test_matches_document_mentions(self):
        """Should match document mentions to centers."""
        mentions = Counter({"VILLA GRIMALDI": 10, "ESTADIO NACIONAL": 5})
        result = get_detention_centers_from_docs(mentions)

        grimaldi = next(c for c in result if c["name"] == "Villa Grimaldi")
        estadio = next(c for c in result if c["name"] == "Estadio Nacional")

        assert grimaldi["doc_count"] == 10
        assert estadio["doc_count"] == 5


class TestGenerateGeocodingStatsCard:
    """Tests for generate_geocoding_stats_card function."""

    def test_returns_html(self):
        """Should return HTML string."""
        html = generate_geocoding_stats_card(
            total_locations=100,
            matched_count=80,
            unmatched_locations=[],
        )
        assert "<div" in html
        assert "80.0%" in html

    def test_shows_percentage(self):
        """Should display correct coverage percentage."""
        html = generate_geocoding_stats_card(
            total_locations=100,
            matched_count=75,
            unmatched_locations=[],
        )
        assert "75.0%" in html

    def test_shows_unmatched_count(self):
        """Should show number of unmatched locations."""
        unmatched = [
            {"name": "UNKNOWN1", "count": 10, "type": "city"},
            {"name": "UNKNOWN2", "count": 5, "type": "city"},
        ]
        html = generate_geocoding_stats_card(
            total_locations=100,
            matched_count=98,
            unmatched_locations=unmatched,
        )
        assert "2" in html  # 2 unmatched

    def test_handles_zero_total(self):
        """Should handle zero total locations without division error."""
        html = generate_geocoding_stats_card(
            total_locations=0,
            matched_count=0,
            unmatched_locations=[],
        )
        assert "0.0%" in html

    def test_includes_container_id(self):
        """Should use specified container ID."""
        html = generate_geocoding_stats_card(
            total_locations=100,
            matched_count=80,
            unmatched_locations=[],
            container_id="test-stats",
        )
        assert 'id="test-stats"' in html


class TestGenerateGeographicMap:
    """Tests for generate_geographic_map function."""

    def test_returns_html_with_leaflet(self):
        """Should return HTML with Leaflet.js script."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
        )
        assert "leaflet" in html.lower()
        assert "<script" in html
        assert 'L.map' in html

    def test_empty_data_returns_valid_html(self):
        """Should return valid HTML even with empty data."""
        html = generate_geographic_map(
            city_count=Counter(),
            country_count=Counter(),
        )
        assert "<div" in html
        assert "map-section" in html

    def test_includes_container_id(self):
        """Should use specified container ID."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            container_id="test-map",
        )
        assert 'id="test-map"' in html

    def test_includes_stats_when_enabled(self):
        """Should include geocoding stats when show_stats=True."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            show_stats=True,
        )
        assert "geocoding-stats" in html.lower() or "Geocoding Coverage" in html

    def test_excludes_stats_when_disabled(self):
        """Should not include geocoding stats when show_stats=False."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            show_stats=False,
        )
        # Stats card should not be present
        assert "Geocoding Coverage" not in html

    def test_includes_heatmap_script_when_enabled(self):
        """Should include Leaflet.heat script when show_heatmap=True."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            show_heatmap=True,
        )
        assert "leaflet-heat.js" in html
        assert "heatLayer" in html

    def test_excludes_heatmap_when_disabled(self):
        """Should not include heatmap when show_heatmap=False."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            show_heatmap=False,
        )
        assert "leaflet-heat.js" not in html

    def test_includes_time_slider_when_enabled(self):
        """Should include time slider when show_time_slider=True and data available."""
        location_by_year = {
            "1973": {"SANTIAGO": 50},
            "1974": {"SANTIAGO": 30},
            "1975": {"SANTIAGO": 20},
        }
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            location_by_year=location_by_year,
            show_time_slider=True,
        )
        assert "year-start" in html
        assert "year-end" in html
        assert "Year Range" in html

    def test_includes_document_links_in_full_mode(self):
        """Should include document links in popups when full_mode=True."""
        city_docs = {
            "SANTIAGO": [
                ("DOC1", "/path/to/doc1.pdf", "doc1"),
                ("DOC2", "/path/to/doc2.pdf", "doc2"),
            ]
        }
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            city_docs=city_docs,
            full_mode=True,
        )
        assert "fullMode = true" in html
        assert "loc.docs" in html

    def test_includes_detention_centers(self):
        """Should include detention centers when show_detention_centers=True."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            torture_detention_centers=Counter({"VILLA GRIMALDI": 5}),
            show_detention_centers=True,
        )
        assert "Detention Centers" in html
        assert "detentionLayer" in html

    def test_includes_condor_countries(self):
        """Should include Operation Condor countries when show_condor_countries=True."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            show_condor_countries=True,
        )
        assert "Operation Condor" in html
        assert "condorLayer" in html


class TestCoordinateConstants:
    """Tests for coordinate constants."""

    def test_location_coords_has_santiago(self):
        """LOCATION_COORDS should include Santiago."""
        assert "SANTIAGO" in LOCATION_COORDS

    def test_country_coords_has_chile(self):
        """COUNTRY_COORDS should include Chile."""
        assert "CHILE" in COUNTRY_COORDS

    def test_detention_centers_has_villa_grimaldi(self):
        """DETENTION_CENTERS should include Villa Grimaldi."""
        names = [c["name"] for c in DETENTION_CENTERS]
        assert "Villa Grimaldi" in names

    def test_operation_condor_countries_list(self):
        """OPERATION_CONDOR_COUNTRIES should list all member states."""
        country_names = [c["name"] for c in OPERATION_CONDOR_COUNTRIES]
        assert "CHILE" in country_names
        assert "ARGENTINA" in country_names
        assert "URUGUAY" in country_names
        assert "PARAGUAY" in country_names
        assert "BOLIVIA" in country_names
        assert "BRAZIL" in country_names
        assert len(OPERATION_CONDOR_COUNTRIES) == 6

    def test_operation_condor_countries_have_required_fields(self):
        """Each Operation Condor country should have required fields."""
        required_fields = ["name", "capital", "lat", "lon", "role", "joined"]
        for country in OPERATION_CONDOR_COUNTRIES:
            for field in required_fields:
                assert field in country, f"Missing field {field} in {country.get('name', 'unknown')}"
            # Validate coordinates
            assert -90 <= country["lat"] <= 90, f"{country['name']} latitude out of range"
            assert -180 <= country["lon"] <= 180, f"{country['name']} longitude out of range"

    def test_coordinates_are_valid_tuples(self):
        """All coordinates should be valid (lat, lon) tuples."""
        for name, coords in LOCATION_COORDS.items():
            assert isinstance(coords, tuple), f"{name} should be a tuple"
            assert len(coords) == 2, f"{name} should have 2 elements"
            lat, lon = coords
            assert -90 <= lat <= 90, f"{name} latitude {lat} out of range"
            assert -180 <= lon <= 180, f"{name} longitude {lon} out of range"

    def test_country_coordinates_are_valid(self):
        """All country coordinates should be valid."""
        for name, coords in COUNTRY_COORDS.items():
            assert isinstance(coords, tuple), f"{name} should be a tuple"
            assert len(coords) == 2
            lat, lon = coords
            assert -90 <= lat <= 90
            assert -180 <= lon <= 180
