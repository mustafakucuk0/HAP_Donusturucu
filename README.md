# HAP Dönüştürücü

Bir klasördeki videoları medya sunucuları için **HAP Q (.mov)** biçimine toplu olarak çeviren, tarayıcıda çalışan yerel bir araç.
Dönüştürmeden önce her dosyanın renk matrisini (BT.709 / BT.601) denetler, bitince çıktının renklerini kaynakla karşılaştırır.

- macOS ve Windows'ta çalışır
- Yalnızca **Python 3** ve **ffmpeg** gerektirir
- Her şey kendi bilgisayarınızda çalışır; internet gerekmez, dışarıya hiçbir şey gönderilmez
- Arayüz Türkçe ve İngilizce, açık ve koyu tema

## Kurulum rehberleri

| İşletim sistemi | Rehber |
|---|---|
| macOS | [docs/KURULUM_MAC.md](docs/KURULUM_MAC.md) |
| Windows | [docs/KURULUM_WINDOWS.md](docs/KURULUM_WINDOWS.md) |

## Kısaca

1. Bu depoyu indirin: **Code** düğmesi → **Download ZIP**, ya da
   ```bash
   git clone https://github.com/mustafakucuk0/HAP_Donusturucu.git
   ```
2. Python 3 ve ffmpeg'i kurun (ayrıntılar rehberlerde).
3. Başlatıcıya çift tıklayın:
   - macOS: `HAP_Donusturucu_Mac.command`
   - Windows: `HAP_Donusturucu_Windows.bat`
4. Tarayıcıda arayüz açılır. **Kaynak Klasör**'ü seçin, **Dönüştürmeyi Başlat**'a basın.

## Kullanım

1. **Kaynak Klasör**: videoların bulunduğu klasör. **Gözat** ile seçin ya da yolu yapıştırın.
   Alt klasörler de taransın istiyorsanız **Alt Klasörleri Dahil Et**'i açın; klasör yapısı hedefte korunur.
2. **Hedef Klasör**: çıktıların yazılacağı yer. Boş bırakırsanız kaynak klasörün içinde `hapq` adlı bir klasör açılır.
3. Listede her dosyanın renk durumu bir noktayla gösterilir:

   | Renk | Anlamı |
   |---|---|
   | Yeşil | Sorun yok |
   | Sarı | Bakılması gereken bir şey var (ör. renk etiketi yok) |
   | Kırmızı | Dosya bu hâliyle dönüştürülemez ya da renkleri yanlış çıkar |

   Renk etiketi olmayan bir dosyada **Önizle**'ye basın. İki renk yorumu yan yana gösterilir; kaynağa uyanı **Bunu Kullan** ile seçin.
4. **Dönüştürmeyi Başlat**'a basın. Bitince her satırda **Renk Doğru** ya da bir uyarı görünür.
   **Önizle** ile kaynak ve çıktı karelerini yan yana karşılaştırabilirsiniz.

Dil (TR / EN) ve tema (açık / koyu) sağ üstteki düğmelerden değişir; seçim tarayıcıda hatırlanır.

## Ayarlar

| Ayar | Açıklama |
|---|---|
| Biçim | HAP Q (önerilen), HAP (daha küçük dosya) ya da saydamlık için HAP Alpha |
| Sıkıştırma | Snappy dosyayı küçültür; oynatıcının diski yavaşsa önerilir |
| Parça Sayısı | Oynatıcının bir kareyi kaç çekirdekle çözeceği; yalnızca Snappy ile geçerli |
| Paralel İş | Aynı anda dönüştürülecek dosya sayısı; 4K ve üstünde 2–3 yeterli |
| Etiketsiz Dosyalarda Renk Matrisi | Renk etiketi olmayan dosyalarda varsayılacak matris |
| Kare Hızı | Kaynakla aynı bırakın ya da sabit bir hıza çevirin |
| Ses | PCM 24 bit, PCM 16 bit ya da sesi kaldırma |

## Notlar

- Sunucu yalnızca bu bilgisayardan erişilebilir (`127.0.0.1`).
- Yarıda kalan iş yeniden başlatılınca bitmiş dosyalar atlanır.
- Hata olursa ayrıntılar hedef klasördeki `_hata_loglari` klasörüne yazılır.
- HAP için görüntünün eni ve boyu **4'ün katı** olmalıdır.
- Başlatıcı olmadan çalıştırmak için: `python3 hapq_server.py --port 8770 --no-browser`

## Dosyalar

| Dosya | Ne işe yarar |
|---|---|
| `hapq_server.py` | Yerel sunucu; ffmpeg'i çalıştırır |
| `hapq.html` | Tarayıcı arayüzü |
| `HAP_Donusturucu_Mac.command` | macOS başlatıcısı |
| `HAP_Donusturucu_Windows.bat` | Windows başlatıcısı |
| `BENIOKU.txt` | Kısa, düz metin kullanım yönergesi |

Arayüzün yazı tipi [Inter](https://rsms.me/inter/) (SIL Open Font License 1.1); internetsiz çalışması için `hapq.html` içine gömülüdür.

## Yazar

**Mustafa Küçük**: [GitHub](https://github.com/mustafakucuk0) · [Instagram](https://www.instagram.com/mustafakucuk0/)

## Lisans

[MIT](LICENSE) © 2026 Mustafa Küçük
