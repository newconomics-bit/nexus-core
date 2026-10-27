"""
Pak Guru — Web Learner Agent (Wave 25)
Perpetual Learning Engine untuk RakitDigital.
Fetch sumber publik, ekstrak pola, simpan ke pattern database permanen.
HANYA public info, rate-limited, cache permanen.
"""
import re
import asyncio
import uuid
from datetime import datetime, timezone
from typing import TypedDict
from urllib.parse import urlparse

import httpx

from core.llm_gateway import call_llm
from core.curriculum import CURRICULUM_SOURCES, DOC_WHITELIST
from database import (
    create_pattern,
    create_learning_task,
    get_learning_task,
    update_learning_task,
    get_pending_tasks,
    is_url_learned,
    seed_initial_patterns,
    save_corporate_memory,
)
from models import ClientPattern, LearningTask, LearningTaskStatus, MemoryCategory, MemorySeverity
from core.pii_masker import mask_pii_in_text


class EthicsViolationError(Exception):
    """Raised when fetch violates ethics rules (private, login-wall, outside whitelist)."""
    pass


class WebLearner:
    """Pak Guru — Web Learner Agent."""

    # Feature keyword mapping (deterministic extraction)
    FEATURE_KEYWORDS = {
        "qr_ordering": ["qr order", "qr ordering", "scan qr", "qr code order", "qr menu"],
        "table_management": ["table manag", "meja", "table layout", "floor plan", "seat"],
        "kitchen_display": ["kitchen display", "kds", "bump screen", "dapur", "ticket dapur"],
        "inventory_sync": ["inventory", "stok", "stock sync", "ingredient", "bahan baku"],
        "qris_payment": ["qris", "qr pay", "qr payment"],
        "booking_reservation": ["booking", "reservation", "reservasi", "appointment", "janji temu"],
        "calendar_schedule": ["calendar", "schedule", "jadwal", "kalender", "availability"],
        "membership_tier": ["membership", "member tier", "loyalty", "poin", "tier member"],
        "class_booking": ["class book", "booking class", "kelas", "jadwal kelas"],
        "attendance": ["attendance", "absensi", "kehadiran", "check in", "check-in"],
        "recurring_billing": ["recurring", "berlangganan", "subscription", "auto bill", "tagihan berkala"],
        "retention_offer": ["retention", "churn", "winback", "retensi", "penawaran kembali"],
        "staff_commission": ["commission", "komisi", "staff pay", "gaji staff", "komisi stylist"],
        "booking_per_chair": ["per chair", "per kursi", "chair booking", "kursi booking"],
        "audit_log": ["audit log", "audit trail", "log aktivitas", "activity log"],
        "pos_interface": ["pos interface", "pos ui", "kasir", "cashier"],
        "barcode_scan": ["barcode", "scan barcode", "qr scan", "scan produk"],
        "stock_auto_deduct": ["auto deduct", "otomatis kurangi", "stock deduct", "stok otomatis"],
        "receipt_print": ["receipt", "struk", "print struk", "cetak struk"],
        "dashboard_analytics": ["dashboard", "analytics", "report", "laporan", "visualisasi"],
        "chat_realtime": ["chat", "realtime", "websocket", "notifikasi realtime", "live chat"],
    }

    PAYMENT_KEYWORDS = {
        "qris": ["qris"],
        "va": ["virtual account", "va ", "va-"],
        "gopay": ["gopay", "go-pay"],
        "ovo": ["ovo"],
        "dana": ["dana "],
        "stripe": ["stripe"],
        "midtrans": ["midtrans"],
        "xendit": ["xendit"],
    }

    def __init__(self):
        self.client = httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=5.0))

    async def close(self):
        await self.client.aclose()

    # ---------------------------------------------------------
    # Ethics & Fetch
    # ---------------------------------------------------------
    def _is_allowed_domain(self, url: str) -> bool:
        """Check if domain is in whitelist or raw.githubusercontent.com."""
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        if domain == "raw.githubusercontent.com":
            return True
        for allowed in DOC_WHITELIST:
            if allowed in domain:
                return True
        return False

    async def _check_robots_txt(self, url: str) -> bool:
        """Check robots.txt for non-GitHub-raw domains (mockable)."""
        parsed = urlparse(url)
        domain = parsed.netloc
        if domain == "raw.githubusercontent.com":
            return True  # GitHub raw allows
        # For other domains, fetch robots.txt
        try:
            robots_url = f"{parsed.scheme}://{domain}/robots.txt"
            resp = await self.client.get(robots_url, timeout=5.0)
            if resp.status_code == 200:
                content = resp.text.lower()
                if "disallow: /" in content and "user-agent: *" in content:
                    return False
        except Exception:
            pass  # If can't fetch robots.txt, assume allowed (conservative)
        return True

    def _detect_login_wall(self, response: httpx.Response) -> bool:
        """Detect if response indicates login wall."""
        if response.status_code in (401, 403):
            return True
        content = response.text.lower()
        login_indicators = [
            "login", "sign in", "signin", "password", "username",
            "auth", "oauth", "sso", "masuk", "daftar", "register"
        ]
        # Check for login form
        if any(ind in content for ind in login_indicators):
            if "<form" in content or "<input" in content:
                return True
        return False

    async def fetch_public(self, url: str) -> str:
        """
        Fetch public content with ethics checks.
        Raises EthicsViolationError if not allowed.
        """
        # Domain whitelist check
        if not self._is_allowed_domain(url):
            raise EthicsViolationError(f"Domain not in whitelist: {url}")

        # Check robots.txt
        if not await self._check_robots_txt(url):
            raise EthicsViolationError(f"robots.txt disallows: {url}")

        # Fetch with rate limiting handled by caller
        response = await self.client.get(url, follow_redirects=True)
        
        # Detect login wall
        if self._detect_login_wall(response):
            raise EthicsViolationError(f"Login wall detected: {url}")

        response.raise_for_status()
        return response.text

    # ---------------------------------------------------------
    # Deterministic Feature Extraction
    # ---------------------------------------------------------
    def extract_features(self, text: str, business_type: str) -> dict:
        """Deterministic keyword-based feature extraction."""
        text_lower = text.lower()
        features = {}
        
        for feat_key, keywords in self.FEATURE_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    features[feat_key] = True
                    break
        
        # Payment methods detection
        payment_methods = []
        for pm_key, keywords in self.PAYMENT_KEYWORDS.items():
            for kw in keywords:
                if kw in text_lower:
                    payment_methods.append(pm_key)
                    break
        
        # User flow inference (deterministic per business_type)
        user_flow = self._infer_user_flow(business_type, features)
        
        return {
            "features": features,
            "payment_methods": payment_methods,
            "user_flow": user_flow,
        }

    def _infer_user_flow(self, business_type: str, features: dict) -> list[str]:
        """Infer standard user flow per business type (deterministic fallback)."""
        if business_type in ("fnb", "cafe", "restoran"):
            base = ["scan_qr", "view_menu", "add_to_cart", "checkout", "order_tracking"]
            if features.get("table_management"):
                base.insert(1, "select_table")
            if features.get("kitchen_display"):
                base.insert(-1, "kitchen_prep")
            return base
        elif business_type in ("booking", "hotel"):
            return ["search", "view_detail", "select_date", "book", "confirmation"]
        elif business_type == "gym":
            return ["view_classes", "book_class", "check_in", "workout_log", "progress"]
        elif business_type == "salon":
            return ["view_services", "book_appointment", "service", "checkout", "review"]
        elif business_type == "retail":
            return ["browse", "search", "add_to_cart", "checkout", "pickup_delivery"]
        elif business_type == "lms":
            return ["browse_courses", "enroll", "watch_lesson", "quiz", "certificate"]
        else:
            return ["view", "select", "checkout", "confirm"]

    def compute_complexity(self, features: dict) -> tuple[int, int]:
        """Deterministic complexity score (1-10) and estimated build hours."""
        feat_count = len(features)
        # Formula: 1 + feature_count, capped at 10
        complexity = min(1 + feat_count, 10)
        # Estimated hours: complexity * 5 + 5
        estimated_hours = complexity * 5 + 5
        return complexity, estimated_hours

    # ---------------------------------------------------------
    # LLM Normalization (Graceful)
    # ---------------------------------------------------------
    async def normalize_with_llm(self, raw_text: str, extracted: dict) -> str:
        """Use LLM to create a 2-sentence summary from raw text + extracted features."""
        system_prompt = (
            "Kamu Pak Guru, ahli ringkasan teknis. Buat 2 kalimat singkat, profesional, "
            "Indonesia 'tongkrongan bisnis' untuk founder. Input: teks mentah + fitur terstruktur. "
            "Output: HANYA 2 kalimat. Tanpa emoji, tanpa slop, tanpa janji berlebihan."
        )
        user_prompt = f"Teks: {raw_text[:2000]}\nFitur: {extracted}"
        try:
            summary = await call_llm("deepseek/deepseek-chat-v3-0324", system_prompt, user_prompt)
            # Quality gate
            from agents.text_quality_gate import enforce
            should_send, msg = enforce(summary)
            if should_send:
                return summary.strip()
        except Exception:
            pass
        # Graceful fallback: use extracted features to make deterministic summary
        feat_names = list(extracted.get("features", {}).keys())
        if feat_names:
            return f"Pola {extracted.get('business_type', 'umum')} terdeteksi dengan fitur: {', '.join(feat_names[:5])}. Estimasi kompleksitas menengah."
        return "Pola bisnis terdeteksi, detail fitur di database."

    # ---------------------------------------------------------
    # Main Learning Pipeline
    # ---------------------------------------------------------
    async def learn_from_url(self, url: str, business_type: str, reference_company: str) -> ClientPattern:
        """Complete learning pipeline: fetch -> extract -> compute -> save."""
        # Fetch
        raw_text = await self.fetch_public(url)
        
        # Extract features deterministically
        extracted = self.extract_features(raw_text, business_type)
        
        # Compute complexity & hours
        complexity, est_hours = self.compute_complexity(extracted["features"])
        
        # LLM normalization for summary (graceful)
        summary = await self.normalize_with_llm(raw_text, {**extracted, "business_type": business_type})
        
        # Create pattern
        now = datetime.now(timezone.utc).isoformat()
        pattern_id = str(uuid.uuid4())
        
        # Determine pricing tiers observed (from text)
        pricing_tiers = self._extract_pricing_tiers(raw_text)
        
        # Tech stack inference (basic)
        tech_stack = self._infer_tech_stack(raw_text)
        
        pattern = ClientPattern(
            pattern_id=pattern_id,
            business_type=business_type,
            reference_company=reference_company,
            features=extracted["features"],
            payment_methods=extracted["payment_methods"],
            user_flow=extracted["user_flow"],
            tech_stack_inferred=tech_stack,
            pricing_tiers_observed=pricing_tiers,
            complexity_score=complexity,
            estimated_build_hours=est_hours,
            source_urls=[url],
            learned_at=now,
            is_active=True,
        )
        
        # Save pattern
        from database import create_pattern
        await create_pattern(pattern)
        
        # Save to corporate memory (append-only)
        from database import save_corporate_memory
        from models import CorporateMemory, MemoryCategory, MemorySeverity
        memory = CorporateMemory(
            memory_id=str(uuid.uuid4()),
            project_id=pattern_id,
            category=MemoryCategory.BUSINESS_PATTERN,
            lesson_text=f"Learned {business_type} pattern from {reference_company}: {summary}. Features: {list(extracted['features'].keys())}. Complexity: {complexity}/10. Est. build: {est_hours}h.",
            severity=MemorySeverity.MEDIUM,
            target_agent=self._get_target_agent(business_type),
            created_at=now,
        )
        await save_corporate_memory(memory)
        
        return pattern

    def _extract_pricing_tiers(self, text: str) -> list[str]:
        """Extract observed pricing tier keywords (observation only)."""
        text_lower = text.lower()
        tiers = []
        tier_keywords = ["basic", "pro", "premium", "enterprise", "paket", "plan", "tier", "starter", "professional", "business"]
        for kw in tier_keywords:
            if kw in text_lower:
                tiers.append(kw)
        return tiers

    def _infer_tech_stack(self, text: str) -> dict:
        """Basic tech stack inference from keywords."""
        text_lower = text.lower()
        stack = {}
        tech_keywords = {
            "frontend": ["react", "vue", "next.js", "nextjs", "svelte", "angular"],
            "backend": ["node", "express", "fastapi", "django", "laravel", "go", "golang", "spring", "rails"],
            "database": ["postgres", "postgresql", "mysql", "mongodb", "redis", "sqlite", "supabase", "prisma", "drizzle"],
            "infra": ["docker", "kubernetes", "k8s", "aws", "gcp", "azure", "vercel", "netlify", "railway"],
        }
        for cat, keywords in tech_keywords.items():
            for kw in keywords:
                if kw in text_lower:
                    stack[cat] = kw
                    break
        return stack

    def _get_target_agent(self, business_type: str) -> str:
        """Map business type to target agent for memory injection."""
        mapping = {
            "fnb": "sari",
            "cafe": "sari",
            "restoran": "sari",
            "booking": "sari",
            "hotel": "sari",
            "gym": "sari",
            "salon": "sari",
            "retail": "sari",
            "lms": "sari",
            "inventory": "mas_eko",
            "crm": "mas_eko",
            "finance": "pak_harto",
            "analytics": "pak_arif",
            "health": "mas_eko",
        }
        return mapping.get(business_type, "sari")

    # ---------------------------------------------------------
    # Curriculum Batch Runner
    # ---------------------------------------------------------
    async def run_curriculum_batch(self, max_fetch: int = 5) -> list[dict]:
        """Run learning on up to max_fetch unlearned curriculum sources."""
        # Seed initial patterns first
        from database import seed_initial_patterns
        await seed_initial_patterns()
        
        results = []
        fetched = 0
        
        for source in CURRICULUM_SOURCES:
            if fetched >= max_fetch:
                break
            
            url = source["url"]
            
            # Permanent cache check
            if await is_url_learned(url):
                results.append({
                    "url": url,
                    "reference": source["reference"],
                    "status": "SKIPPED_CACHED",
                })
                continue
            
            # Rate limiting: 1 second between fetches
            if fetched > 0:
                await asyncio.sleep(1)
            
            try:
                pattern = await self.learn_from_url(url, source["business_type"], source["reference"])
                results.append({
                    "url": url,
                    "reference": source["reference"],
                    "pattern_id": pattern.pattern_id,
                    "business_type": pattern.business_type,
                    "complexity": pattern.complexity_score,
                    "est_hours": pattern.estimated_build_hours,
                    "status": "COMPLETED",
                })
                fetched += 1
            except EthicsViolationError as e:
                results.append({
                    "url": url,
                    "reference": source["reference"],
                    "status": "ETHICS_BLOCKED",
                    "error": str(e),
                })
            except Exception as e:
                results.append({
                    "url": url,
                    "reference": source["reference"],
                    "status": "FAILED",
                    "error": str(e),
                })
        
        return results


# Singleton instance
_web_learner_instance = None


async def get_web_learner() -> WebLearner:
    global _web_learner_instance
    if _web_learner_instance is None:
        _web_learner_instance = WebLearner()
    return _web_learner_instance


async def run_curriculum_batch(max_fetch: int = 5) -> list[dict]:
    """Convenience function for scheduler."""
    learner = await get_web_learner()
    return await learner.run_curriculum_batch(max_fetch)


async def execute_learning_task(task_id: str) -> dict:
    """Execute a specific learning task by ID."""
    task = await get_learning_task(task_id)
    if not task:
        return {"status": "NOT_FOUND", "task_id": task_id}
    
    # Mark in progress
    task.status = LearningTaskStatus.IN_PROGRESS
    await update_learning_task(task)
    
    learner = await get_web_learner()
    try:
        pattern = await learner.learn_from_url(task.target_url, task.business_type, task.reference_company)
        task.status = LearningTaskStatus.COMPLETED
        task.extracted_summary = {
            "pattern_id": pattern.pattern_id,
            "features": list(pattern.features.keys()),
            "complexity": pattern.complexity_score,
            "est_hours": pattern.estimated_build_hours,
        }
        task.completed_at = datetime.now(timezone.utc).isoformat()
        await update_learning_task(task)
        return {"status": "COMPLETED", "pattern_id": pattern.pattern_id}
    except EthicsViolationError as e:
        task.status = LearningTaskStatus.FAILED
        task.error_message = f"Ethics violation: {str(e)}"
        task.completed_at = datetime.now(timezone.utc).isoformat()
        await update_learning_task(task)
        return {"status": "FAILED", "error": str(e)}
    except Exception as e:
        task.status = LearningTaskStatus.FAILED
        task.error_message = str(e)
        task.completed_at = datetime.now(timezone.utc).isoformat()
        await update_learning_task(task)
        return {"status": "FAILED", "error": str(e)}