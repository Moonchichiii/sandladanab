"""Site content — single source of truth for template data.

Copy that Jeffery may want to change lives in COPY; images are slot records that
`macros/picture.html` turns into <picture> elements (renditions come from
scripts/render_images.py, which has the same slot names).
"""

from __future__ import annotations

SERVICES: list[dict[str, str]] = [
    {
        "title": "Schakt & markplanering",
        "description": "Noggrant utfört med rätt lutningar och masshantering.",
    },
    {
        "title": "Dränering",
        "description": "Fuktproblem förebyggs med korrekt dimensionerade lösningar.",
    },
    {
        "title": "Fiber-/rör-diken",
        "description": "Precision och dokumentation enligt beställarens krav.",
    },
    {
        "title": "Grävning",
        "description": "Grundläggning, poolgravar och större markarbeten.",
    },
    {
        "title": "Mindre rivning",
        "description": "Vi tar hand om rivning av plattor, fundament och murar.",
    },
    {
        "title": "Maskinuthyrning",
        "description": "Kvalificerad förare medföljer alltid.",
    },
]

# ── Images ───────────────────────────────────────────
# file  = rendition stem in static/assets/images/ (see scripts/render_images.py)
# widths = rendered widths (srcset); ratio = [w, h] of the crop;
# alt = what is in the picture

HERO_IMAGE: dict = {
    "file": "hero-rorlaggning",
    "widths": [768, 1280, 1920],
    "ratio": [3, 2],
    "alt": "Grävmaskin med tiltrotator lägger rör i en schakt intill en byggnad",
}
HERO_SIZES = "(min-width: 900px) 40vw, 100vw"

ABOUT_IMAGE: dict = {
    "file": "om-hytten",
    "widths": [480, 768, 960],
    "ratio": [4, 5],
    "alt": "Grävmaskinens hytt med fyra arbetslampor – och hunden i förarstolen",
}
ABOUT_SIZES = "(min-width: 48rem) 40vw, 100vw"

# slot: lead (2x2), square (1x1), wide (2x1).
# Captions say what the work is; alt says what is in the picture.
GALLERY_ITEMS: list[dict] = [
    {
        "slot": "lead",
        "file": "galleri-isolering",
        "widths": [768, 1024, 1536],
        "ratio": [1, 1],
        "alt": "Cellplastskiva och rör i en rörgrav intill en betongbrunn",
        "caption": "Isolering och rörläggning i schakt",
    },
    {
        "slot": "square",
        "file": "galleri-maskinstyrning",
        "widths": [480, 768, 1024],
        "ratio": [1, 1],
        "alt": (
            "Vy från hytten över en grundläggning, "
            "med maskinstyrningens skärm i förgrunden"
        ),
        "caption": "Grundläggning med maskinstyrning",
    },
    {
        "slot": "square",
        "file": "galleri-kabelror",
        "widths": [480, 768, 1024],
        "ratio": [1, 1],
        "alt": "Fyra gula kabelskyddsrör i en ledningsgrav",
        "caption": "Kabelskyddsrör i ledningsgrav",
    },
    {
        "slot": "wide",
        "file": "galleri-avloppsror",
        "widths": [768, 1152, 1536],
        "ratio": [2, 1],
        "alt": "Orangea avloppsrör och en svart brunn i en schakt",
        "caption": "Avloppsrör och brunn",
    },
]
GALLERY_SIZES: dict[str, str] = {
    "lead": "(min-width: 48rem) 66vw, 100vw",
    "square": "(min-width: 48rem) 33vw, 50vw",
    "wide": "(min-width: 48rem) 66vw, 100vw",
}

# ── Navigation ───────────────────────────────────────
# Absolute hashes so the links work from /integritet too.
NAV_LINKS: list[dict[str, str]] = [
    {"href": "/#tjanster", "label": "Tjänster"},
    {"href": "/#galleri", "label": "Galleri"},
    {"href": "/#om", "label": "Om oss"},
    {"href": "/#offert", "label": "Offert"},
]

# ── Copy ─────────────────────────────────────────────
# Sentences marked (förslag) are proposed in the v2 refresh; confirm them with Jeffery.
COPY: dict[str, str] = {
    "hero_h1": "Anläggningsjobb när du behöver det.",
    "hero_lead": "Punktliga leveranser · Försäkrat arbete · Erfaren förare",
    "services_h2": "Markarbeten, från schakt till färdig yta.",  # (förslag)
    "gallery_h2": "Från våra arbetsplatser.",  # (förslag)
    "gallery_lead": "Riktiga jobb på västkusten – inga arkivbilder.",  # (förslag)
    # (förslag - stämmer det?)
    "about_h2": "Du pratar direkt med den som kör maskinen.",
    "about_body": (
        "Sandlådan AB är ett anläggningsföretag i Göteborg som utför grävmaskinsjobb "
        "på konsultbasis – för byggföretag, fastighetsägare och privatpersoner på "
        "västkusten. Egen maskin, egen förare och korta beslutsvägar."
    ),  # (förslag)
    "offert_h2": "Beskriv jobbet – vi hör av oss, oftast samma dag.",
    "offert_lead": (
        "Formuläret går direkt till oss. "
        "Vi ringer upp och bokar platsbesök om det behövs."
    ),
    "consent": (
        "Genom att skicka formuläret godkänner du att vi behandlar dina uppgifter "
        "för att kunna återkomma med offert. Inga uppgifter används i "
        "marknadsföringssyfte och delas inte med tredje part."
    ),
    "footer_contact": "Beskriv jobbet i formuläret så ringer vi upp dig.",
    "footer_contact_phone": "Ring, eller beskriv jobbet i formuläret så ringer vi dig.",
    "footer_blurb": (
        "Grävmaskinsjobb och anläggningsarbeten på konsultbasis. Göteborg med omnejd."
    ),
}

PRIVACY_UPDATED = "2026-09-21"
