"""Site content — single source of truth for template data."""

from __future__ import annotations

SERVICES: list[dict[str, str]] = [
    {
        "title": "Schakt & markplanering",
        "description": "Noggrant utfört med rätt lutningar och masshantering.",
    },
    {
        "title": "Dränering",
        "description": ("Fuktproblem förebyggs med korrekt dimensionerade lösningar."),
    },
    {
        "title": "Fiber-/rör-diken",
        "description": ("Precision och dokumentation enligt beställarens krav."),
    },
    {
        "title": "Grävning",
        "description": ("Grundläggning, poolgravar och större markarbeten."),
    },
    {
        "title": "Mindre rivning",
        "description": ("Vi tar hand om rivning av plattor, fundament och murar."),
    },
    {
        "title": "Maskinuthyrning",
        "description": "Kvalificerad förare medföljer alltid.",
    },
]

GALLERY_ITEMS: list[dict[str, str]] = [
    {"name": "Grundgrävning", "id": "1"},
    {"name": "Markplanering", "id": "2"},
    {"name": "Dräneringsjobb", "id": "3"},
    {"name": "Ledningsförläggning", "id": "4"},
    {"name": "Schaktarbete", "id": "5"},
    {"name": "Färdigställt projekt", "id": "6"},
]

NAV_LINKS: list[dict[str, str]] = [
    {"href": "#tjanster", "label": "Tjänster"},
    {"href": "#galleri", "label": "Galleri"},
    {"href": "#offert", "label": "Offert"},
]
