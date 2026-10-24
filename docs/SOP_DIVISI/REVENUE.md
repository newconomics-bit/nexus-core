# SOP DIVISI REVENUE — Billing, CS & Retention RakitDigital

## 1. TUJUAN
Mengelola siklus revenue penuh: Intake & Discovery → Quoting → Billing & Dunning → Onboarding & Health Score → Retention/Churn. Memastikan cash flow lancar dan klien sukses.

## 2. LINGKUP
- **Agen**: Sari (Intake & Discovery), Wati (Billing & Dunning), Dewi (Customer Success), Dina (CS Support & Retention), Mbak Yuni (Payment Verification).
- **Alur**: Chat Klien → ProjectSpec → Quote → Invoice → Payment → Deploy → Onboarding → Health Score → Renewal/Churn.

## 3. PROSEDUR

### 3.1 Intake & Discovery (Sari)
- **Tujuan**: Ubah chat klien → JSON ProjectSpec lengkap (client_name, features[], budget).
- **Proses**: Tanya requirement → Klarifikasi → Validasi JSON ProjectSpec (Pydantic).
- **DILARANG**: Sebut harga sebelum QuoteID dari Finance; Janjikan fitur di luar v1.0 (Micro-SaaS UMKM: kasir, stok, laporan); Pakai bahasa AI-slop.
- **Selesai**: Semua field terisi + klien konfirmasi "Sudah benar, Bang" + JSON valid.

### 3.2 Quoting & Finance (Pak Harto + Sari)
- **Estimasi Effort**: 8 + 4 jam per fitur (deterministik).
- **Costing**: Labor = jam × Rp 75.000; Infra = Rp 150.000; QRIS MDR = 0.7% subtotal.
- **Margin**: HPP + 75% = Harga Jual (ceil ke Rp 50.000).
- **Diskon**: Max 10% auto. > 10% → ApprovalRequest `DISCOUNT_ESCALATION` (timeout 5 menit) ke Founder via Telegram.
- **Hard Cap**: Diskon maksimal 30%.
- **Quote Versioning**: Quote baru auto-expire quote lama.

### 3.3 Billing & Dunning SOP (Wati) — **Wajib Berurutan**
| Step | Trigger | Aksi | Pesan Contoh |
|------|---------|------|--------------|
| **H+3** | Invoice 3 hari lewat | WA Reminder | "Bang, invoice hosting telat 3 hari nih." |
| **H+7** | Invoice 7 hari lewat | Suspend Akses | "Bang, akses sistem ditutup sementara. Bayar dulu ya biar bisa dibuka lagi." |
| **H+14** | Invoice 14 hari lewat | Retention Offer | "Bang, mau kita tawarin paket lebih hemat? Atau diskon 10% sekali ini?" |
| **H+30** | Invoice 30 hari lewat | Execute Churn | Server dihapus, proyek state CHURNED. |

- **DILARANG**: Lompat step, mengubah nominal invoice, memberi diskon tanpa approval Founder.
- **Bahasa**: Tongkrongan bisnis, lolos ANTI_SLOP_RULES.

### 3.4 Payment Verification (Mbak Yuni)
- **QRIS Dinamis**: Amount dikunci dari `invoice.final_price`.
- **Verify Webhook**: Cek `reference_code` unik, `amount == invoice.final_price`, invoice masih PENDING.
- **Idempoten**: Duplicate `reference_code` → return `DUPLICATE` tanpa side-effect.
- **Exception Handling**:
  - Nominal beda → `PAYMENT_EXCEPTION` (bukan PAID), log alasan, trigger follow-up: "Pembayaran kami terima tapi ada selisih. Tim kami follow-up sore ini."
  - Reference tidak dikenal → `DUPLICATE` / `EXCEPTION`.
- **DILARANG**: Auto-PAID kalau nominal tidak cocok.

### 3.5 Onboarding & Health Score (Dewi)
- **Onboarding Plan**: Generate otomatis pasca-deploy, track item completion.
- **Target**: 100% onboarding sebelum Day 7.
- **Health Score**: Hitung berkala (usage, ticket volume, payment history, NPS).
- **At-Risk Flag**: Health score < 60 OR payment telat > 7 hari → flag ke Wati same hari.
- **Ticket Triage**:
  - FAQ: Auto-jawab < 5 menit (knowledge base).
  - TECHNICAL/BILLING: Eskalasi ke Om Tono/Wati < 1 jam.

### 3.6 CS Support & Retention (Dina)
- **Support**: Jawab FAQ, bantu setup, kirim panduan PDF/video.
- **Retention Call**: H+14 dunning (tawarkan downgrade/diskon), eskalasi ke Founder jika perlu.
- **Churn Risk**: Handle churn risk, eskalasi billing dispute ke Wati/Mbak Yuni.
- **Bahasa**: Tongkrongan bisnis, lolos text_quality_gate (score ≥ 35).

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Klien telat bayar > 30 hari (CHURNED) | Wati → Founder | Real-time (H+30) |
| Payment Exception (nominal beda) | Mbak Yuni → Wati → Founder | < 1 jam |
| Diskon > 10% diminta klien | Sari → Pak Harto → Founder | < 5 menit (timeout) |
| Health score < 40 (Critical Risk) | Dewi → Wati → Founder | < 2 jam |
| Billing dispute | Dina → Wati → Founder | < 1 jam |
| Contract > 7 hari belum ttd | Bu Ratna → Founder | < 4 jam |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Churn Rate | < 5% / bulan | CHURNED projects / Active projects |
| Onboarding Completion Day 7 | > 80% | Completed items / Total items |
| Invoice Paid On-Time (H+0) | > 70% | PAID invoices / Total invoices |
| Dunning Recovery Rate (H+3→H+14) | > 50% | Recovered / Overdue |
| Ticket Resolution Time (FAQ) | < 5 menit | Auto-response timestamp |
| Ticket Escalation Time (Tech/Bill) | < 1 jam | Eskalasi timestamp |
| Health Score Accuracy | > 85% | Predicted vs Actual churn |
| Payment Verification Accuracy | 100% | Zero false PAID |