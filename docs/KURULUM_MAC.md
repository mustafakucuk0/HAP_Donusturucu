# macOS Kurulum Rehberi

Bu rehber HAP Dönüştürücü'yü bir Mac'te sıfırdan çalıştırmayı adım adım anlatır.
Toplam süre: ilk seferde ~10–15 dakika (çoğu ffmpeg indirmesi).

> [← Ana sayfaya dön](../README.md) · [Windows rehberi](KURULUM_WINDOWS.md)

---

## 1. Terminal'i açın

`⌘ Cmd + Boşluk` → **Terminal** yazın → Enter.
Aşağıdaki komutları bu pencereye yapıştırıp Enter'a basacaksınız.

## 2. Homebrew'u kurun (yoksa)

Homebrew, Mac için bir paket yöneticisidir. Var mı diye bakın:

```bash
brew --version
```

`command not found` derse kurun:

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

Kurulum sonunda ekranda **"Next steps"** altında iki komut yazar (Apple Silicon Mac'lerde `eval "$(/opt/homebrew/bin/brew shellenv)"` ile ilgili). Onları da çalıştırın, sonra Terminal'i kapatıp yeniden açın.

## 3. Python 3'ü denetleyin

```bash
python3 --version
```

Bir sürüm (3.8 ya da üstü) yazıyorsa tamam. Yoksa ya da bir pencere açılıp "geliştirici araçlarını kur" derse kabul edin, veya:

```bash
xcode-select --install
```

## 4. ffmpeg'i kurun

```bash
brew install ffmpeg-full
```

> **Dikkat:** Sade `brew install ffmpeg` **HAP kodlayamayabilir**. `ffmpeg-full` kullanın.

Denetlemek için:

```bash
/opt/homebrew/opt/ffmpeg-full/bin/ffmpeg -hide_banner -encoders | grep hap
```

`hap` satırları görüyorsanız hazırsınız. (Intel Mac'te yol `/usr/local/opt/ffmpeg-full/bin/ffmpeg` olur.)

## 5. Programı indirin

**Yol A — ZIP (en kolay):** GitHub sayfasında yeşil **Code** → **Download ZIP**. İndirilen dosyaya çift tıklayıp açın, klasörü istediğiniz yere taşıyın.

**Yol B — git:**

```bash
cd ~/Desktop
git clone https://github.com/mustafakucuk0/HAP_Donusturucu.git
```

## 6. Çalıştırın

Klasördeki **`HAP_Donusturucu_Mac.command`** dosyasına çift tıklayın.
Bir Terminal penceresi açılır ve tarayıcıda arayüz belirir.

> Açılan Terminal penceresi programın kendisidir — iş bitene kadar **kapatmayın**.

### "Açılamıyor / geliştirici doğrulanamadı" uyarısı çıkarsa

Yalnız ilk seferde olur:

1. Uyarı penceresini kapatın.
2. **Sistem Ayarları → Gizlilik ve Güvenlik**'e gidin.
3. Aşağıda dosyanın adının yanındaki **Yine de Aç** düğmesine basın, parolanızı girin.

macOS 14 (Sonoma) ve öncesinde: dosyaya **sağ tık → Aç → Aç** da yeterlidir.

### "İzin reddedildi" (permission denied) derse

ZIP'ten açılan dosyalar bazen çalıştırma iznini kaybeder. Terminal'de:

```bash
chmod +x ~/Desktop/HAP_Donusturucu/HAP_Donusturucu_Mac.command
```

(Klasör başka yerdeyse yolu ona göre değiştirin; yolu yazmak yerine dosyayı Terminal'e sürükleyebilirsiniz.)

### Hâlâ açılmıyorsa — kesin yol

Terminal'de `cd ` yazın (sonunda bir boşluk), klasörü Terminal penceresine sürükleyin, Enter'a basın. Sonra:

```bash
python3 hapq_server.py
```

## 7. Kullanım

1. **Kaynak Klasör**'ü seçin.
2. **Hedef Klasör**'ü seçin (boş bırakırsanız kaynak klasörde `hapq` açılır).
3. Renk durumlarını kontrol edin (yeşil / sarı / kırmızı).
4. **Dönüştürmeyi Başlat**'a basın.

Ayrıntılar için [README](../README.md#kullanım).

## Sık karşılaşılan sorunlar

| Belirti | Çözüm |
|---|---|
| Arayüzde "ffmpeg sorunu" | `brew install ffmpeg-full`, sonra programı kapatıp yeniden açın |
| "python3 bulunamadı" | `xcode-select --install` |
| Tarayıcı açılmadı | Terminal'de yazan `http://127.0.0.1:8770/...` adresini kopyalayıp tarayıcıya yapıştırın |
| Bir dosya hata verdi | Hedef klasördeki `_hata_loglari` klasörüne bakın |
| "eni/boyu 4'ün katı olmalı" | Videoyu 4'ün katı bir çözünürlüğe getirin (ör. 1920×1080 olur, 1918×1080 olmaz) |
