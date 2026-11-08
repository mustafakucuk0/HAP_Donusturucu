# Windows Kurulum Rehberi

Bu rehber HAP Dönüştürücü'yü bir Windows 10/11 bilgisayarda sıfırdan çalıştırmayı adım adım anlatır.
Toplam süre: ilk seferde ~10 dakika.

> [← Ana sayfaya dön](../README.md) · [Mac rehberi](KURULUM_MAC.md)

---

## 1. PowerShell'i açın

**Başlat** menüsüne sağ tık → **Terminal** (ya da **Windows PowerShell**).
Aşağıdaki komutları bu pencereye yapıştırıp Enter'a basacaksınız.

## 2. Python 3'ü kurun

Var mı diye bakın:

```powershell
py --version
```

Bir sürüm (3.8 ya da üstü) yazıyorsa bu adımı atlayın. Yoksa:

```powershell
winget install Python.Python.3.12
```

**winget yoksa:** [python.org/downloads](https://www.python.org/downloads/) adresinden indirip kurun.
> **Dikkat:** Kurulumun ilk ekranında **"Add python.exe to PATH"** kutusunu mutlaka işaretleyin.

## 3. ffmpeg'i kurun

**Yol A — winget (önerilen):**

```powershell
winget install Gyan.FFmpeg
```

**Yol B — elle:** [gyan.dev/ffmpeg/builds](https://www.gyan.dev/ffmpeg/builds/) adresinden `ffmpeg-release-full.7z` dosyasını indirin, açın ve `bin` klasöründeki **`ffmpeg.exe`** ile **`ffprobe.exe`**'yi doğrudan HAP Dönüştürücü klasörüne kopyalayın. Program onları orada da bulur.

Kurduktan sonra PowerShell'i **kapatıp yeniden açın** ve denetleyin:

```powershell
ffmpeg -hide_banner -encoders | findstr hap
```

`hap` satırları görüyorsanız hazırsınız.

## 4. Programı indirin

**Yol A — ZIP (en kolay):** GitHub sayfasında yeşil **Code** → **Download ZIP**. İndirilen ZIP'e sağ tık → **Tümünü ayıkla…** → klasörü istediğiniz yere çıkarın.

> ZIP'in içinden doğrudan çalıştırmayın; önce mutlaka ayıklayın.

**Yol B — git:**

```powershell
cd $HOME\Desktop
git clone https://github.com/mustafakucuk0/HAP_Donusturucu.git
```

## 5. Çalıştırın

Klasördeki **`HAP_Donusturucu_Windows.bat`** dosyasına çift tıklayın.
Siyah bir pencere açılır ve tarayıcıda arayüz belirir.

> Açılan siyah pencere programın kendisidir — iş bitene kadar **kapatmayın**.

### "Windows bilgisayarınızı korudu" (SmartScreen) uyarısı çıkarsa

1. **Ek bilgi**'ye tıklayın.
2. **Yine de çalıştır**'a basın.

Yalnız ilk seferde sorar.

### Güvenlik duvarı sorarsa

Program yalnızca bu bilgisayardan erişilen yerel bir sunucu açar (`127.0.0.1`). İzin verebilir ya da iptal edebilirsiniz; iki durumda da çalışır.

### "Python bulunamadı" derse

Python kurulu ama PATH'te değil demektir. Python'u yeniden kurup **"Add python.exe to PATH"** kutusunu işaretleyin, ya da bilgisayarı yeniden başlatın.

Elle çalıştırmak için klasörde adres çubuğuna `powershell` yazıp Enter'a basın, sonra:

```powershell
py -3 hapq_server.py
```

## 6. Kullanım

1. **Kaynak Klasör**'ü seçin.
2. **Hedef Klasör**'ü seçin (boş bırakırsanız kaynak klasörde `hapq` açılır).
3. Renk durumlarını kontrol edin (yeşil / sarı / kırmızı).
4. **Dönüştürmeyi Başlat**'a basın.

Ayrıntılar için [README](../README.md#kullanım).

## Sık karşılaşılan sorunlar

| Belirti | Çözüm |
|---|---|
| Arayüzde "ffmpeg sorunu" | `winget install Gyan.FFmpeg` ya da `ffmpeg.exe` + `ffprobe.exe`'yi klasöre koyun, programı yeniden açın |
| Türkçe karakterler bozuk görünüyor | Sorun değil, yalnız siyah penceredeki yazılardır; arayüz etkilenmez |
| Tarayıcı açılmadı | Siyah pencerede yazan `http://127.0.0.1:8770/...` adresini kopyalayıp tarayıcıya yapıştırın |
| Bir dosya hata verdi | Hedef klasördeki `_hata_loglari` klasörüne bakın |
| "eni/boyu 4'ün katı olmalı" | Videoyu 4'ün katı bir çözünürlüğe getirin (ör. 1920×1080 olur, 1918×1080 olmaz) |
