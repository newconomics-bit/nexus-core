"""
Consultation Matrix & Modular Pricing Engine
Deterministic pricing logic for RakitDigital consultative sales.
NO LLM pricing - all hardcoded in Python dicts.
"""
from typing import TypedDict


class HiddenRequirement(TypedDict):
    name: str
    reason: str


class BusinessPattern(TypedDict):
    base_tier: str
    hidden_requirements: list[HiddenRequirement]
    upsell_script: str


class AddOnModule(TypedDict):
    name: str
    setup_fee: int
    monthly: int


# ============================================================
# BUSINESS PATTERNS - Deterministic consultation matrix
# ============================================================

BUSINESS_PATTERNS: dict[str, BusinessPattern] = {
    "cafe": {
        "base_tier": "Paket Tumbuh",
        "hidden_requirements": [
            {
                "name": "Kitchen Display System (KDS)",
                "reason": "Pesanan masuk dapur otomatis, kurangi error manual.",
            },
            {
                "name": "Manajemen Meja Real-time",
                "reason": "Cegah double order & optimize turnover meja.",
            },
        ],
        "upsell_script": "Berdasarkan pengalaman kami, sistem QR Ordering butuh KDS dan Manajemen Meja agar operasional lancar. Apakah Bapak sekalian ambil Paket Jaya untuk dashboard Margin Real-time?",
    },
    "salon": {
        "base_tier": "Paket Tumbuh",
        "hidden_requirements": [
            {
                "name": "Manajemen Membership & Diskon",
                "reason": "Retensi pelanggan dengan poin & tier loyalty.",
            },
            {
                "name": "Komisi Stylist Otomatis",
                "reason": "Transparansi gaji & kurangi dispute komisi.",
            },
        ],
        "upsell_script": "Salon butuh sistem Membership agar pelanggan kembali, dan komisi otomatis biar stylist nyaman. Paket Jaya sudah include dashboard performa stylist real-time. Mau coba?",
    },
    "retail": {
        "base_tier": "Paket Tumbuh",
        "hidden_requirements": [
            {
                "name": "Multi-Gudang & Transfer Stok",
                "reason": "Sinkron stok antar cabang & warehouse.",
            },
            {
                "name": "Auto-Reorder Point",
                "reason": "Pesan otomatis saat stok di bawah minimum.",
            },
        ],
        "upsell_script": "Retail multi-cabang butuh visibilitas stok real-time. Paket Jaya punya Multi-Gudang & Auto-Reorder. Biar gak pernah kehabisan stok best-seller.",
    },
    "distributor": {
        "base_tier": "Paket Tumbuh",
        "hidden_requirements": [
            {
                "name": "Manajemen Sales Order & Delivery",
                "reason": "Track order dari salesman ke delivery.",
            },
            {
                "name": "Piutang & Tagihan Otomatis",
                "reason": "Kolektibilitas piutang real-time per customer.",
            },
        ],
        "upsell_script": "Distributor butuh kontrol piutang ketat. Paket Jaya include aging report & auto-reminder tagihan. Cashflow jadi lebih predictable.",
    },
    "restoran": {
        "base_tier": "Paket Tumbuh",
        "hidden_requirements": [
            {
                "name": "Kitchen Display System (KDS)",
                "reason": "Pesanan masuk dapur otomatis, kurangi error manual.",
            },
            {
                "name": "Manajemen Meja Real-time",
                "reason": "Cegah double order & optimize turnover meja.",
            },
            {
                "name": "Split Bill & Service Charge",
                "reason": "Kelola service charge & split bill otomatis.",
            },
        ],
        "upsell_script": "Restoran butuh KDS, Manajemen Meja, dan Split Bill. Paket Jaya sudah lengkap dengan Margin Real-time per menu. Biar owner tau item mana yang untung.",
    },
}


# ============================================================
# PACKAGING TIERS - Deterministic base pricing
# ============================================================

PACKAGE_TIERS: dict[str, dict] = {
    "Paket Mulai": {
        "setup_fee": 5_000_000,
        "monthly_fee": 500_000,
        "features": ["Kasir Digital", "Stok Dasar", "Laporan Harian", "QRIS"],
        "max_users": 2,
        "support_level": "Email",
    },
    "Paket Tumbuh": {
        "setup_fee": 10_000_000,
        "monthly_fee": 1_000_000,
        "features": ["Kasir Digital", "Stok Lanjutan", "Laporan Real-time", "QRIS", "Multi-User", "API Basic"],
        "max_users": 5,
        "support_level": "Email + Chat",
    },
    "Paket Jaya": {
        "setup_fee": 20_000_000,
        "monthly_fee": 2_500_000,
        "features": [
            "Semua fitur Tumbuh",
            "Margin Real-time per Item",
            "Multi-Cabang",
            "KDS",
            "Manajemen Meja",
            "Membership",
            "Komisi Staff",
            "API Full",
        ],
        "max_users": 20,
        "support_level": "Dedicated (Telegram + Call)",
    },
}


# ============================================================
# ADD-ON MODULES - Deterministic add-on pricing
# ============================================================

ADD_ON_MODULES: dict[str, AddOnModule] = {
    "membership": {
        "name": "Modul Membership & Loyalty",
        "setup_fee": 1_500_000,
        "monthly": 50_000,
    },
    "staff_commission": {
        "name": "Modul Komisi Staff Otomatis",
        "setup_fee": 1_500_000,
        "monthly": 50_000,
    },
    "kds": {
        "name": "Modul Kitchen Display System (KDS)",
        "setup_fee": 2_000_000,
        "monthly": 100_000,
    },
    "table_management": {
        "name": "Modul Manajemen Meja Real-time",
        "setup_fee": 1_500_000,
        "monthly": 75_000,
    },
    "multi_warehouse": {
        "name": "Modul Multi-Gudang & Transfer Stok",
        "setup_fee": 2_000_000,
        "monthly": 100_000,
    },
    "auto_reorder": {
        "name": "Modul Auto-Reorder Point",
        "setup_fee": 1_000_000,
        "monthly": 50_000,
    },
    "sales_delivery": {
        "name": "Modul Sales Order & Delivery",
        "setup_fee": 2_000_000,
        "monthly": 100_000,
    },
    "receivables": {
        "name": "Modul Piutang & Tagihan Otomatis",
        "setup_fee": 1_500_000,
        "monthly": 75_000,
    },
    "split_bill": {
        "name": "Modul Split Bill & Service Charge",
        "setup_fee": 1_000_000,
        "monthly": 50_000,
    },
}


# ============================================================
# HELPER FUNCTIONS
# ============================================================

def get_business_pattern(business_type: str) -> BusinessPattern | None:
    """Get consultation pattern for a business type (case-insensitive)."""
    return BUSINESS_PATTERNS.get(business_type.lower())


def get_package_tier(tier_name: str) -> dict | None:
    """Get package tier details."""
    return PACKAGE_TIERS.get(tier_name)


def get_add_on_module(module_key: str) -> AddOnModule | None:
    """Get add-on module details."""
    return ADD_ON_MODULES.get(module_key)


def detect_business_type(message: str) -> str | None:
    """Detect business type from client message (simple keyword matching)."""
    message_lower = message.lower()
    type_keywords = {
        "cafe": ["cafe", "kafe", "kopi", "kedaikopi", "warungkopi", "coffee"],
        "salon": ["salon", "klinik kecantikan", "spa", "barbershop", "rambut"],
        "retail": ["retail", "minimarket", "supermarket", "baju", "fashion", "sepatu", "toko baju", "toko sepatu", "toko fashion"],
        "distributor": ["distributor", "agen", "supplier", "grosir", "wholesale"],
        "restoran": ["restoran", "rumah makan", "warteg", "kedai makan", "nasi"],
    }
    for btype, keywords in type_keywords.items():
        if any(kw in message_lower for kw in keywords):
            return btype
    return None


def is_enterprise_request(message: str) -> bool:
    """Detect if request is enterprise/complex (RAKIT-CUSTOM trigger)."""
    message_lower = message.lower()
    enterprise_keywords = [
        "rakit-custom",
        "custom erp",
        "multi-tenant",
        "bloomberg",
        "real-time market",
        "enterprise",
        "saas platform",
        "white label",
        "custom integration",
        "legacy migration",
        "microservices",
        "kubernetes",
        "on-premise",
        "high frequency",
        "trading",
        "fintech core",
    ]
    return any(kw in message_lower for kw in enterprise_keywords)


def generate_consultative_response(business_type: str) -> dict:
    """
    Generate consultative response for a business type.
    Returns dict with script, hidden requirements, and recommended tier.
    """
    pattern = get_business_pattern(business_type)
    if not pattern:
        return {
            "business_type": business_type,
            "recognized": False,
            "message": "Bisnis tipe ini belum punya template konsultasi. Sari akan tanya detail kebutuhan manual.",
        }

    hidden_reqs = pattern["hidden_requirements"]
    req_list = "\n".join([f"- {r['name']}: {r['reason']}" for r in hidden_reqs])

    return {
        "business_type": business_type,
        "recognized": True,
        "base_tier": pattern["base_tier"],
        "hidden_requirements": hidden_reqs,
        "upsell_script": pattern["upsell_script"],
        "consultative_message": (
            f"Bang, untuk bisnis {business_type.capitalize()}, kami sarankan {pattern['base_tier']}.\n\n"
            f"Tapi based on pengalaman kami, biasanya butuh ini juga:\n{req_list}\n\n"
            f"{pattern['upsell_script']}"
        ),
    }


def calculate_quote(base_tier: str, modules: list[str]) -> dict:
    """
    Calculate total quote deterministically.
    Returns dict with setup_fee, monthly_fee, breakdown.
    """
    tier = get_package_tier(base_tier)
    if not tier:
        raise ValueError(f"Unknown tier: {base_tier}")

    total_setup = tier["setup_fee"]
    total_monthly = tier["monthly_fee"]
    module_breakdown = []

    for module_key in modules:
        module = get_add_on_module(module_key)
        if module:
            total_setup += module["setup_fee"]
            total_monthly += module["monthly"]
            module_breakdown.append({
                "module": module_key,
                "name": module["name"],
                "setup_fee": module["setup_fee"],
                "monthly": module["monthly"],
            })

    return {
        "base_tier": base_tier,
        "base_setup_fee": tier["setup_fee"],
        "base_monthly_fee": tier["monthly_fee"],
        "modules": module_breakdown,
        "total_setup_fee": total_setup,
        "total_monthly_fee": total_monthly,
        "currency": "IDR",
    }


# Tier recommendations based on business type
TIER_RECOMMENDATIONS: dict[str, str] = {
    "cafe": "Paket Tumbuh",
    "salon": "Paket Tumbuh",
    "retail": "Paket Tumbuh",
    "distributor": "Paket Tumbuh",
    "restoran": "Paket Tumbuh",
}

DEFAULT_MODULES_BY_TYPE: dict[str, list[str]] = {
    "cafe": ["kds", "table_management"],
    "salon": ["membership", "staff_commission"],
    "retail": ["multi_warehouse", "auto_reorder"],
    "distributor": ["sales_delivery", "receivables"],
    "restoran": ["kds", "table_management", "split_bill"],
}


def get_recommended_config(business_type: str) -> dict:
    """Get recommended tier + modules for a business type."""
    base_tier = TIER_RECOMMENDATIONS.get(business_type, "Paket Tumbuh")
    modules = DEFAULT_MODULES_BY_TYPE.get(business_type, [])
    return calculate_quote(base_tier, modules)