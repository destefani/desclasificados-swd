"""
Historical events database for Chilean dictatorship timeline visualization.

This module contains key historical events from 1970-1991 that provide
context for the declassified CIA documents. Events are categorized by
significance (major, moderate, minor) and period.
"""

from dataclasses import dataclass
from typing import Literal


@dataclass
class HistoricalEvent:
    """A historical event to annotate on the timeline."""
    date: str  # ISO format YYYY-MM-DD
    name: str  # Short name for display
    description: str  # Longer description for tooltip
    category: Literal["major", "moderate", "minor"]
    period: str  # Historical period grouping


# Key historical events for the Chilean dictatorship period
HISTORICAL_EVENTS: list[HistoricalEvent] = [
    # Pre-Coup Period (1970-1973)
    HistoricalEvent(
        date="1970-09-04",
        name="Allende Wins Election",
        description="Salvador Allende wins presidential election, becoming the first democratically elected Marxist president in the Americas.",
        category="major",
        period="Pre-Coup"
    ),
    HistoricalEvent(
        date="1970-10-22",
        name="Schneider Assassination",
        description="General René Schneider, Chilean Army Commander-in-Chief, assassinated in CIA-linked coup attempt.",
        category="moderate",
        period="Pre-Coup"
    ),
    HistoricalEvent(
        date="1970-11-03",
        name="Allende Inaugurated",
        description="Salvador Allende inaugurated as President of Chile, beginning socialist government.",
        category="moderate",
        period="Pre-Coup"
    ),
    HistoricalEvent(
        date="1973-06-29",
        name="Tanquetazo",
        description="Failed military coup attempt by tank regiment against Allende government.",
        category="moderate",
        period="Pre-Coup"
    ),

    # The Coup (September 1973)
    HistoricalEvent(
        date="1973-09-11",
        name="Military Coup",
        description="Military coup overthrows Allende government. President Allende dies in La Moneda palace. General Pinochet leads military junta.",
        category="major",
        period="Coup"
    ),
    HistoricalEvent(
        date="1973-09-13",
        name="Congress Dissolved",
        description="Military junta dissolves Chilean Congress, ending democratic institutions.",
        category="moderate",
        period="Coup"
    ),

    # Consolidation of Dictatorship (1973-1977)
    HistoricalEvent(
        date="1973-09-20",
        name="Caravan of Death",
        description="Military death squad begins mass executions across Chile, killing at least 97 political prisoners.",
        category="major",
        period="Consolidation"
    ),
    HistoricalEvent(
        date="1974-06-18",
        name="DINA Established",
        description="Dirección de Inteligencia Nacional (DINA) secret police formally established under Manuel Contreras.",
        category="major",
        period="Consolidation"
    ),
    HistoricalEvent(
        date="1974-09-30",
        name="Prats Assassination",
        description="Former Army Commander General Carlos Prats and wife assassinated by DINA car bomb in Buenos Aires.",
        category="moderate",
        period="Consolidation"
    ),
    HistoricalEvent(
        date="1975-11-25",
        name="Operation Condor",
        description="Operation Condor formally established - coordinated intelligence operations between South American dictatorships.",
        category="major",
        period="Consolidation"
    ),
    HistoricalEvent(
        date="1976-09-21",
        name="Letelier Assassination",
        description="Orlando Letelier and Ronni Moffitt assassinated by DINA car bomb in Washington, D.C. Major international incident.",
        category="major",
        period="Consolidation"
    ),
    HistoricalEvent(
        date="1977-08-13",
        name="DINA Dissolved",
        description="DINA dissolved and replaced by CNI (Central Nacional de Informaciones) following international pressure after Letelier assassination.",
        category="moderate",
        period="Consolidation"
    ),

    # International Pressure Era (1977-1983)
    HistoricalEvent(
        date="1978-04-18",
        name="Amnesty Law",
        description="Pinochet regime enacts Amnesty Law (Decreto Ley 2191), granting self-amnesty for human rights crimes 1973-1978.",
        category="moderate",
        period="International Pressure"
    ),
    HistoricalEvent(
        date="1980-09-11",
        name="Constitution Plebiscite",
        description="New constitution approved in controlled plebiscite, institutionalizing Pinochet's rule until 1989.",
        category="major",
        period="International Pressure"
    ),
    HistoricalEvent(
        date="1982-08-01",
        name="Economic Crisis",
        description="Chile defaults on international debt amid severe economic crisis; GDP falls 14%.",
        category="moderate",
        period="International Pressure"
    ),
    HistoricalEvent(
        date="1983-05-11",
        name="First National Protest",
        description="First major national protest against Pinochet regime marks beginning of organized mass opposition.",
        category="moderate",
        period="International Pressure"
    ),

    # Transition Period (1984-1990)
    HistoricalEvent(
        date="1985-03-30",
        name="Caso Degollados",
        description="Three Communist Party members kidnapped and murdered by Carabineros, bodies found with throats slashed.",
        category="moderate",
        period="Transition"
    ),
    HistoricalEvent(
        date="1986-07-02",
        name="Carmen Gloria Quintana",
        description="Rodrigo Rojas and Carmen Gloria Quintana burned alive by military patrol during national protest. Rojas dies.",
        category="moderate",
        period="Transition"
    ),
    HistoricalEvent(
        date="1986-09-07",
        name="Pinochet Assassination Attempt",
        description="FPMR guerrillas ambush Pinochet's motorcade, killing 5 bodyguards. Pinochet escapes with minor injuries.",
        category="moderate",
        period="Transition"
    ),
    HistoricalEvent(
        date="1987-04-01",
        name="Pope John Paul II Visit",
        description="Pope John Paul II visits Chile, meets with opposition and human rights victims, bringing international attention.",
        category="moderate",
        period="Transition"
    ),
    HistoricalEvent(
        date="1988-10-05",
        name="Plebiscite - 'No' Wins",
        description="Chilean citizens vote 'No' to extending Pinochet's rule in historic plebiscite, triggering democratic transition.",
        category="major",
        period="Transition"
    ),
    HistoricalEvent(
        date="1989-12-14",
        name="Aylwin Elected",
        description="Patricio Aylwin wins presidential election, first democratic election since 1970.",
        category="major",
        period="Transition"
    ),
    HistoricalEvent(
        date="1990-03-11",
        name="Return to Democracy",
        description="Pinochet transfers power to Aylwin, ending 17 years of military dictatorship.",
        category="major",
        period="Transition"
    ),

    # Post-Dictatorship (1990-1991)
    HistoricalEvent(
        date="1990-04-25",
        name="Rettig Commission",
        description="National Commission for Truth and Reconciliation (Rettig Commission) created to investigate human rights violations.",
        category="moderate",
        period="Post-Dictatorship"
    ),
    HistoricalEvent(
        date="1991-02-08",
        name="Rettig Report",
        description="Rettig Commission publishes report documenting 2,279 deaths and disappearances during dictatorship.",
        category="major",
        period="Post-Dictatorship"
    ),
]


def get_events_for_year_range(start_year: int, end_year: int) -> list[HistoricalEvent]:
    """Get events within a specific year range."""
    events = []
    for event in HISTORICAL_EVENTS:
        year = int(event.date[:4])
        if start_year <= year <= end_year:
            events.append(event)
    return events


def get_major_events() -> list[HistoricalEvent]:
    """Get only major events for simplified timeline view."""
    return [e for e in HISTORICAL_EVENTS if e.category == "major"]


def events_to_json() -> list[dict]:
    """Convert events to JSON-serializable format for JavaScript."""
    return [
        {
            "date": e.date,
            "name": e.name,
            "description": e.description,
            "category": e.category,
            "period": e.period,
        }
        for e in HISTORICAL_EVENTS
    ]
