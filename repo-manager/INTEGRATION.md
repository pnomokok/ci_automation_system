# Integration Guide

Bu dosya `repo-manager` modulu diger ekip modulleri ile birlestirilmeden once
yerel entegrasyon testi yapabilmek icin hazirlandi.

## 1. Repo Manager servisini calistir

```bash
uvicorn app.webhook_receiver:app --host 127.0.0.1 --port 8081
```

## 2. Mock Orchestrator calistir

Gercek Orchestrator henuz hazir degilse bu servis kullanilabilir:

```bash
uvicorn integration.mock_orchestrator:app --host 127.0.0.1 --port 8000
```

## 3. Ornek istekler

### Trigger endpoint

```bash
curl -X POST http://127.0.0.1:8081/trigger ^
  -H "Content-Type: application/json" ^
  -d @integration/trigger_request.json
```

Not: Bu endpoint gercek git clone/checkout yaptigi icin test repo URL'si erisilebilir
olmali.

Yerel dosya tabanli test repo ile denemek istersen:

```bash
curl -X POST http://127.0.0.1:8081/trigger ^
  -H "Content-Type: application/json" ^
  -d @integration/trigger_local_file_repo.json
```

### Webhook endpoint

Webhook testinde `X-Hub-Signature-256` degeri, `GITHUB_WEBHOOK_SECRET` ile ayni
secret kullanilarak uretilmelidir.

PowerShell ile ornek:

```powershell
$secret = "change-me"
$body = Get-Content -LiteralPath ".\\integration\\webhook_payload.json" -Raw
$bytes = [System.Text.Encoding]::UTF8.GetBytes($body)
$key = [System.Text.Encoding]::UTF8.GetBytes($secret)
$hmac = [System.Security.Cryptography.HMACSHA256]::new($key)
$hash = ($hmac.ComputeHash($bytes) | ForEach-Object { $_.ToString("x2") }) -join ""
$signature = "sha256=$hash"

Invoke-WebRequest -Method Post -Uri "http://127.0.0.1:8081/webhook" `
  -Headers @{
    "X-GitHub-Event" = "push"
    "X-Hub-Signature-256" = $signature
    "Content-Type" = "application/json"
  } `
  -Body $body
```

## 4. Beklenen sonuc

- `repo-manager` gelen veriyi dogrular
- `ci-config.yaml` bilgilerini pipeline istegine ekler
- Orchestrator'a `POST /api/v1/pipelines` gonderir
- Basarili durumda `status=queued` ve `pipeline_id` doner

## 5. GitHub Webhook'u Internetten Test Etme (ngrok / smee.io)

GitHub'in webhook POST'u gondermesi icin `repo-manager`'in internetten erisebilir bir URL'e
sahip olmasi gerekir. Gelistirme ortaminda bu iki aractan biriyle saglanir.

### Secenek A — ngrok

```bash
# Kurulum (bir kez)
# https://ngrok.com/download adresinden indir veya:
# Windows: choco install ngrok  |  macOS: brew install ngrok

# Repo Manager 8081 portunda calismalidir
ngrok http 8081
```

ngrok calistiktan sonra terminalde su formatta bir URL gorunur:

```
Forwarding  https://abc123.ngrok-free.app -> http://localhost:8081
```

GitHub reposunda **Settings > Webhooks > Add webhook** bolumune gidilir:
- **Payload URL**: `https://abc123.ngrok-free.app/webhook`
- **Content type**: `application/json`
- **Secret**: `.env` dosyasindaki `GITHUB_WEBHOOK_SECRET` degeri
- **Events**: "Just the push event"

### Secenek B — smee.io

```bash
# Kurulum (bir kez)
npm install --global smee-client

# smee.io adresinden yeni bir kanal olustur: https://smee.io/new
# Alinan URL ile baslat:
smee --url https://smee.io/<kanal-id> --target http://localhost:8081/webhook
```

GitHub webhook URL olarak `https://smee.io/<kanal-id>` girilir;
smee istemcisi gelen istekleri yerel servise yonlendirir.

### Test Akisi

1. `repo-manager` ve (ihtiyac varsa) `mock_orchestrator` servislerini baslat.
2. ngrok veya smee.io ile tunel ac.
3. GitHub reposuna kucuk bir commit push'la.
4. `repo-manager` loglarinda `POST /webhook 200` gorunmeli.
5. Mock Orchestrator loglarinda pipeline olusturma istegi gorunmeli.

## 6. Bu turda dogrulananlar

- `/health` endpointi canli olarak dogrulandi
- signed `POST /webhook` istegi mock Orchestrator ile uctan uca test edildi
- `POST /trigger` istegi yerel bir ornek git repo ile uctan uca test edildi
