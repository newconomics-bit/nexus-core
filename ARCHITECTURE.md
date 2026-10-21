# ARCHITECTURE: NEXUS CORE

## Tech Stack
- **Language:** Python 3.10+
- **Framework:** FastAPI (Async)
- **Database:** SQLite (Local dev) / Supabase (Prod)
- **Validation:** Pydantic
- **Orchestration:** State Machine (Transisi status proyek)

## Struktur Folder
```text
nexus-core/
├── main.py             # FastAPI Router & Telegram Webhook
├── database.py         # Koneksi DB & State tracking
├── models.py           # Pydantic schemas (ProjectSpec, Quote, AuditReport)
├── agents/
│   ├── manager.py      # Logic Budi (COO)
│   ├── cs.py           # Logic Sari & Wati
│   ├── finance.py      # Logic Pak Harto
│   ├── engineering.py  # Logic Mas Eko, Agus, Bambang
│   └── qa.py           # Logic Bang Jago
└── core/
    ├── llm_router.py   # Logic buat milih DeepSeek/Qwen/Claude
    └── circuit_breaker.py # Proteksi token & infinite loop
```

## Aturan Handoff
- Agent A TIDAK BOLEH memanggil fungsi Agent B secara langsung.
- Agent A menulis JSON ke Database -> Core Router membaca -> Core Router memicu Agent B.