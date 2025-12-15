"""
Geographic map visualization using Leaflet.js.

Generates interactive maps showing:
- Document mentions by location
- Detention centers from torture references
- Operation Condor country connections
"""

import json
from collections import Counter
from typing import Any


# Leaflet.js CDN URLs
LEAFLET_CSS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"
LEAFLET_JS = "https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"

# Pre-defined coordinates for known locations
# Format: "LOCATION_NAME": (latitude, longitude)
LOCATION_COORDS: dict[str, tuple[float, float]] = {
    # Chile - Cities
    "SANTIAGO": (-33.4489, -70.6693),
    "VALPARAISO": (-33.0472, -71.6127),
    "VALPARAÍSO": (-33.0472, -71.6127),
    "CONCEPCION": (-36.8270, -73.0503),
    "CONCEPCIÓN": (-36.8270, -73.0503),
    "VIÑA DEL MAR": (-33.0153, -71.5500),
    "ANTOFAGASTA": (-23.6509, -70.3975),
    "TEMUCO": (-38.7359, -72.5904),
    "IQUIQUE": (-20.2208, -70.1431),
    "PUNTA ARENAS": (-53.1638, -70.9171),
    "TALCA": (-35.4264, -71.6554),
    "ARICA": (-18.4783, -70.3126),
    "CHILLAN": (-36.6066, -72.1034),
    "CHILLÁN": (-36.6066, -72.1034),
    "OSORNO": (-40.5740, -73.1335),
    "PUERTO MONTT": (-41.4693, -72.9424),
    "LA SERENA": (-29.9027, -71.2519),
    "RANCAGUA": (-34.1708, -70.7444),
    "TALCAHUANO": (-36.7249, -73.1169),
    "COPIAPO": (-27.3668, -70.3323),
    "COPIAPÓ": (-27.3668, -70.3323),

    # Chile - Detention Centers (known sites)
    "VILLA GRIMALDI": (-33.4545, -70.5483),
    "LONDRES 38": (-33.4422, -70.6506),
    "JOSE DOMINGO CANAS": (-33.4350, -70.6100),
    "JOSÉ DOMINGO CAÑAS": (-33.4350, -70.6100),
    "TEJAS VERDES": (-33.6167, -71.6167),
    "ESTADIO NACIONAL": (-33.4650, -70.6106),
    "ESTADIO CHILE": (-33.4514, -70.6658),
    "TRES ALAMOS": (-33.5167, -70.6333),
    "CUATRO ALAMOS": (-33.5167, -70.6333),
    "COLONIA DIGNIDAD": (-36.1500, -71.3833),
    "RITOQUE": (-32.8333, -71.5167),
    "PISAGUA": (-19.5972, -70.2122),
    "CHACABUCO": (-22.9167, -69.0667),
    "DAWSON ISLAND": (-53.7500, -70.5000),
    "ISLA DAWSON": (-53.7500, -70.5000),

    # Argentina
    "BUENOS AIRES": (-34.6037, -58.3816),
    "CORDOBA": (-31.4201, -64.1888),
    "CÓRDOBA": (-31.4201, -64.1888),
    "MENDOZA": (-32.8908, -68.8272),
    "ROSARIO": (-32.9442, -60.6505),
    "MAR DEL PLATA": (-38.0055, -57.5426),

    # Uruguay
    "MONTEVIDEO": (-34.9011, -56.1645),

    # Paraguay
    "ASUNCION": (-25.2637, -57.5759),
    "ASUNCIÓN": (-25.2637, -57.5759),

    # Bolivia
    "LA PAZ": (-16.4897, -68.1193),
    "SANTA CRUZ": (-17.7833, -63.1822),
    "COCHABAMBA": (-17.3895, -66.1568),

    # Brazil
    "BRASILIA": (-15.7975, -47.8919),
    "BRASÍLIA": (-15.7975, -47.8919),
    "SAO PAULO": (-23.5505, -46.6333),
    "SÃO PAULO": (-23.5505, -46.6333),
    "RIO DE JANEIRO": (-22.9068, -43.1729),
    "PORTO ALEGRE": (-30.0346, -51.2177),

    # Peru
    "LIMA": (-12.0464, -77.0428),

    # Ecuador
    "QUITO": (-0.1807, -78.4678),
    "GUAYAQUIL": (-2.1710, -79.9224),

    # Colombia
    "BOGOTA": (4.7110, -74.0721),
    "BOGOTÁ": (4.7110, -74.0721),

    # Venezuela
    "CARACAS": (10.4806, -66.9036),

    # United States
    "WASHINGTON": (38.9072, -77.0369),
    "WASHINGTON D.C.": (38.9072, -77.0369),
    "WASHINGTON DC": (38.9072, -77.0369),
    "WASHDC": (38.9072, -77.0369),
    "NEW YORK": (40.7128, -74.0060),
    "NEW YORK CITY": (40.7128, -74.0060),
    "MIAMI": (25.7617, -80.1918),
    "LOS ANGELES": (34.0522, -118.2437),
    "LANGLEY": (38.9318, -77.1467),  # CIA HQ
    "CHICAGO": (41.8781, -87.6298),

    # Cuba
    "HAVANA": (23.1136, -82.3666),
    "LA HABANA": (23.1136, -82.3666),

    # Mexico
    "MEXICO CITY": (19.4326, -99.1332),
    "CIUDAD DE MEXICO": (19.4326, -99.1332),

    # Panama
    "PANAMA CITY": (8.9824, -79.5199),
    "PANAMA": (8.9824, -79.5199),
    "PANAMÁ": (8.9824, -79.5199),

    # Europe
    "ROME": (41.9028, 12.4964),
    "ROMA": (41.9028, 12.4964),
    "PARIS": (48.8566, 2.3522),
    "LONDON": (51.5074, -0.1278),
    "MADRID": (40.4168, -3.7038),
    "BONN": (50.7374, 7.0982),
    "GENEVA": (46.2044, 6.1432),
}

# Country coordinates (for country-level aggregation)
COUNTRY_COORDS: dict[str, tuple[float, float]] = {
    "CHILE": (-35.6751, -71.5430),
    "ARGENTINA": (-38.4161, -63.6167),
    "UNITED STATES": (37.0902, -95.7129),
    "USA": (37.0902, -95.7129),
    "URUGUAY": (-32.5228, -55.7658),
    "PARAGUAY": (-23.4425, -58.4438),
    "BOLIVIA": (-16.2902, -63.5887),
    "BRAZIL": (-14.2350, -51.9253),
    "PERU": (-9.1900, -75.0152),
    "ECUADOR": (-1.8312, -78.1834),
    "COLOMBIA": (4.5709, -74.2973),
    "VENEZUELA": (6.4238, -66.5897),
    "CUBA": (21.5218, -77.7812),
    "MEXICO": (23.6345, -102.5528),
    "PANAMA": (8.5380, -80.7821),
    "ITALY": (41.8719, 12.5674),
    "FRANCE": (46.2276, 2.2137),
    "UNITED KINGDOM": (55.3781, -3.4360),
    "SPAIN": (40.4637, -3.7492),
    "GERMANY": (51.1657, 10.4515),
    "SWITZERLAND": (46.8182, 8.2275),
}

# Known detention centers with metadata
DETENTION_CENTERS: list[dict[str, Any]] = [
    {
        "name": "Villa Grimaldi",
        "coords": (-33.4545, -70.5483),
        "city": "Santiago",
        "description": "DINA torture center, operated 1974-1978. Estimated 4,500 prisoners, 226 killed.",
        "type": "torture_center"
    },
    {
        "name": "Londres 38",
        "coords": (-33.4422, -70.6506),
        "city": "Santiago",
        "description": "DINA detention center at Londres Street 38. Active 1973-1974.",
        "type": "torture_center"
    },
    {
        "name": "José Domingo Cañas",
        "coords": (-33.4350, -70.6100),
        "city": "Santiago",
        "description": "DINA detention center. Active 1974.",
        "type": "torture_center"
    },
    {
        "name": "Estadio Nacional",
        "coords": (-33.4650, -70.6106),
        "city": "Santiago",
        "description": "National Stadium used as mass detention center after coup. Sept-Nov 1973.",
        "type": "detention"
    },
    {
        "name": "Estadio Chile",
        "coords": (-33.4514, -70.6658),
        "city": "Santiago",
        "description": "Chile Stadium detention center. Víctor Jara murdered here.",
        "type": "detention"
    },
    {
        "name": "Tejas Verdes",
        "coords": (-33.6167, -71.6167),
        "city": "San Antonio",
        "description": "Military school used as torture center. Active 1973-1974.",
        "type": "torture_center"
    },
    {
        "name": "Colonia Dignidad",
        "coords": (-36.1500, -71.3833),
        "city": "Parral",
        "description": "German cult compound used by DINA for torture and disappearances.",
        "type": "torture_center"
    },
    {
        "name": "Isla Dawson",
        "coords": (-53.7500, -70.5000),
        "city": "Magallanes",
        "description": "Island prison camp for political prisoners. 1973-1974.",
        "type": "prison_camp"
    },
    {
        "name": "Pisagua",
        "coords": (-19.5972, -70.2122),
        "city": "Tarapacá",
        "description": "Desert prison camp. Mass graves discovered 1990.",
        "type": "prison_camp"
    },
    {
        "name": "Chacabuco",
        "coords": (-22.9167, -69.0667),
        "city": "Antofagasta",
        "description": "Former nitrate mining town converted to prison camp.",
        "type": "prison_camp"
    },
    {
        "name": "Tres Álamos",
        "coords": (-33.5167, -70.6333),
        "city": "Santiago",
        "description": "CNI detention center, operated after DINA dissolution.",
        "type": "detention"
    },
]

# Operation Condor member countries
OPERATION_CONDOR_COUNTRIES = [
    "CHILE", "ARGENTINA", "URUGUAY", "PARAGUAY", "BOLIVIA", "BRAZIL"
]

# GeoJSON polygons for Operation Condor countries
# More detailed boundaries for visualization
CONDOR_COUNTRY_GEOJSON: dict[str, dict] = {
    "CHILE": {
        "type": "Feature",
        "properties": {"name": "Chile"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-69.5, -17.5], [-69.9, -17.7], [-70.2, -18.1], [-70.4, -18.6],
                [-70.3, -19.2], [-70.1, -19.8], [-70.2, -20.5], [-70.1, -21.1],
                [-70.4, -21.8], [-70.6, -22.5], [-70.4, -23.2], [-70.2, -23.8],
                [-70.4, -24.5], [-70.5, -25.2], [-70.3, -25.8], [-70.1, -26.5],
                [-70.3, -27.1], [-70.6, -27.8], [-70.9, -28.5], [-71.2, -29.2],
                [-71.4, -29.8], [-71.5, -30.3], [-71.5, -30.8], [-71.6, -31.4],
                [-71.6, -32.0], [-71.7, -32.6], [-71.6, -33.2], [-71.4, -33.8],
                [-71.3, -34.4], [-71.4, -35.0], [-71.7, -35.6], [-72.0, -36.2],
                [-72.4, -36.8], [-72.8, -37.4], [-73.0, -38.0], [-73.1, -38.6],
                [-73.2, -39.2], [-73.3, -39.8], [-73.4, -40.4], [-73.3, -41.0],
                [-73.2, -41.5], [-72.8, -42.0], [-72.4, -42.5], [-72.1, -43.0],
                [-72.5, -43.5], [-73.2, -43.8], [-73.8, -44.2], [-74.2, -44.8],
                [-74.5, -45.4], [-74.7, -46.0], [-75.0, -46.6], [-75.2, -47.2],
                [-75.3, -47.8], [-75.4, -48.4], [-75.3, -49.0], [-74.8, -49.6],
                [-74.4, -50.2], [-74.0, -50.8], [-73.5, -51.4], [-73.0, -52.0],
                [-72.3, -52.4], [-71.5, -52.6], [-70.8, -52.8], [-70.0, -53.2],
                [-69.5, -53.8], [-69.0, -54.4], [-68.6, -54.9], [-68.6, -54.9],
                [-68.6, -54.4], [-68.6, -53.8], [-68.7, -53.2], [-68.9, -52.6],
                [-69.2, -52.0], [-69.4, -51.4], [-69.4, -50.8], [-69.3, -50.2],
                [-69.2, -49.6], [-69.0, -49.0], [-68.7, -48.4], [-68.4, -47.8],
                [-68.0, -47.2], [-67.5, -46.6], [-67.0, -46.0], [-66.5, -45.4],
                [-66.2, -44.8], [-66.4, -44.2], [-66.6, -43.6], [-66.8, -43.0],
                [-67.0, -42.4], [-67.0, -41.8], [-67.0, -41.2], [-67.0, -40.6],
                [-67.0, -40.0], [-67.0, -39.4], [-67.0, -38.8], [-67.0, -38.2],
                [-67.2, -37.6], [-67.4, -37.0], [-67.6, -36.4], [-67.8, -35.8],
                [-68.0, -35.2], [-68.2, -34.6], [-68.4, -34.0], [-68.5, -33.4],
                [-68.5, -32.8], [-68.4, -32.2], [-68.3, -31.6], [-68.5, -31.0],
                [-68.8, -30.4], [-69.0, -29.8], [-69.0, -29.2], [-68.8, -28.6],
                [-68.5, -28.0], [-68.3, -27.4], [-68.4, -26.8], [-68.5, -26.2],
                [-68.6, -25.6], [-68.6, -25.0], [-68.5, -24.4], [-68.2, -23.8],
                [-67.8, -23.2], [-67.4, -22.6], [-67.2, -22.0], [-67.1, -21.4],
                [-67.2, -20.8], [-67.5, -20.2], [-68.0, -19.6], [-68.5, -19.0],
                [-69.0, -18.4], [-69.5, -17.5]
            ]]
        }
    },
    "ARGENTINA": {
        "type": "Feature",
        "properties": {"name": "Argentina"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-66.0, -22.0], [-65.2, -22.1], [-64.5, -22.4], [-63.8, -22.2],
                [-63.0, -22.0], [-62.4, -22.3], [-61.8, -22.8], [-61.2, -23.2],
                [-60.6, -23.6], [-60.0, -24.0], [-59.4, -24.2], [-58.8, -24.4],
                [-58.2, -24.8], [-57.6, -25.2], [-57.2, -25.8], [-57.4, -26.4],
                [-57.8, -27.0], [-57.2, -27.3], [-56.4, -27.5], [-55.8, -27.8],
                [-55.2, -28.2], [-54.6, -28.6], [-54.2, -29.2], [-54.0, -29.8],
                [-53.9, -30.4], [-54.0, -31.0], [-54.2, -31.6], [-54.5, -32.2],
                [-54.8, -32.8], [-55.2, -33.2], [-55.8, -33.6], [-56.4, -33.9],
                [-57.0, -34.2], [-57.6, -34.4], [-58.2, -34.5], [-58.5, -34.2],
                [-58.8, -34.6], [-59.2, -35.2], [-59.6, -35.8], [-60.0, -36.2],
                [-60.5, -36.6], [-61.0, -37.0], [-61.6, -37.6], [-62.2, -38.2],
                [-62.6, -38.6], [-63.0, -39.0], [-63.4, -39.4], [-63.8, -39.8],
                [-64.2, -40.2], [-64.6, -40.6], [-65.0, -41.0], [-65.2, -41.6],
                [-65.2, -42.2], [-65.4, -42.8], [-65.6, -43.4], [-66.0, -44.0],
                [-66.3, -44.6], [-66.5, -45.2], [-66.7, -45.8], [-67.0, -46.4],
                [-67.2, -47.0], [-67.4, -47.6], [-67.6, -48.2], [-67.7, -48.8],
                [-67.8, -49.4], [-67.9, -50.0], [-68.0, -50.6], [-68.2, -51.2],
                [-68.4, -51.8], [-68.6, -52.4], [-68.8, -53.0], [-69.0, -53.6],
                [-69.2, -54.2], [-68.6, -54.9], [-68.6, -54.9], [-68.6, -54.4],
                [-68.6, -53.8], [-68.7, -53.2], [-68.9, -52.6], [-69.2, -52.0],
                [-69.4, -51.4], [-69.4, -50.8], [-69.3, -50.2], [-69.2, -49.6],
                [-69.0, -49.0], [-68.7, -48.4], [-68.4, -47.8], [-68.0, -47.2],
                [-67.5, -46.6], [-67.0, -46.0], [-66.5, -45.4], [-66.2, -44.8],
                [-66.4, -44.2], [-66.6, -43.6], [-66.8, -43.0], [-67.0, -42.4],
                [-67.0, -41.8], [-67.0, -41.2], [-67.0, -40.6], [-67.0, -40.0],
                [-67.0, -39.4], [-67.0, -38.8], [-67.0, -38.2], [-67.2, -37.6],
                [-67.4, -37.0], [-67.6, -36.4], [-67.8, -35.8], [-68.0, -35.2],
                [-68.2, -34.6], [-68.4, -34.0], [-68.5, -33.4], [-68.5, -32.8],
                [-68.4, -32.2], [-68.3, -31.6], [-68.5, -31.0], [-68.8, -30.4],
                [-69.0, -29.8], [-69.0, -29.2], [-68.8, -28.6], [-68.5, -28.0],
                [-68.3, -27.4], [-68.4, -26.8], [-68.5, -26.2], [-68.6, -25.6],
                [-68.6, -25.0], [-68.5, -24.4], [-68.2, -23.8], [-67.8, -23.2],
                [-67.4, -22.6], [-67.2, -22.2], [-66.6, -22.0], [-66.0, -22.0]
            ]]
        }
    },
    "URUGUAY": {
        "type": "Feature",
        "properties": {"name": "Uruguay"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-58.4, -33.0], [-58.3, -33.3], [-58.1, -33.6], [-58.0, -33.9],
                [-57.8, -34.1], [-57.5, -34.3], [-57.1, -34.4], [-56.7, -34.4],
                [-56.3, -34.3], [-55.9, -34.2], [-55.5, -34.1], [-55.1, -34.0],
                [-54.7, -34.1], [-54.3, -34.3], [-53.9, -34.5], [-53.6, -34.2],
                [-53.5, -33.8], [-53.5, -33.4], [-53.6, -33.0], [-53.8, -32.6],
                [-54.1, -32.2], [-54.4, -31.8], [-54.7, -31.4], [-55.0, -31.1],
                [-55.4, -30.9], [-55.8, -30.7], [-56.2, -30.5], [-56.6, -30.3],
                [-57.0, -30.2], [-57.4, -30.3], [-57.7, -30.5], [-58.0, -30.8],
                [-58.1, -31.2], [-58.2, -31.6], [-58.3, -32.0], [-58.4, -32.5],
                [-58.4, -33.0]
            ]]
        }
    },
    "PARAGUAY": {
        "type": "Feature",
        "properties": {"name": "Paraguay"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-62.5, -22.0], [-62.0, -21.4], [-61.5, -20.8], [-61.0, -20.2],
                [-60.5, -19.8], [-60.0, -19.5], [-59.5, -19.4], [-59.0, -19.4],
                [-58.5, -19.6], [-58.2, -20.0], [-58.0, -20.5], [-57.8, -21.0],
                [-57.8, -21.6], [-57.8, -22.2], [-57.5, -22.6], [-57.0, -22.8],
                [-56.5, -22.8], [-56.0, -22.6], [-55.7, -23.0], [-55.5, -23.5],
                [-55.4, -24.0], [-55.4, -24.5], [-55.5, -25.0], [-55.6, -25.5],
                [-55.7, -26.0], [-55.8, -26.5], [-56.0, -27.0], [-56.5, -27.2],
                [-57.0, -27.3], [-57.5, -27.2], [-57.8, -27.0], [-57.4, -26.4],
                [-57.2, -25.8], [-57.6, -25.2], [-58.2, -24.8], [-58.8, -24.4],
                [-59.4, -24.2], [-60.0, -24.0], [-60.6, -23.6], [-61.2, -23.2],
                [-61.8, -22.8], [-62.2, -22.4], [-62.5, -22.0]
            ]]
        }
    },
    "BOLIVIA": {
        "type": "Feature",
        "properties": {"name": "Bolivia"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-69.5, -17.5], [-69.2, -17.8], [-69.0, -18.2], [-68.8, -18.6],
                [-68.6, -19.0], [-68.4, -19.4], [-68.2, -19.8], [-68.0, -20.2],
                [-67.8, -20.6], [-67.6, -21.0], [-67.4, -21.4], [-67.2, -21.8],
                [-67.2, -22.2], [-67.4, -22.6], [-67.0, -22.8], [-66.5, -22.6],
                [-66.0, -22.4], [-65.5, -22.2], [-65.0, -22.1], [-64.5, -22.3],
                [-64.0, -22.4], [-63.5, -22.2], [-63.0, -22.0], [-62.5, -22.0],
                [-62.2, -22.4], [-61.8, -22.8], [-61.5, -22.4], [-61.2, -21.8],
                [-61.0, -21.2], [-60.8, -20.6], [-60.4, -20.0], [-60.0, -19.5],
                [-59.5, -19.4], [-59.0, -19.4], [-58.5, -19.0], [-58.2, -18.5],
                [-58.2, -18.0], [-58.4, -17.5], [-58.6, -17.0], [-58.8, -16.5],
                [-59.2, -16.2], [-59.6, -16.0], [-60.0, -15.8], [-60.5, -15.5],
                [-61.0, -15.2], [-61.5, -14.8], [-62.0, -14.4], [-62.5, -14.0],
                [-63.0, -13.6], [-63.5, -13.2], [-64.0, -12.8], [-64.5, -12.4],
                [-65.0, -11.8], [-65.5, -11.4], [-66.0, -11.0], [-66.5, -10.7],
                [-67.0, -10.5], [-67.5, -10.5], [-68.0, -10.7], [-68.5, -11.0],
                [-68.8, -11.5], [-69.0, -12.0], [-69.2, -12.6], [-69.3, -13.2],
                [-69.4, -13.8], [-69.5, -14.4], [-69.5, -15.0], [-69.5, -15.6],
                [-69.5, -16.2], [-69.5, -16.8], [-69.5, -17.5]
            ]]
        }
    },
    "BRAZIL": {
        "type": "Feature",
        "properties": {"name": "Brazil"},
        "geometry": {
            "type": "Polygon",
            "coordinates": [[
                [-53.5, -33.4], [-53.4, -33.0], [-53.3, -32.5], [-53.0, -32.0],
                [-52.5, -31.5], [-52.0, -31.0], [-51.5, -30.5], [-51.0, -30.0],
                [-50.5, -29.5], [-50.0, -29.0], [-49.5, -28.5], [-49.0, -28.0],
                [-48.5, -27.0], [-48.2, -26.0], [-48.3, -25.5], [-48.5, -25.0],
                [-48.2, -24.5], [-47.5, -24.2], [-47.0, -24.0], [-46.5, -23.8],
                [-46.0, -23.5], [-45.5, -23.2], [-45.0, -23.0], [-44.5, -22.8],
                [-44.0, -22.6], [-43.5, -22.6], [-43.0, -22.4], [-42.5, -22.2],
                [-42.0, -22.2], [-41.5, -22.0], [-41.0, -21.5], [-40.5, -20.8],
                [-40.0, -20.0], [-39.5, -18.5], [-39.0, -17.0], [-38.5, -15.5],
                [-38.0, -14.0], [-37.5, -12.5], [-36.5, -10.5], [-35.5, -8.5],
                [-35.0, -6.5], [-35.0, -5.5], [-35.5, -5.0], [-36.5, -4.8],
                [-37.5, -4.5], [-38.5, -4.0], [-39.5, -3.5], [-40.5, -3.0],
                [-41.5, -2.5], [-42.5, -2.2], [-43.5, -2.0], [-44.5, -1.8],
                [-45.5, -1.5], [-46.5, -1.2], [-47.5, -0.8], [-48.5, -0.4],
                [-49.5, -0.1], [-50.0, 0.2], [-50.5, 0.6], [-51.0, 1.0],
                [-51.5, 1.5], [-52.0, 2.0], [-52.5, 2.3], [-53.5, 2.5],
                [-54.5, 2.4], [-55.5, 2.2], [-56.5, 2.0], [-57.5, 1.8],
                [-58.5, 1.5], [-59.5, 1.2], [-60.5, 1.0], [-61.5, 0.8],
                [-62.5, 0.6], [-63.5, 0.8], [-64.5, 1.0], [-65.5, 1.2],
                [-66.5, 1.8], [-67.0, 2.0], [-67.5, 1.8], [-68.0, 1.4],
                [-68.5, 1.0], [-69.0, 0.5], [-69.5, 0.0], [-70.0, -0.5],
                [-70.0, -1.5], [-69.8, -2.5], [-69.5, -3.5], [-69.5, -4.5],
                [-69.8, -5.5], [-70.0, -6.5], [-70.2, -7.5], [-70.5, -8.5],
                [-71.0, -9.5], [-71.5, -10.0], [-72.0, -10.5], [-72.5, -11.0],
                [-73.0, -11.5], [-73.5, -12.0], [-73.2, -12.8], [-72.8, -13.5],
                [-72.0, -14.0], [-71.0, -14.2], [-70.0, -14.5], [-69.5, -15.0],
                [-69.5, -15.6], [-69.5, -16.2], [-69.5, -16.8], [-69.5, -17.5],
                [-69.0, -18.2], [-68.5, -19.0], [-68.0, -19.8], [-58.4, -17.5],
                [-58.2, -18.0], [-58.2, -18.5], [-58.5, -19.0], [-59.0, -19.4],
                [-59.5, -19.4], [-60.0, -19.5], [-60.4, -20.0], [-60.8, -20.6],
                [-61.0, -21.2], [-61.2, -21.8], [-61.5, -22.4], [-61.8, -22.8],
                [-61.2, -23.2], [-60.6, -23.6], [-60.0, -24.0], [-59.4, -24.2],
                [-58.8, -24.4], [-58.2, -24.8], [-57.6, -25.2], [-57.2, -25.8],
                [-57.4, -26.4], [-57.8, -27.0], [-57.5, -27.2], [-57.0, -27.3],
                [-56.5, -27.2], [-56.0, -27.0], [-55.8, -26.5], [-55.7, -26.0],
                [-55.6, -25.5], [-55.5, -25.0], [-55.4, -24.5], [-55.4, -24.0],
                [-55.5, -23.5], [-55.7, -23.0], [-56.0, -22.6], [-56.5, -22.8],
                [-57.0, -22.8], [-57.5, -22.6], [-57.8, -22.2], [-57.8, -21.6],
                [-57.8, -21.0], [-58.0, -20.5], [-58.2, -20.0], [-58.5, -19.6],
                [-59.0, -19.4], [-58.2, -18.5], [-58.2, -18.0], [-58.0, -17.5],
                [-57.5, -18.0], [-57.0, -19.0], [-56.5, -20.0], [-56.0, -21.0],
                [-55.5, -22.0], [-55.0, -23.0], [-54.5, -24.0], [-54.0, -25.0],
                [-53.8, -26.0], [-53.7, -27.0], [-53.6, -28.0], [-53.6, -29.0],
                [-53.5, -30.0], [-53.4, -31.0], [-53.4, -32.0], [-53.5, -33.4]
            ]]
        }
    }
}


def geocode_location(location: str) -> tuple[float, float] | None:
    """
    Get coordinates for a location name.

    Returns (lat, lon) tuple or None if not found.
    """
    # Normalize location name
    normalized = location.upper().strip()

    # Try exact match first
    if normalized in LOCATION_COORDS:
        return LOCATION_COORDS[normalized]

    # Try country coords
    if normalized in COUNTRY_COORDS:
        return COUNTRY_COORDS[normalized]

    # Try partial match for cities
    for name, coords in LOCATION_COORDS.items():
        if normalized in name or name in normalized:
            return coords

    return None


def aggregate_locations(
    city_count: Counter,
    country_count: Counter,
    other_place_count: Counter,
) -> list[dict[str, Any]]:
    """
    Aggregate location data from document metadata.

    Returns list of location dicts with coords and counts.
    """
    locations = []
    seen_coords = set()

    # Process cities first (most specific)
    for city, count in city_count.most_common():
        coords = geocode_location(city)
        if coords and coords not in seen_coords:
            locations.append({
                "name": city,
                "count": count,
                "lat": coords[0],
                "lon": coords[1],
                "type": "city",
            })
            seen_coords.add(coords)

    # Process other places
    for place, count in other_place_count.most_common():
        coords = geocode_location(place)
        if coords and coords not in seen_coords:
            locations.append({
                "name": place,
                "count": count,
                "lat": coords[0],
                "lon": coords[1],
                "type": "place",
            })
            seen_coords.add(coords)

    # Process countries (only if no city from that country)
    for country, count in country_count.most_common():
        coords = geocode_location(country)
        if coords and coords not in seen_coords:
            locations.append({
                "name": country,
                "count": count,
                "lat": coords[0],
                "lon": coords[1],
                "type": "country",
            })
            seen_coords.add(coords)

    return locations


def get_detention_centers_from_docs(
    torture_detention_centers: Counter,
) -> list[dict[str, Any]]:
    """
    Match detention center mentions from documents to known centers.
    """
    centers = []

    for center_data in DETENTION_CENTERS:
        name_upper = center_data["name"].upper()
        # Check if this center is mentioned in documents
        count = 0
        for doc_center, doc_count in torture_detention_centers.items():
            if name_upper in doc_center.upper() or doc_center.upper() in name_upper:
                count += doc_count
                break

        centers.append({
            **center_data,
            "doc_count": count,
        })

    return centers


def generate_geographic_map(
    city_count: Counter,
    country_count: Counter,
    other_place_count: Counter | None = None,
    torture_detention_centers: Counter | None = None,
    container_id: str = "geographic-map",
    height: str = "600px",
    show_detention_centers: bool = True,
    show_condor_countries: bool = True,
) -> str:
    """
    Generate HTML/JavaScript for an interactive geographic map.

    Args:
        city_count: Counter of city mentions
        country_count: Counter of country mentions
        other_place_count: Counter of other place mentions
        torture_detention_centers: Counter of detention center mentions
        container_id: HTML element ID for the map
        height: CSS height for the container
        show_detention_centers: Whether to show detention center markers
        show_condor_countries: Whether to highlight Operation Condor countries

    Returns:
        HTML string with embedded JavaScript for the map
    """
    # Aggregate locations
    other_count = other_place_count or Counter()
    locations = aggregate_locations(city_count, country_count, other_count)

    # Get detention centers
    detention_centers = []
    if show_detention_centers and torture_detention_centers:
        detention_centers = get_detention_centers_from_docs(torture_detention_centers)

    # Calculate max count for scaling
    max_count = max((loc["count"] for loc in locations), default=1)

    # Prepare data for JavaScript
    locations_json = json.dumps(locations)
    detention_centers_json = json.dumps(detention_centers)
    # Create GeoJSON FeatureCollection for Operation Condor countries
    condor_geojson = {
        "type": "FeatureCollection",
        "features": [CONDOR_COUNTRY_GEOJSON[country] for country in OPERATION_CONDOR_COUNTRIES]
    }
    condor_geojson_json = json.dumps(condor_geojson)

    html = f'''
<div class="map-section">
    <div class="map-controls" style="margin-bottom: 10px; display: flex; gap: 10px; flex-wrap: wrap; align-items: center;">
        <label style="display: flex; align-items: center; gap: 5px; font-size: 12px;">
            <input type="checkbox" id="{container_id}-locations" checked onchange="toggleLayer_{container_id.replace('-', '_')}('locations')">
            Document Locations
        </label>
        <label style="display: flex; align-items: center; gap: 5px; font-size: 12px;">
            <input type="checkbox" id="{container_id}-detention" {"checked" if show_detention_centers else ""} onchange="toggleLayer_{container_id.replace('-', '_')}('detention')">
            Detention Centers
        </label>
        <label style="display: flex; align-items: center; gap: 5px; font-size: 12px;">
            <input type="checkbox" id="{container_id}-condor" {"checked" if show_condor_countries else ""} onchange="toggleLayer_{container_id.replace('-', '_')}('condor')">
            Operation Condor Countries
        </label>
        <div style="flex: 1;"></div>
        <button onclick="resetMap_{container_id.replace('-', '_')}()" class="map-btn">Reset View</button>
    </div>

    <div id="{container_id}" style="width: 100%; max-width: 100%; height: {height}; border: 1px solid #E5E7EB; border-radius: 8px; overflow: hidden;"></div>

    <div class="map-legend" style="margin-top: 10px; display: flex; gap: 20px; flex-wrap: wrap; font-size: 12px;">
        <span style="display: flex; align-items: center; gap: 5px;">
            <span style="width: 16px; height: 16px; background: #3B82F6; border-radius: 50%; opacity: 0.7;"></span>
            Document mentions (size = frequency)
        </span>
        <span style="display: flex; align-items: center; gap: 5px;">
            <span style="width: 16px; height: 16px; background: #DC2626; border-radius: 50%;"></span>
            Detention/Torture centers
        </span>
        <span style="display: flex; align-items: center; gap: 5px;">
            <span style="width: 20px; height: 12px; background: rgba(239, 68, 68, 0.1); border: 2px solid #EF4444;"></span>
            Operation Condor countries
        </span>
    </div>
</div>

<style>
.map-btn {{
    padding: 6px 12px;
    background: #E5E7EB;
    color: #374151;
    border: 1px solid #D1D5DB;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}}
.map-btn:hover {{
    background: #D1D5DB;
}}
</style>

<link rel="stylesheet" href="{LEAFLET_CSS}" />
<script src="{LEAFLET_JS}"></script>

<script>
(function() {{
    // Initialize map centered on South America
    const map_{container_id.replace('-', '_')} = L.map('{container_id}').setView([-25, -60], 3);

    // Add tile layer (OpenStreetMap)
    L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png', {{
        attribution: '© OpenStreetMap contributors',
        maxZoom: 18
    }}).addTo(map_{container_id.replace('-', '_')});

    const locations = {locations_json};
    const detentionCenters = {detention_centers_json};
    const condorGeoJSON = {condor_geojson_json};
    const maxCount = {max_count};

    // Layer groups
    const locationLayer = L.layerGroup();
    const detentionLayer = L.layerGroup();
    const condorLayer = L.layerGroup();

    // Add location markers
    locations.forEach(loc => {{
        const radius = Math.max(8, Math.min(40, 8 + (loc.count / maxCount) * 32));
        const marker = L.circleMarker([loc.lat, loc.lon], {{
            radius: radius,
            fillColor: '#3B82F6',
            color: '#1D4ED8',
            weight: 2,
            opacity: 1,
            fillOpacity: 0.6
        }});
        marker.bindPopup(`
            <strong>${{loc.name}}</strong><br>
            ${{loc.count.toLocaleString()}} document mentions<br>
            <small>Type: ${{loc.type}}</small>
        `);
        marker.bindTooltip(loc.name, {{permanent: false, direction: 'top'}});
        locationLayer.addLayer(marker);
    }});

    // Add detention center markers
    detentionCenters.forEach(center => {{
        const marker = L.marker([center.coords[0], center.coords[1]], {{
            icon: L.divIcon({{
                className: 'detention-marker',
                html: '<div style="background: #DC2626; width: 12px; height: 12px; border-radius: 50%; border: 2px solid white; box-shadow: 0 2px 4px rgba(0,0,0,0.3);"></div>',
                iconSize: [16, 16],
                iconAnchor: [8, 8]
            }})
        }});
        let popup = `<strong>${{center.name}}</strong><br>${{center.city}}<br><small>${{center.description}}</small>`;
        if (center.doc_count > 0) {{
            popup += `<br><em>${{center.doc_count}} document mentions</em>`;
        }}
        marker.bindPopup(popup);
        marker.bindTooltip(center.name, {{permanent: false, direction: 'top'}});
        detentionLayer.addLayer(marker);
    }});

    // Operation Condor country boundaries (GeoJSON polygons)
    L.geoJSON(condorGeoJSON, {{
        style: {{
            color: '#EF4444',
            weight: 2,
            fillColor: '#EF4444',
            fillOpacity: 0.1
        }},
        onEachFeature: function(feature, layer) {{
            layer.bindPopup(`<strong>${{feature.properties.name}}</strong><br>Operation Condor member state`);
        }}
    }}).addTo(condorLayer);

    // Add layers to map (condor countries first so they're behind markers)
    {'condorLayer.addTo(map_' + container_id.replace('-', '_') + ');' if show_condor_countries else ''}
    locationLayer.addTo(map_{container_id.replace('-', '_')});
    {'detentionLayer.addTo(map_' + container_id.replace('-', '_') + ');' if show_detention_centers else ''}

    // Layer toggle functions
    window.toggleLayer_{container_id.replace('-', '_')} = function(layer) {{
        const checkbox = document.getElementById('{container_id}-' + layer);
        if (layer === 'locations') {{
            if (checkbox.checked) {{
                map_{container_id.replace('-', '_')}.addLayer(locationLayer);
            }} else {{
                map_{container_id.replace('-', '_')}.removeLayer(locationLayer);
            }}
        }} else if (layer === 'detention') {{
            if (checkbox.checked) {{
                map_{container_id.replace('-', '_')}.addLayer(detentionLayer);
            }} else {{
                map_{container_id.replace('-', '_')}.removeLayer(detentionLayer);
            }}
        }} else if (layer === 'condor') {{
            if (checkbox.checked) {{
                map_{container_id.replace('-', '_')}.addLayer(condorLayer);
            }} else {{
                map_{container_id.replace('-', '_')}.removeLayer(condorLayer);
            }}
        }}
    }};

    // Reset view
    window.resetMap_{container_id.replace('-', '_')} = function() {{
        map_{container_id.replace('-', '_')}.setView([-25, -60], 3);
    }};
}})();
</script>
'''

    return html
