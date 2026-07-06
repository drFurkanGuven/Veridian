# Veridian nginx — güvenli kurulum
#
# Bu dosyalar SADECE Veridian domain'leri için ayrı server block'lar ekler.
# Mevcut nginx.conf veya diğer site config'lerine DOKUNULMAZ.
#
# Kurulum:
#   sudo bash infrastructure/scripts/setup-nginx.sh install
#   sudo bash infrastructure/scripts/setup-nginx.sh ssl
#
# Kaldırma (sadece Veridian):
#   sudo bash infrastructure/scripts/setup-nginx.sh remove
