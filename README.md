# HAP Dönüştürücü

Bir klasördeki videoları **HAP Q (.mov)** biçimine toplu olarak çeviren, tarayıcıda çalışan küçük bir araç.
Çevirmeden önce her dosyanın renk bilgisini denetler, bitince çıktının renklerini kaynakla karşılaştırır.

- Mac ve Windows'ta çalışır
- Yalnızca **Python 3** ve **ffmpeg** gerektirir, başka kurulum yok
- Her şey kendi bilgisayarınızda çalışır, internete hiçbir şey gönderilmez

## Kurulum rehberleri

| İşletim sistemi | Rehber |
|---|---|
| 🍎 macOS | [docs/KURULUM_MAC.md](docs/KURULUM_MAC.md) |
| 🪟 Windows | [docs/KURULUM_WINDOWS.md](docs/KURULUM_WINDOWS.md) |

## Kısaca

1. Bu depoyu indirin: yeşil **Code** düğmesi → **Download ZIP**, ya da
   ```bash
   git clone https://github.com/mustafakucuk0/HAP_Donusturucu.git
   ```
2. Python 3 ve ffmpeg'i kurun (ayrıntılar yukarıdaki rehberlerde).
3. Başlatıcıya çift tıklayın:
   - Mac: `HAP_Donusturucu_Mac.command`
   - Windows: `HAP_Donusturucu_Windows.bat`
4. Tarayıcıda arayüz açılır. Giriş klasörünü seçin, **Dönüştürmeyi başlat**'a basın.

## Kullanım

1. **Giriş klasörünü** seçin (Seç… düğmesi ya da yolu yapıştırın).
2. **Çıkış klasörünü** seçin. Boş bırakırsanız giriş klasöründe `hapq` adlı bir klasör açılır.
3. Listede her dosyanın renk durumu görünür:
   - 🟢 **yeşil**: sorun yok
   - 🟡 **sarı**: bakılması gereken bir şey var (ör. renk etiketi yok)
   - 🔴 **kırmızı**: bu dosya bu hâliyle dönüştürülemez ya da yanlış çıkar

   Renk etiketi olmayan dosyada **Önizle**'ye basın; iki renk yorumundan kaynağa uyanı **Bunu kullan** ile seçin.
4. **Dönüştürmeyi başlat**'a basın. Bitince her satırda "Renk doğru" ya da bir uyarı görünür.
   Önizle ile kaynak ve çıktıyı yan yana görebilirsiniz.

## Notlar

- Sunucu yalnız bu bilgisayardan erişilebilir (`127.0.0.1`).
- Yarıda kalan iş yeniden başlatılınca biten dosyalar atlanır.
- Hata olursa ayrıntı, çıkış klasöründeki `_hata_loglari` klasörüne yazılır.
- HAP için görüntünün eni ve boyu **4'ün katı** olmalıdır.
- Gelişmiş: `python3 hapq_server.py --port 8770 --no-browser`

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `hapq_server.py` | Yerel sunucu; ffmpeg'i çalıştırır |
| `hapq.html` | Tarayıcı arayüzü |
| `HAP_Donusturucu_Mac.command` | Mac başlatıcısı |
| `HAP_Donusturucu_Windows.bat` | Windows başlatıcısı |
| `BENIOKU.txt` | Kısa düz metin yönerge |

## Yazar

**Mustafa Küçük** — [@mustafakucuk0](https://github.com/mustafakucuk0)

## Lisans

[MIT](LICENSE) © 2026 Mustafa Küçük
