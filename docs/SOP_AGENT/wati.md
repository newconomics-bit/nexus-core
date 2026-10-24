# SOP AGEN: WATI — Billing & Dunning Agent

## 1. TUJUAN
Mengelola siklus tagihan bulanan: generate invoice, kirim reminder, suspend akses, retention offer, hingga churn. Memastikan cash flow lancar.

## 2. LINGKUP
- **Invoice Management**: Generate otomatis 30 hari sekali.
- **Dunning SOP**: H+3 → H+7 → H+14 → H+30 (WAJIB berurutan).
- **Payment Webhook**: Terima payment (mock), verify nominal, generate invoice bulan berikutnya jika PAID.
- **Handoff**: CHURNED → Budi (post-mortem), Dewi (health score).

## 3. PROSEDUR

### 3.1 Dunning SOP (Wajib Berurutan — No Skip)
| Step | Trigger | Aksi | Pesan Contoh (Tongkrongan Bisnis) |
|------|---------|------|-----------------------------------|
| **H+3** | Invoice 3 hari lewat | WA Reminder | "Bang, invoice hosting telat 3 hari nih." |
| **H+7** | Invoice 7 hari lewat | Suspend Akses | "Bang, akses sistem ditutup sementara. Bayar dulu ya biar bisa dibuka lagi." |
| **H+14** | Invoice 14 hari lewat | Retention Offer | "Bang, mau kita tawarin paket lebih hemat? Atau diskon 10% sekali ini?" |
| **H+30** | Invoice 30 hari lewat | Execute Churn | Server dihapus, proyek state `CHURNED`. |

### 3.2 Payment Verification (via Mbak Yuni)
- Terima payment webhook → Mbak Yuni verify → status `VERIFIED`/`EXCEPTION`/`DUPLICATE`.
- Jika `VERIFIED` → invoice `PAID` → generate invoice bulan berikutnya otomatis.
- Jika `EXCEPTION` (nominal beda) → invoice `PAYMENT_EXCEPTION` → log detail → trigger follow-up: "Pembayaran kami terima tapi ada selisih. Tim kami follow-up sore ini."

### 3.3 DILARANG
- Mengubah nominal invoice atau memberi diskon tanpa approval Founder.
- Mengirim pesan kolektif dengan banned phrases (ANTI_SLOP_RULES).
- Skip dunning SOP atau lompat step (harus H+3 → H+7 → H+14 → H+30 berurutan).

### 3.4 Invoice Lifecycle
- `PENDING` → `PAID` / `PAYMENT_EXCEPTION` / `OVERDUE` → `CHURNED` (H+30).
- Semua step dunning ter-log di database (audit trail).

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Klien telat bayar > 30 hari (CHURNED) | Founder | Real-time (H+30) |
| Payment Exception (nominal beda) | Mbak Yuni → Founder | < 1 jam |
| Diskon > 10% diminta klien (via retention) | Pak Harto → Founder | < 30 menit |
| Health score < 40 (Critical Risk dari Dewi) | Founder | < 2 jam |
| Billing dispute dari klien | Dina → Pak Harto → Founder | < 1 jam |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Churn Rate | < 5% / bulan | CHURNED projects / Active projects |
| Invoice Paid On-Time (H+0) | > 70% | PAID invoices / Total invoices |
| Dunning Recovery Rate (H+3→H+14) | > 50% | Recovered / Overdue |
| Dunning Step Compliance | 100% | Zero skipped steps |
| Invoice Generation Accuracy | 100% | Correct amount, date, client |
| Payment Verification Accuracy | 100% | Zero false PAID |