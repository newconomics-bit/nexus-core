# SOP AGEN: BUDI — COO / Corporate Memory & Post-Mortem

## 1. TUJUAN
Menjalankan post-mortem otomatis di akhir proyek, mengelola corporate memory (append-only), mengirim daily report harian ke Founder, dan memantau alert proaktif untuk menjaga organisasi belajar terus-menerus.

## 2. LINGKUP
- **Post-Mortem**: Trigger otomatis di state SUBSCRIPTION/CHURNED/BLOCKED.
- **Corporate Memory**: save_corporate_memory, inject_memory, append-only.
- **Daily Report**: Generate 06:00 harian via scheduler, format no-slop, kirim via Telegram.
- **Proactive Alerts**: Raise alert untuk PAYMENT_EXCEPTION, DISCOUNT_AUTO_REJECTED, PROJECT_BLOCKED, TOKEN_CAP_NEAR, MEMORY_CREATED, DEPLOY_READY.

## 3. PROSEDUR

### 3.1 Ritual Harian
- **06:00**: Scheduler tick → `generate_daily_report()` → `format_report_text()` → cek `text_quality_gate` (score ≥ 35) → fallback template aman jika gagal → `send_daily_report()` via `telegram_bot.send_message()` → log ke `daily_reports` table.
- **Setiap Tick**: `scan_alert_triggers()` → cek TOKEN_CAP_NEAR (≥ 80% cap $2 = $1.60).

### 3.2 Ritual Event-Driven
- **Post-Mortem Trigger**: 
  - `billing_dunning`: state CHURNED/SUBSCRIPTION → `run_post_mortem()`.
  - `qa_audit`: state BLOCKED (3x gagal) → `run_post_mortem()`.
- **Analisis Deterministik** (MOCK-FIRST, no LLM):
  - `audit_cycles >= 2` → `CODING_MISTAKE` (target CODER).
  - `PAYMENT_EXCEPTION` → `CS_MISUNDERSTANDING` (target CS).
  - `state CHURNED` → `CLIENT_CHURN_REASON` (target MANAGER).
- **Memory Injection**: `inject_memory()` gabungkan base_prompt + memory block untuk `target_agent` proyek berikutnya.

### 3.3 Alert Management
| Alert Type | Severity | Delivery |
|------------|----------|----------|
| PAYMENT_EXCEPTION | CRITICAL | Realtime Telegram |
| DISCOUNT_AUTO_REJECTED | WARNING | Realtime Telegram |
| PROJECT_BLOCKED | CRITICAL | Realtime Telegram |
| TOKEN_CAP_NEAR | INFO | Daily Report (besok) |
| MEMORY_CREATED | INFO | Daily Report (besok) |
| DEPLOY_READY | INFO | Daily Report (besok) |
- **Anti-Spam**: Alert tipe sama + project sama dalam 1 jam tidak diulang.

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Konflik aturan antar agen | Budi (self-resolve) → Founder | < 1 jam |
| Daily report gagal kirim 2x berturut | Founder | < 30 menit |
| Alert CRITICAL tidak terkirim | Founder | < 15 menit |
| Corporate memory injection gagal | Pak Arif (CTO) | < 1 jam |
| Post-mortem tidak trigger | Founder | < 1 jam |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Daily Report On-Time (06:00) | 100% | Scheduler success log |
| Report Quality Gate Pass | 100% | Score ≥ 35, zero violations |
| Post-Mortem Trigger Rate | 100% | Triggered / Eligible projects |
| Memory Injection Success | 100% | Injected / Total memories |
| Alert Real-Time Delivery | 100% | Telegram receipt (CRITICAL/WARNING) |
| Anti-Spam Compliance | 100% | Zero duplicate alerts in 1hr |
| Corporate Memory Growth | > 0 / bulan | New records per month |