# SECRET ROTATION RUNBOOK — RAKITDIGITAL

## 1. KAPAN ROTATE?
- Rutin: tiap 90 hari (quarterly)
- Emergency: kalau ada indikasi compromise (leak, unauthorized access)

## 2. CARA ROTATE TELEGRAM BOT TOKEN
1. Buka @BotFather di Telegram
2. /mybots -> pilih bot -> Revoke Token
3. Copy token baru
4. Update .env di server production
5. Restart service
6. Test: kirim /start ke bot, pastikan respond
7. Monitor 1 jam: cek apakah ada approval card yang terkirim

## 3. CARA ROTATE LLM API KEY (OpenRouter/DeepSeek/Claude)
1. Login ke dashboard provider
2. Create new API key
3. Update .env di server production
4. Restart service
5. Test: trigger CS intake, pastikan Sari respond
6. Monitor 1 jam: cek apakah ada error "invalid API key"
7. Revoke old API key di dashboard provider

## 4. CARA ROTATE QRIS WEBHOOK SECRET
1. Login ke dashboard payment gateway (Midtrans/Xendit)
2. Generate new webhook secret
3. Update .env di server production
4. Restart service
5. Test: simulate QRIS scan, pastikan payment verified
6. Monitor 1 jam: cek apakah ada webhook yang fail signature

## 5. CHECKLIST POST-ROTATION
- [ ] Semua service restart sukses
- [ ] Test manual semua endpoint sensitif
- [ ] Monitor log 1 jam, tidak ada error "unauthorized" atau "invalid signature"
- [ ] Old secret revoked (kecuali Telegram bot token yang nggak bisa revoke, cuma bisa regenerate)
- [ ] Update Bitwarden dengan secret baru

## 6. ROLLBACK PLAN
Kalau setelah rotation ada issue:
1. Restore .env dari backup (sebelum rotation)
2. Restart service
3. Investigasi root cause
4. Re-rotate dengan prosedur yang bener