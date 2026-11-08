#!/bin/bash
# HAP Dönüştürücü - Mac başlatıcı. Çift tıklayın; tarayıcıda arayüz açılır.
# Yazar: Mustafa Küçük - MIT Lisansı
cd "$(dirname "$0")" || exit 1
export PATH="/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v python3 >/dev/null 2>&1; then
  echo "python3 bulunamadı. Terminal'de şunu çalıştırın:  xcode-select --install"
  read -r -p "Kapatmak için Enter'a basın."
  exit 1
fi
if ! command -v ffmpeg >/dev/null 2>&1 \
   && [ ! -x /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg ] \
   && [ ! -x /usr/local/opt/ffmpeg-full/bin/ffmpeg ]; then
  echo "Uyarı: ffmpeg bulunamadı. Kurmak için:  brew install ffmpeg-full"
fi

python3 hapq_server.py
