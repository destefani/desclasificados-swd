"""Unit tests for app.visualizations.geographic_map module."""

import pytest
from collections import Counter

from app.visualizations.geographic_map import (
    geocode_location,
    aggregate_locations,
    get_detention_centers_from_docs,
    generate_geographic_map,
    LOCATION_COORDS,
    COUNTRY_COORDS,
    DETENTION_CENTERS,
    OPERATION_CONDOR_COUNTRIES,
    CONDOR_COUNTRY_CODES,
    COUNTRIES_GEOJSON_URL,
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

    def test_returns_list(self):
        """Should return list of locations."""
        city_count = Counter({"SANTIAGO": 100})
        result = aggregate_locations(city_count, Counter(), Counter())
        assert isinstance(result, list)

    def test_matched_locations_have_coords(self):
        """Matched locations should have lat/lon."""
        city_count = Counter({"SANTIAGO": 100, "BUENOS AIRES": 50})
        locations = aggregate_locations(city_count, Counter(), Counter())
        assert len(locations) == 2
        for loc in locations:
            assert "lat" in loc
            assert "lon" in loc
            assert "count" in loc
            assert "name" in loc
            assert "type" in loc

    def test_deduplicates_by_coordinates(self):
        """Should deduplicate locations with same coordinates."""
        # VALPARAISO and VALPARAÍSO have same coords
        city_count = Counter({"VALPARAISO": 100, "VALPARAÍSO": 50})
        locations = aggregate_locations(city_count, Counter(), Counter())
        # Only one should be included (first one processed - highest count)
        assert len(locations) == 1

    def test_city_priority_over_country(self):
        """Cities should be processed before countries."""
        city_count = Counter({"SANTIAGO": 100})
        country_count = Counter({"CHILE": 200})
        locations = aggregate_locations(city_count, country_count, Counter())

        names = [loc["name"] for loc in locations]
        assert "SANTIAGO" in names

    def test_empty_input(self):
        """Should handle empty counters."""
        locations = aggregate_locations(Counter(), Counter(), Counter())
        assert locations == []


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
        assert "L.map" in html

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

    def test_uses_external_geojson_for_condor_countries(self):
        """Should fetch GeoJSON from external CDN for Condor countries."""
        html = generate_geographic_map(
            city_count=Counter({"SANTIAGO": 100}),
            country_count=Counter(),
            show_condor_countries=True,
        )
        assert "L.geoJSON" in html
        assert "L.rectangle" not in html
        assert "topojson" in html
        assert COUNTRIES_GEOJSON_URL in html

    def test_condor_country_codes_in_html(self):
        """Generated HTML should contain country codes for filtering."""
        html = generate_geographic_map(
            city_count=Counter(),
            country_count=Counter(),
            show_condor_countries=True,
        )
        # Check that country codes are in the JavaScript
        assert "condorCountryCodes" in html
        assert '"152"' in html  # Chile
        assert '"032"' in html  # Argentina


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
        assert "CHILE" in OPERATION_CONDOR_COUNTRIES
        assert "ARGENTINA" in OPERATION_CONDOR_COUNTRIES
        assert "URUGUAY" in OPERATION_CONDOR_COUNTRIES
        assert "PARAGUAY" in OPERATION_CONDOR_COUNTRIES
        assert "BOLIVIA" in OPERATION_CONDOR_COUNTRIES
        assert "BRAZIL" in OPERATION_CONDOR_COUNTRIES
        assert len(OPERATION_CONDOR_COUNTRIES) == 6

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


class TestCondorCountryCodes:
    """Tests for CONDOR_COUNTRY_CODES constant."""

    def test_has_six_countries(self):
        """Should have exactly 6 Operation Condor countries."""
        assert len(CONDOR_COUNTRY_CODES) == 6

    def test_has_all_condor_countries(self):
        """Should have codes for all Operation Condor countries."""
        country_names = set(CONDOR_COUNTRY_CODES.values())
        expected = {"Chile", "Argentina", "Uruguay", "Paraguay", "Bolivia", "Brazil"}
        assert country_names == expected

    def test_codes_are_valid_iso3166(self):
        """Country codes should be valid ISO 3166-1 numeric codes."""
        expected_codes = {
            "152": "Chile",
            "032": "Argentina",
            "858": "Uruguay",
            "600": "Paraguay",
            "068": "Bolivia",
            "076": "Brazil",
        }
        assert CONDOR_COUNTRY_CODES == expected_codes

    def test_geojson_url_is_valid(self):
        """GeoJSON URL should be a valid HTTPS URL."""
        assert COUNTRIES_GEOJSON_URL.startswith("https://")
        assert "countries" in COUNTRIES_GEOJSON_URL.lower()
