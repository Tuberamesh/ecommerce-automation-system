import os
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOCAL_DATABASE_PATH = PROJECT_ROOT / "database" / "ecommerce.db"
DEPLOYMENT_DATABASE_PATH = PROJECT_ROOT / "database" / "deployment_ecommerce.db"

DEFAULT_DATABASE_PATH = (
    LOCAL_DATABASE_PATH
    if LOCAL_DATABASE_PATH.is_file()
    else DEPLOYMENT_DATABASE_PATH
)

DATABASE_PATH = Path(
    os.environ.get("OLIST_DATABASE_PATH", str(DEFAULT_DATABASE_PATH))
).expanduser()

if not DATABASE_PATH.is_absolute():
    DATABASE_PATH = (PROJECT_ROOT / DATABASE_PATH).resolve()

PRODUCT_NAME = "Olist Commerce Intelligence"
PRODUCT_SUBTITLE = "Brazilian Marketplace Performance & Operations Analytics"
CURRENCY_CONTEXT = "Brazilian real (BRL; symbol R$)"

PAGE_NAMES = (
    "Executive Overview",
    "Sales Analytics",
    "Product Intelligence",
    "Customer Intelligence",
    "Payments & Operations",
    "Order Explorer",
)

PAGE_COPY = {
    "Executive Overview": (
        "Executive Overview",
        "A snapshot of delivered sales and marketplace performance.",
    ),
    "Sales Analytics": (
        "Sales Analytics",
        "Explore revenue trends and regional demand.",
    ),
    "Product Intelligence": (
        "Product Intelligence",
        "Understand category and product performance.",
    ),
    "Customer Intelligence": (
        "Customer Intelligence",
        "Explore customer distribution and review patterns.",
    ),
    "Payments & Operations": (
        "Payments & Operations",
        "Understand payment behaviour and delivery performance.",
    ),
    "Order Explorer": (
        "Order Explorer",
        "Search and inspect individual orders.",
    ),
}

PAGE_EYEBROWS = {
    "Executive Overview": "Marketplace performance",
    "Sales Analytics": "Revenue & demand",
    "Product Intelligence": "Product mix",
    "Customer Intelligence": "Customer experience",
    "Payments & Operations": "Payments & delivery",
    "Order Explorer": "Order-level analysis",
}

COLORS = {
    "ink": "#E6E8EB",
    "muted": "#9AA1AC",
    "primary": "#83B96A",
    "secondary": "#E6B450",
    "accent": "#E6B450",
    "surface": "#181B21",
    "panel": "#181B21",
    "grid": "#262A32",
    "border": "#262A32",
    "palette": ["#83B96A", "#E6B450"],
}
