#!/bin/bash
# HAP Dönüştürücü - Mac başlatıcı. Çift tıklayın; tarayıcıda arayüz açılır.
# Yazar: Mustafa Küçük - MIT Lisansı
cd "$(dirname "$0")" || exit 1
export PATH="$HOME/.local/bin:$HOME/.cargo/bin:/opt/homebrew/bin:/usr/local/bin:$PATH"

if ! command -v ffmpeg >/dev/null 2>&1 \
   && [ ! -x /opt/homebrew/opt/ffmpeg-full/bin/ffmpeg ] \
   && [ ! -x /usr/local/opt/ffmpeg-full/bin/ffmpeg ]; then
  echo "Uyarı: ffmpeg bulunamadı. Kurmak için:  brew install ffmpeg-full"
fi

# Önce uv: Python yoksa ilk açılışta kendisi indirir.
if command -v uv >/dev/null 2>&1; then
  uv run --no-project --python 3.12 hapq_server.py
elif command -v python3 >/dev/null 2>&1 && python3 -c "import sys" >/dev/null 2>&1; then
  python3 hapq_server.py
else
  echo "Python bulunamadı. En kolayı uv kurmak; Terminal'de şunu çalıştırın:"
  echo "  brew install uv"
  echo "ya da:"
  echo "  curl -LsSf https://astral.sh/uv/install.sh | sh"
  echo "Sonra bu dosyaya yeniden çift tıklayın."
  read -r -p "Kapatmak için Enter'a basın."
  exit 1
fi
