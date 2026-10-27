"""
Golden Curriculum Seed — Pak Guru (Wave 25)
Perpetual Learning Engine untuk RakitDigital.
Sumber kurikulum terkurasi dari daftar repo terkurasi Founder.
HANYA public info, HANYA fetch via raw.githubusercontent.com atau domain docs di-whitelist.
"""
from typing import TypedDict


class CurriculumSource(TypedDict):
    business_type: str
    reference: str
    url: str


# ============================================================
# CURRICULUM SOURCES — Hardcoded seed dari daftar terkurasi Founder
# 14+ entri minimal, semua URL ke raw.githubusercontent.com
# ============================================================

CURRICULUM_SOURCES: list[CurriculumSource] = [
    {
        "business_type": "retail",
        "reference": "Loystar POS",
        "url": "https://raw.githubusercontent.com/loystar/POS-System/main/README.md",
    },
    {
        "business_type": "fnb",
        "reference": "Restaurant WebApp",
        "url": "https://raw.githubusercontent.com/ipenywis/restaurant-webapp/main/README.md",
    },
    {
        "business_type": "fnb",
        "reference": "Restaurant Reservation",
        "url": "https://raw.githubusercontent.com/mikheel28/restaurant-reservation/main/README.md",
    },
    {
        "business_type": "booking",
        "reference": "Hotel Management",
        "url": "https://raw.githubusercontent.com/machadop1407/hotel-management-full-stack/main/README.md",
    },
    {
        "business_type": "booking",
        "reference": "Airbnb Clone",
        "url": "https://raw.githubusercontent.com/safak/youtube/main/airbnb-clone/README.md",
    },
    {
        "business_type": "booking",
        "reference": "Calendso Scheduling",
        "url": "https://raw.githubusercontent.com/calendso/calendso/main/README.md",
    },
    {
        "business_type": "gym",
        "reference": "Fitness Tracker",
        "url": "https://raw.githubusercontent.com/machadop1487/Fitness-Tracker-App/main/README.md",
    },
    {
        "business_type": "lms",
        "reference": "Next13 LMS Platform",
        "url": "https://raw.githubusercontent.com/antonioerdeljac/next13-lms-platform/main/README.md",
    },
    {
        "business_type": "retail",
        "reference": "Amazona E-Commerce",
        "url": "https://raw.githubusercontent.com/basir/amazona/main/README.md",
    },
    {
        "business_type": "inventory",
        "reference": "Inventory Management",
        "url": "https://raw.githubusercontent.com/saadpasta/inventory-management-system/main/README.md",
    },
    {
        "business_type": "crm",
        "reference": "Corteza CRM",
        "url": "https://raw.githubusercontent.com/cortezeproject/corteza-server/master/README.md",
    },
    {
        "business_type": "finance",
        "reference": "InvoiceNinja",
        "url": "https://raw.githubusercontent.com/invoiceninja/invoiceninja/develop/README.md",
    },
    {
        "business_type": "analytics",
        "reference": "Metabase BI",
        "url": "https://raw.githubusercontent.com/metabase/metabase/master/README.md",
    },
    {
        "business_type": "health",
        "reference": "Hospital Management",
        "url": "https://raw.githubusercontent.com/shubhammehra4/Hospital-Management-System/main/README.md",
    },
]


# ============================================================
# DOCUMENTATION WHITELIST — Domain yang diizinkan untuk fetch
# ============================================================

DOC_WHITELIST: list[str] = [
    "raw.githubusercontent.com",
    "docs.midtrans.com",
    "docs.xendit.id",
]


# ============================================================
# AI CAPABILITY CATALOG — Roadmap v1.1 (NON-PRICING, referensi saja)
# Untuk Pak Arif & Rina planning v1.1. TIDAK TERHUBUNG KE HARGA.
# ============================================================

AI_CAPABILITY_CATALOG: list[str] = [
    "ai_product_descriptions",
    "ai_feedback_sentiment_analysis",
    "ai_data_visualization_insight",
    "ai_document_processing",
    "ai_code_review_assist",
    "ai_test_generation",
    "ai_documentation_generation",
    "ai_migration_planning",
]