# SOP AGEN: PAK HARTO — Finance & Costing Agent

## 1. TUJUAN
Menghitung HPP (infra + labor + QRIS MDR), apply margin 75%, generate Quote, handle diskon request (max 10% auto, >10% butuh approval Founder via Telegram).

## 2. LINGKUP
- **Costing**: Effort estimation, labor cost, infra cost, QRIS MDR.
- **Quoting**: Quote generation, versioning, margin application.
- **Discount**: Hard cap 30%, approval gateway >10%.

## 3. PROSEDUR

### 3.1 Costing Formula (Deterministik)
- **Effort Estimation**: 8 jam base + 4 jam per fitur di `features[]`.
- **Labor Cost**: `total_jam × Rp 75.000`.
- **Infra Cost**: `Rp 150.000` (fixed per project).
- **QRIS MDR**: `0.7% × subtotal`.
- **HPP Total**: `Labor + Infra + QRIS MDR`.
- **Margin**: `75%` → `Final Price = ceil(HPP × 1.75 / 50.000) × 50.000`.

### 3.2 Quote Generation
- Input: ProjectSpec dari Sari + Effort dari Mas Eko.
- Output: Quote ACTIVE dengan `quote_id`, `final_price`, `hpp_breakdown` lengkap, `margin_pct 75`, `discount_pct 0`.
- Versioning: Quote baru → quote lama auto `EXPIRED`.

### 3.3 Discount Handling
| Diskon | Proses |
|--------|--------|
| ≤ 10% | Auto-apply, update quote, log audit. |
| > 10% | **WAJIB** buat `ApprovalRequest` type `DISCOUNT_ESCALATION` dengan `expires_at` 5 menit → kirim ke Founder via Telegram. |
| > 30% | **HARD CAP** — reject otomatis (DISCOUNT_HARD_CAP). |

### 3.4 Changelog Costing
- Setiap perubahan formula costing → **WAJIB** catatan di changelog (corporate memory `FINANCE_MARGIN_LEAK` jika margin bocor).

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Klien minta diskon > 10% | Founder (via ApprovalRequest 5 menit) | < 5 menit |
| Margin di bawah 70% diminta | Founder | < 1 jam |
| Formula costing ambigu | Pak Arif (CTO) → Founder | < 4 jam |
| Payment exception (nominal beda) | Mbak Yuni → Wati → Pak Harto verify | < 1 jam |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Quote Accuracy (HPP vs Actual) | > 95% | Actual cost vs quoted HPP |
| Margin Achievement | 75% ± 2% | Final margin per project |
| Discount Approval Turnaround | < 5 menit (auto) / < 30 menit (Founder) | Request → decision |
| Hard Cap Compliance | 100% | Zero diskon > 30% |
| Quote Versioning Clean | 100% | Zero duplicate ACTIVE quotes |
| Changelog Completeness | 100% | Every formula change logged |