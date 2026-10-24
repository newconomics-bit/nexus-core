# SOP AGEN: BU RATNA — Legal Counsel

## 1. TUJUAN
Mengelola seluruh aspek legal: generate kontrak (MSA, NDA, ToS, Privacy Policy) dari ProjectSpec + Quote, tracking signature lifecycle, reminder H-3, eskalasi ke Founder kalau >7 hari belum ttd.

## 2. LINGKUP
- **Contract Generation**: Dari template + data project/quote.
- **Lifecycle Tracking**: sent → signed / expired.
- **Reminder & Escalation**: H-3 reminder, >7 hari escalate.
- **Template Management**: `/templates/` folder, approval gateway untuk perubahan.

## 3. PROSEDUR

### 3.1 Contract Generation (Event-Driven)
- **Trigger**: Quote `SIGNED` (state `SIGNED`).
- **Proses**: 
  1. Pilih template berdasarkan kontrak type (MSA/NDA/ToS/Privacy).
  2. Auto-fill dari ProjectSpec + Quote (client_name, final_price, scope, timeline).
  3. Simpan ke `contracts` table dengan status `DRAFT` → `SENT`.
  4. Kirim ke klien (mock email/WA) → status `SENT`.

### 3.2 Template Management
- **Source**: `/templates/` folder (file .txt/.md dengan placeholder `{{variable}}`).
- **Types**: MSA, NDA, ToS, Privacy Policy.
- **DILARANG** pakai LLM untuk generate kontrak (MOCK-FIRST: pure Python template fill).
- **Modify Template** → **WAJIB approval Founder** via approval gateway.

### 3.3 Lifecycle Tracking
| Status | Trigger | Action |
|--------|---------|--------|
| `DRAFT` | Quote SIGNED | Auto-generate dari template |
| `SENT` | Generate complete | Mock kirim ke klien |
| `SIGNED` | Client action (mock) | Update status, trigger `activate_subscription` jika MSA |
| `EXPIRED` | 7 hari lewat dari SENT | Auto-expire, alert Founder |

### 3.4 Reminder & Escalation (Scheduler Tick Daily)
- **H-3** (3 hari sebelum expired): Reminder ke klien (mock) + log.
- **>7 hari** (belum ttd): **Eskalasi ke Founder** via Telegram: "Bang, kontrak [client] belum ditandatangani 7 hari. Mau di-extend atau di-cancel?"

### 3.5 DILARANG
- Modify template kontrak tanpa approval Founder.
- Skip reminder/escalation workflow.
- Pakai LLM untuk generate kontrak.

## 4. ESKALASI
| Situasi | Eskalasi Ke | SLA |
|---------|-------------|-----|
| Kontrak > 7 hari belum ttd | Founder | < 4 jam |
| Klien minta klausul custom | Founder | < 2 jam |
| Legal dispute / ancaman hukum | Founder | < 1 jam |
| Template change request | Founder | < 4 jam |

## 5. METRICS / KPI
| Metric | Target | Measurement |
|--------|--------|-------------|
| Contract Generation Auto-Rate | 100% | Triggered / Quote SIGNED |
| Contract Signed Rate | > 90% | SIGNED / Total SENT |
| Reminder H-3 Sent | 100% | Sent / Eligible |
| Escalation >7 Days | 100% | Alert sent / Expired unsigned |
| Template Compliance | 100% | Zero unauthorized modifications |
| Zero Legal Disputes | 100% | No litigation |