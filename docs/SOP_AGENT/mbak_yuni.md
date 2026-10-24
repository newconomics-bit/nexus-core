# SOP AGEN: MBAK YUNI — Payment & Verification Agent

## 1. TUJUAN
Memverifikasi pembayaran QRIS dinamis: cek reference_code unik, amount == invoice.final_price, invoice masih PENDING. Handle exception (nominal beda, duplicate, invoice tidak pending).

## 2. LINGKUP
- **QRIS Generation**: Dinamis, amount dikunci dari `invoice.amount`.
- **Verification**: Webhook handler, idempoten, exception handling.
- **Output**: Status `VERIFIED` / `EXCEPTION` / `DUPLICATE`.

## 3. PROSEDUR

### 3.1 QRIS Generation
- Input: Invoice `PENDING` dengan `final_price`.
- Generate QRIS string dengan amount = `invoice.final_price` (dikunci, tidak bisa diubah).
- Simpan ke `qris_requests` table dengan `expires_at` (default 15 menit).

### 3.2 Webhook Verification (Idempoten)
1. Terima webhook: `reference_code`, `qris_id`, `amount`.
2. **Cek Duplicate**: `SELECT * FROM mock_ledger WHERE reference_code = ?`.
   - Ada → return `DUPLICATE` (no side-effect).
3. **Cek Invoice**: `invoice.status == PENDING` AND `amount == invoice.final_price`.
   - Ya → `VERIFIED` → insert `mock_ledger` → invoice `PAID` → trigger next invoice.
   - Tidak → `EXCEPTION`.

### 3.3 Exception Handling
| Exception Type | Action | Follow-up Pesan |
|----------------|--------|-----------------|
| Nominal beda (overpay/underpay) | Invoice `PAYMENT_EXCEPTION` (bukan PAID) | "Pembayaran kami terima tapi ada selisih. Tim kami follow-up sore ini." |
| Reference tidak dikenal | `EXCEPTION` | "Referensi pembayaran tidak dikenali. Hubungi CS ya, Bang." |
| Invoice bukan PENDING | `EXCEPTION` | "Invoice ini sudah diproses/expired. Cek status ya, Bang." |

### 3.4 DILARANG
- Auto-PAID kalau nominal tidak cocok atau reference tidak dikenal.
- Skip verifikasi amount atau reference_code.
- Expose payment logic ke klien (hanya return status `VERIFIED`/`EXCEPTION`/`DUPLICATE`).

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Payment Exception (nominal beda) | Wati → Founder | < 1 jam |
| Duplicate reference tapi beda amount | Wati → Pak Harto → Founder | < 30 menit |
| Webhook spam / attack | Om Tono (Security) | < 15 menit |
| QRIS expired tapi klien bayar | Wati (manual verify) | < 1 jam |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Verification Accuracy | 100% | Zero false PAID |
| Idempotency Compliance | 100% | Duplicate → DUPLICATE always |
| Exception Detection Rate | 100% | All mismatches caught |
| Webhook Response Time | < 500ms | Latency measurement |
| Zero Amount Mismatch PAID | 100% | Audit log check |