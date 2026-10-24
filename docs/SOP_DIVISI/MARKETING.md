# SOP DIVISI MARKETING — Akuisisi & Brand RakitDigital

## 1. TUJUAN
Merancang dan mengeksekusi strategi akuisisi klien UMKM yang etis, realistis, dan lolos quality gate. Fokus pada Micro-SaaS UMKM: Kasir, Stok, Laporan Harian.

## 2. LINGKUP
- **Agen**: Rina (Strategy & Acquisition), Citra (Content - jika ada), Sinta (Growth - jika ada), Lina (Content Execution).
- **Output**: Marketing Plan, Positioning Doc, ICP Definition, Battlecards, A/B Test Design, Lead List, Partnership Evaluation, Copy Assets (Iklan, Email, Landing Page).

## 3. PROSEDUR

### 3.1 Campaign Planning (8-Step Workflow)
1. **Define Objectives** — SMART goal: MQL target, CPL target, conversion target.
2. **Identify Audience** — Gunakan ICP Definition (firmographics, technographics, psychographics, buyer personas).
3. **Develop Strategy** — Channel mix, messaging pillars, funnel stages.
4. **Create Assets** — Copy iklan, email sequence, landing page copy (semua via Lina).
5. **Plan Execution** — Timeline, budget allocation, resource assignment.
6. **Set Measurement** — KPI: CPL, CAC, Conversion Rate, MQL to SQL rate.
7. **Launch** — Hanya setelah review Lina + approval Founder.
8. **Analyze** — Post-campaign review, winner determination, lesson learned → corporate memory.

### 3.2 Positioning (April Dunford 6-Step)
1. **List Alternatives** — Apa yang klien pakai sekarang? (BukuWarung, MokaPOS, KasirAja, manual Excel).
2. **Isolate Unique Attributes** — QRIS terintegrasi, Akuntansi otomatis, Multi-cabang, Harga transparan.
3. **Map to Value** — "Hemat 2 jam admin sehari", "Tidak pernah salah hitung stok", "Bisa cek omzet dari HP".
4. **Define Best-Fit Customers** — UMKM Retail 10-50 karyawan, omzet 1-5M/bulan, pakai POS manual.
5. **Nail Market Category** — "Micro-SaaS Kasir & Stok untuk UMKM Indonesia".
6. **Layer Trends** — QRIS mandatory, E-invoicing Pajak, Digitalisasi UMKM.

### 3.3 Lead Generation Ethics (NON-NEGOTIABLE)
- **HANYA** API resmi/direktori ber-izin: Google Places API, direktori ber-izin Kemenkop.
- **DILARANG KERAS**: Scraping (etika + hukum + IP block risk).
- **Mock Interface**: `generate_leads_etis()` return dummy leads untuk development.
- **Output**: LeadGenRecord dengan source="mock_api_resmi" atau "api_resmi_berizin".

### 3.4 Partnership Evaluation
| Kriteria | Bobot | Threshold |
|----------|-------|-----------|
| Cost (0-100) | 25% | |
| Reliability (0-100) | 25% | |
| Support (0-100) | 25% | |
| Integration Ease (0-100) | 25% | |
| **Total Score** | **100%** | **≥ 70 = RECOMMENDED** / **< 70 = REJECTED** |

Partner Types: PAYMENT_GATEWAY, HOSTING, AGENCY.

### 3.5 A/B Testing Framework
- **Design**: Variant A vs B, metric (CTR/Conversion), sample size per variant.
- **Execute**: Run via campaign channels.
- **Analyze**: Winner determination dengan 5% significance threshold.
- **Decision**: Winner = A/B/TIE (selisih < 5% = TIE).

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Budget kampanye > Rp 1.000.000 | Founder | < 4 jam |
| Campaign launch tanpa review Lina | Rina → Pak Arif | < 1 jam |
| Copy/assets gagal text_quality_gate | Lina rewrite → Rina review | < 30 menit |
| Partnership score borderline (65-74) | Rina → Founder | < 2 jam |
| Lead source legality question | Rina → Bu Ratna (Legal) | < 4 jam |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| MQLs per Bulan | ≥ 50 | CRM pipeline count |
| CPL (Cost Per Lead) | < Rp 50.000 | Total spend / MQLs |
| Conversion Rate (MQL→SQL) | > 15% | SQL count / MQL count |
| Campaign Launch On-Time | 100% | Scheduler vs actual |
| Copy Quality Gate Pass Rate | 100% | Zero violations pre-launch |
| Partnership Evaluation Accuracy | > 80% | Post-partnership review |
| Zero Scraping Violations | 100% | Code audit + source check |