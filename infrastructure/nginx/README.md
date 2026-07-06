# Veridian nginx — güvenli kurulum

Bu dosyalar **sadece** Veridian domain'leri için ayrı `server` block'lar ekler.
Mevcut `nginx.conf` veya diğer site config'lerine **dokunulmaz**.

## DNS (önce bunu yapın)

| Kayıt | Tip | Değer |
|---|---|---|
| `veridian.furkanguven.space` | A | sunucu IP |
| `api.veridian.furkanguven.space` | A | sunucu IP |

API kaydı yoksa SSL yine de ana domain için alınabilir; API DNS eklendikten sonra `ssl-api` çalıştırılır.

## Kurulum

```bash
sudo bash infrastructure/scripts/setup-nginx.sh install
sudo bash infrastructure/scripts/setup-nginx.sh diagnose   # DNS + webroot kontrolü
sudo bash infrastructure/scripts/setup-nginx.sh ssl
```

API DNS sonradan eklendiyse:

```bash
sudo bash infrastructure/scripts/setup-nginx.sh ssl-api
```

## 403 hatası (ACME challenge)

En sık nedenler:

1. **DNS yok** — `api.veridian.furkanguven.space` için A kaydı ekleyin
2. **SELinux** — script `chcon` uygular; `diagnose` ile kontrol edin
3. **Duplicate server_name** — başka bir nginx config aynı domain'i zaten tanımlıyorsa 403 olabilir; `diagnose` gösterir

## Kaldırma

```bash
sudo bash infrastructure/scripts/setup-nginx.sh remove
```

Sadece `zz-veridian-*.conf` dosyaları silinir; diğer siteler etkilenmez.
