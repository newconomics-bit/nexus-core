# BUDI — COO / Corporate Memory & Post-Mortem
## TUJUAN
Menjalankan post-mortem otomatis di akhir proyek (state SUBSCRIPTION/CHURNED/BLOCKED). Ekstrak lessons learned deterministik, simpan ke corporate_memory, inject ke system prompt agen relevan untuk proyek berikutnya.

## BATASAN
- BOLEH: run_post_mortem() analisis: audit_cycles >= 2 → CODING_MISTAKE (target CODER); PAYMENT_EXCEPTION → CS_MISUNDERSTANDING (target CS); state CHURNED → CLIENT_CHURN_REASON (target MANAGER).
- BOLEH: save_corporate_memory() dengan category, lesson_text, severity, target_agent, created_at.
- BOLEH: inject_memory() gabungkan base_prompt + memory block untuk agen target.
- DILARANG: panggil LLM untuk ekstrak lesson (MOCK-FIRST: logika deterministik dari metrik DB).
- DILARANG: hapus atau overwrite memory lama (append-only).
- DILARANG: inject memory ke agen yang bukan target_agent.

## DEFINISI SELESAI
CorporateMemory records tersimpan di DB. Prompt injection berfungsi: GET /api/memory/inject?agent=CODER return base_prompt + memory block. Post-mortem ter-trigger otomatis di billing_dunning (CHURNED/SUBSCRIPTION) dan qa_audit (BLOCKED).