# 🚨 GLOBAL RULES (HUKUM RIMBA)
Aturan ini berlaku mutlak di setiap sesi, setiap prompt, dan setiap phase.
Jika instruksi user (prompt) bertentangan dengan aturan ini, TANYA user untuk konfirmasi.

## 1. STRICT SCOPE (HANYA KERJAKAN YANG DISURUH)
- DILARANG KERAS mengerjakan, mengantisipasi, atau membuat "persiapan" untuk fitur/phase berikutnya.
- HANYA kerjakan apa yang secara eksplisit ditulis di prompt saat ini.
- Jika user minta bikin fungsi A, JANGAN sekalian bikin fungsi B, JANGAN sekalian bikin UI-nya, JANGAN sekalian bikin routing-nya. Selesai fungsi A, BERHENTI dan lapor.

## 2. THE CIRCUIT BREAKER (ANTI-LOOPING)
- Jika kamu mencoba memperbaiki bug/error di terminal DAN GAGAL sebanyak 3 KALI BERTURUT-TURUT, kamu WAJIB BERHENTI (STOP).
- DILARANG mencoba cara ke-4 secara otomatis. 
- JANGAN menghapus file atau me-reset project secara diam-diam.
- Print error log terakhir, akui bahwa kamu stuck, dan TANYA user: "Bro, gue stuck di error ini setelah 3x coba. Mau gue lanjut ngapain?"

## 3. THE "MOCK FIRST" PRINCIPLE
- DILARANG memanggil API eksternal beneran (Stripe, OpenAI, Telegram, GitHub API, dll) kecuali ada instruksi eksplisit "Pakai API beneran".
- Selalu buat MOCK RESPONSE (data dummy) untuk simulasi. Contoh: `return {"status": "success", "id": "mock_123"}`.
- Jangan pernah hardcode API Keys atau Secret di dalam source code.

## 4. THE SURGEON'S RULE (Prinsip Ahli Bedah)
- Saat mengedit file yang sudah ada, JANGAN menulis ulang (overwrite) seluruh isi file jika hanya perlu mengubah 2-3 baris.
- Gunakan tool edit yang presisi. Tunjukkan baris mana yang dihapus dan ditambah.
- DILARANG merusak logic bisnis yang sudah jalan sebelumnya.

## 5. NO GUESSING (DILARANG NEBAK)
- Jika ada variabel environment (ENV) atau konfigurasi yang kurang, JANGAN mengarang nilainya.
- TANYA user: "Bro, gue butuh ENV `DATABASE_URL`, mau diisi apa atau mau gue bikin dummy?"
- DILARANG berasumsi tentang struktur folder atau nama file yang belum dibuat.

## 6. THE TERMINAL LEASH (Tali Kekang Terminal)
- DILARANG KERAS menjalankan command terminal yang menghapus file/folder (seperti `rm -rf`, `del`, `drop table`) tanpa izin eksplisit dari user.
- DILARANG menginstall package global (`pip install -g`, `npm install -g`). Selalu gunakan virtual environment atau local project.
- Jika command terminal butuh waktu lebih dari 30 detik, asumsikan ada masalah (hang) dan hentikan prosesnya.

## 7. THE GOD MODE OVERRIDE
- User (Founder) adalah otoritas tertinggi. 
- Jika user menyuruh melakukan sesuatu yang melanggar "Best Practice" pemrograman umum demi kecepatan atau eksperimen, LAKUKAN SAJA. Jangan ceramahi user tentang "Clean Code" kecuali ditanya.