"""
Visualization modules for declassified documents analysis.

This package provides interactive JavaScript-based visualizations
for the HTML reports, including:
- Interactive timeline with historical event annotations
- Network graphs for people/organization relationships
- Geographic maps for location analysis
"""

from app.visualizations.interactive_timeline import (
    generate_interactive_timeline,
    generate_timeline_with_monthly_detail,
)
from app.visualizations.historical_events import HISTORICAL_EVENTS
from app.visualizations.network_graph import (
    compute_cooccurrence,
    generate_network_graph,
    generate_people_network,
    generate_organization_network,
)
from app.visualizations.geographic_map import (
    generate_geographic_map,
    geocode_location,
    aggregate_locations,
    LOCATION_COORDS,
    COUNTRY_COORDS,
    DETENTION_CENTERS,
    OPERATION_CONDOR_COUNTRIES,
)
from app.visualizations.sensitive_content import (
    generate_sensitive_timeline,
    generate_perpetrator_victim_network,
    generate_incident_types_chart,
    generate_sensitive_summary_cards,
    SENSITIVE_COLORS,
)
from app.visualizations.keyword_cloud import (
    generate_keyword_cloud,
    generate_keyword_bar_chart,
    prepare_wordcloud_data,
    KEYWORD_COLORS,
)

__all__ = [
    "generate_interactive_timeline",
    "generate_timeline_with_monthly_detail",
    "HISTORICAL_EVENTS",
    "compute_cooccurrence",
    "generate_network_graph",
    "generate_people_network",
    "generate_organization_network",
    "generate_geographic_map",
    "geocode_location",
    "aggregate_locations",
    "LOCATION_COORDS",
    "COUNTRY_COORDS",
    "DETENTION_CENTERS",
    "OPERATION_CONDOR_COUNTRIES",
    "generate_sensitive_timeline",
    "generate_perpetrator_victim_network",
    "generate_incident_types_chart",
    "generate_sensitive_summary_cards",
    "SENSITIVE_COLORS",
    "generate_keyword_cloud",
    "generate_keyword_bar_chart",
    "prepare_wordcloud_data",
    "KEYWORD_COLORS",
]
