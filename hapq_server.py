#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
HAP Dönüştürücü - yerel sunucu.

Tarayıcıdaki arayüz (hapq.html) ffmpeg'i bu sunucu üzerinden çalıştırır.
Sunucu yalnız bu bilgisayardan erişilebilir (127.0.0.1). Python 3.8+ ve ffmpeg
dışında hiçbir şey gerektirmez.

Kullanım:  python3 hapq_server.py [--port 8770] [--no-browser]

Yazar: Mustafa Küçük
Lisans: MIT (bkz. LICENSE)
"""
import base64
import json
import os
import re
import secrets
import shutil
import subprocess
import sys
import tempfile
import threading
import time
import urllib.error
import urllib.request
import webbrowser
import zipfile
from concurrent.futures import ThreadPoolExecutor
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

HERE = os.path.dirname(os.path.abspath(__file__))
IS_MAC = sys.platform == "darwin"
IS_WIN = os.name == "nt"
NOWIN = getattr(subprocess, "CREATE_NO_WINDOW", 0) if IS_WIN else 0
TOKEN = secrets.token_urlsafe(18)

# Yeni sürüm yayınlarken bu numarayı artırın ve GitHub'da aynı numarayla
# (ör. v1.1.0) bir Release oluşturun; kullanıcıların programı onu görür.
VERSION = "1.0.0"
REPO = "mustafakucuk0/HAP_Donusturucu"
UA = "HAP-Donusturucu/" + VERSION
SRV = None

VIDEO_EXT = {".mp4", ".mov", ".mkv", ".avi", ".m4v", ".webm", ".mxf"}
MATRICES = {"bt709", "bt601", "bt2020", "smpte240m", "fcc"}
FORMATS = {"hap_q", "hap", "hap_alpha"}
AUDIO = {"pcm_s24le", "pcm_s16le", "none"}
# ffprobe renk etiketi -> ffmpeg scale filtresinin matris adı
TAG2M = {"bt709": "bt709", "smpte170m": "bt601", "bt470bg": "bt601",
         "bt2020nc": "bt2020", "bt2020c": "bt2020", "smpte240m": "smpte240m", "fcc": "fcc"}
RGB_RE = re.compile(r"^(rgb|bgr|gbr|argb|abgr|0rgb|0bgr|x2rgb|x2bgr|pal8|gray|ya\d|mono)")
ALPHA_RE = re.compile(r"^(yuva|gbrap|ya\d|rgba|bgra|argb|abgr)")


class ApiError(Exception):
    pass


# ---------------------------------------------------------------- araçlar

def _win_registry_path():
    """Windows: kurulumdan sonra açılmış olsa bile Gezgin'in eski PATH'ini değil,
    kayıt defterindeki güncel PATH'i okur (winget/kurulum sonrası yeniden
    oturum açmadan da bulunsun)."""
    out = []
    try:
        import winreg
    except ImportError:
        return out
    keys = ((winreg.HKEY_CURRENT_USER, "Environment"),
            (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"))
    for root, sub in keys:
        try:
            with winreg.OpenKey(root, sub) as k:
                v, _ = winreg.QueryValueEx(k, "Path")
                out += [os.path.expandvars(p) for p in str(v).split(";")]
        except OSError:
            pass
    return out


def _candidate_dirs():
    import glob
    dirs = [HERE, os.path.join(HERE, "ffmpeg"), os.path.join(HERE, "ffmpeg", "bin")]
    dirs += glob.glob(os.path.join(HERE, "ffmpeg*", "bin")) + glob.glob(os.path.join(HERE, "ffmpeg*", "*", "bin"))
    env_dir = os.environ.get("HAPQ_FFMPEG_DIR")
    if env_dir:
        dirs.insert(0, env_dir)
    if IS_WIN:
        dirs += os.environ.get("PATH", "").split(os.pathsep) + _win_registry_path()
        home = os.path.expanduser("~")
        lad = os.environ.get("LOCALAPPDATA") or os.path.join(home, "AppData", "Local")
        pf = os.environ.get("ProgramFiles") or r"C:\Program Files"
        pd = os.environ.get("ProgramData") or r"C:\ProgramData"
        for base in (os.path.join(lad, "Microsoft", "WinGet"), os.path.join(pf, "WinGet")):
            dirs.append(os.path.join(base, "Links"))
            # winget install Gyan.FFmpeg -> Packages\Gyan.FFmpeg_...\ffmpeg-x.y-full_build\bin
            dirs += glob.glob(os.path.join(base, "Packages", "*FFmpeg*", "*", "bin"))
        dirs += [os.path.join(pd, "chocolatey", "bin"),
                 os.path.join(home, "scoop", "shims"),
                 os.path.join(home, "scoop", "apps", "ffmpeg", "current", "bin"),
                 os.path.join(pf, "ffmpeg", "bin")]
        # elle indirilip açılmış zip (C:\ffmpeg, İndirilenler, Masaüstü)
        for root in ("C:\\", pf, os.path.join(home, "Downloads"), os.path.join(home, "Desktop"), home):
            dirs += glob.glob(os.path.join(root, "ffmpeg*", "bin"))
            dirs += glob.glob(os.path.join(root, "ffmpeg*", "*", "bin"))
    else:
        # Homebrew'ün ffmpeg-full'u "keg-only": /opt/homebrew/bin'e bağlanmaz,
        # kendi klasöründe durur. HAP (snappy) çoğu zaman yalnız onda var.
        for pre in ("/opt/homebrew", "/usr/local", "/home/linuxbrew/.linuxbrew"):
            dirs.append(os.path.join(pre, "opt", "ffmpeg-full", "bin"))
        dirs += os.environ.get("PATH", "").split(os.pathsep)
        # Finder'dan çift tıklamada PATH'te Homebrew/MacPorts olmayabilir
        dirs += ["/opt/homebrew/bin", "/usr/local/bin", "/opt/local/bin", "/usr/bin", "/snap/bin"]
    seen, res = set(), []
    for d in dirs:
        d = (d or "").strip().strip('"')
        if not d:
            continue
        k = os.path.normcase(os.path.abspath(d))
        if k not in seen:
            seen.add(k)
            res.append(d)
    return res


def _has_hap(ffmpeg):
    try:
        r = subprocess.run([ffmpeg, "-hide_banner", "-h", "encoder=hap"], stdout=subprocess.PIPE,
                           stderr=subprocess.PIPE, stdin=subprocess.DEVNULL, timeout=20,
                           creationflags=NOWIN)
        return "hap_q" in (r.stdout or b"").decode("utf-8", "replace")
    except (OSError, subprocess.SubprocessError):
        return False


def find_ffmpeg():
    """ffmpeg + ffprobe çiftini bulur. Birden çok kurulum varsa HAP kodlayabileni
    seçer (ör. PATH'te sade Homebrew ffmpeg'i, yanında ffmpeg-full)."""
    ext = ".exe" if IS_WIN else ""
    pairs = []
    for d in _candidate_dirs():
        f, p = os.path.join(d, "ffmpeg" + ext), os.path.join(d, "ffprobe" + ext)
        if os.path.isfile(f) and os.path.isfile(p):
            pairs.append((f, p))
    for f, p in pairs:
        if _has_hap(f):
            return f, p, pairs
    if pairs:
        return pairs[0][0], pairs[0][1], pairs
    # ffprobe ayrı yerdeyse
    f = shutil.which("ffmpeg")
    p = shutil.which("ffprobe")
    return f, p, pairs


FFMPEG, FFPROBE, FF_FOUND = find_ffmpeg()


def run(cmd, timeout=None, env=None):
    return subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                          stdin=subprocess.DEVNULL, timeout=timeout,
                          creationflags=NOWIN, env=env)


def txt(b):
    return (b or b"").decode("utf-8", "replace")


def frac(s):
    try:
        s = str(s or "")
        if "/" in s:
            a, b = s.split("/", 1)
            b = float(b)
            return float(a) / b if b else 0.0
        return float(s) if s else 0.0
    except ValueError:
        return 0.0


def clamp(v, lo, hi, default):
    try:
        return max(lo, min(hi, int(v)))
    except (TypeError, ValueError):
        return default


_ENV = None


def get_env():
    global _ENV
    if _ENV is not None:
        return _ENV
    info = {"platform": "mac" if IS_MAC else "win" if IS_WIN else "linux",
            "cpus": os.cpu_count() or 4, "ffmpeg": FFMPEG or "", "version": "",
            "hap": False, "problem": "", "app_version": VERSION}
    if not FFMPEG or not FFPROBE:
        info["problem"] = ("ffprobe bulunamadı (ffmpeg var: %s)." % FFMPEG) if FFMPEG else "ffmpeg bulunamadı."
    else:
        try:
            v = txt(run([FFMPEG, "-hide_banner", "-version"], 20).stdout).splitlines()
            info["version"] = v[0] if v else ""
            h = txt(run([FFMPEG, "-hide_banner", "-h", "encoder=hap"], 20).stdout)
            info["hap"] = "hap_q" in h
            if not info["hap"]:
                info["problem"] = "Bu ffmpeg HAP kodlayamıyor (snappy desteği olmadan derlenmiş): %s" % FFMPEG
        except Exception as ex:  # noqa: BLE001
            info["problem"] = "ffmpeg çalıştırılamadı: %s" % ex
    _ENV = info
    return info


# ---------------------------------------------------------------- güncellemeler

def _vtuple(s):
    """'v1.2.0', '9.0.2_1', '7.1-full_build-www.gyan.dev' -> (1,2,0,0). Sürüm değilse None."""
    m = re.match(r"\s*[vV]?(\d+(?:\.\d+){0,3})", s or "")
    if not m:
        return None
    t = [int(x) for x in m.group(1).split(".")]
    return tuple(t + [0] * (4 - len(t)))


def _newer(latest, current):
    a, b = _vtuple(latest), _vtuple(current)
    return bool(a and b and a > b)


def _fetch(url, timeout=6):
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/vnd.github+json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return r.read()


def _app_update():
    res = {"current": VERSION, "latest": None, "newer": False, "url": "https://github.com/%s/releases" % REPO,
           "zip": None, "can_apply": True, "why": ""}
    if os.path.isdir(os.path.join(HERE, ".git")):
        res["can_apply"], res["why"] = False, "git"
    elif not os.access(HERE, os.W_OK):
        res["can_apply"], res["why"] = False, "readonly"
    try:
        j = json.loads(_fetch("https://api.github.com/repos/%s/releases/latest" % REPO))
        res["latest"] = str(j.get("tag_name") or "").lstrip("vV") or None
        res["url"] = j.get("html_url") or res["url"]
        res["zip"] = j.get("zipball_url")
        res["newer"] = _newer(res["latest"], VERSION)
    except urllib.error.HTTPError as ex:
        if ex.code != 404:  # 404: henüz hiç sürüm yayınlanmamış
            res["error"] = True
    except Exception:  # noqa: BLE001  (internet yok vb.: sessizce geç)
        res["error"] = True
    return res


def _ffmpeg_update():
    env = get_env()
    m = re.search(r"ffmpeg version (\S+)", env.get("version") or "")
    res = {"current": m.group(1) if m else "", "latest": None, "newer": False, "kind": "", "how": ""}
    if not FFMPEG or not _vtuple(res["current"]):
        return res  # bulunamadı ya da git derlemesi (sürüm numarası yok)
    real = os.path.realpath(FFMPEG)
    low = real.lower()
    try:
        cellar = re.search(r"/Cellar/([^/]+)/([^/]+)/", real)
        if cellar:
            name = cellar.group(1)
            j = json.loads(_fetch("https://formulae.brew.sh/api/formula/%s.json" % name))
            res["latest"] = (j.get("versions") or {}).get("stable")
            res["kind"], res["how"] = "brew", "brew upgrade %s" % name
        elif IS_WIN:
            res["latest"] = txt(_fetch("https://www.gyan.dev/ffmpeg/builds/release-version")).strip() or None
            if "gyan.ffmpeg" in low or "winget" in low:
                res["kind"], res["how"] = "winget", "winget upgrade Gyan.FFmpeg"
            elif "chocolatey" in low:
                res["kind"], res["how"] = "choco", "choco upgrade ffmpeg-full"
            elif "scoop" in low:
                res["kind"], res["how"] = "scoop", "scoop update ffmpeg"
            else:
                res["kind"], res["how"] = "manual", "https://www.gyan.dev/ffmpeg/builds/"
    except Exception:  # noqa: BLE001
        res["error"] = True
    res["newer"] = _newer(res["latest"], res["current"])
    return res


_UPD = {"at": 0, "data": None}
_UPD_LOCK = threading.Lock()


def check_updates(force=False):
    with _UPD_LOCK:
        if not force and _UPD["data"] and time.time() - _UPD["at"] < 1800:
            return _UPD["data"]
    with ThreadPoolExecutor(2) as ex:
        a, f = ex.submit(_app_update), ex.submit(_ffmpeg_update)
        data = {"app": a.result(), "ffmpeg": f.result()}
    with _UPD_LOCK:
        _UPD.update(at=time.time(), data=data)
    return data


def apply_update():
    """Son sürümün zip'ini indirip program dosyalarının üzerine yazar.
    Değişen dosyaların eski hâli .eski_surum klasörüne yedeklenir."""
    if RUNNER.state == "running":
        raise ApiError("Dönüştürme sürerken güncellenemez.")
    info = check_updates(force=True)["app"]
    if info["why"] == "git":
        raise ApiError("Bu klasör git ile indirilmiş; güncellemek için klasörde git pull çalıştırın.")
    if info["why"] == "readonly":
        raise ApiError("Program klasörüne yazılamıyor; yeni sürümü GitHub'dan indirin.")
    if not info["newer"] or not info["zip"]:
        raise ApiError("Yeni sürüm bulunamadı.")
    try:
        data = _fetch(info["zip"], timeout=60)
    except Exception:  # noqa: BLE001
        raise ApiError("Güncelleme indirilemedi; internet bağlantınızı kontrol edin.")
    tmp = tempfile.NamedTemporaryFile(delete=False, suffix=".zip")
    try:
        tmp.write(data)
        tmp.close()
        with zipfile.ZipFile(tmp.name) as z:
            names = [n for n in z.namelist() if not n.endswith("/")]
            prefix = os.path.commonprefix(names).rsplit("/", 1)[0] + "/" if names else ""
            files = []
            for n in names:
                rel = n[len(prefix):]
                parts = rel.replace("\\", "/").split("/")
                if not rel or rel.startswith("/") or ".." in parts or ":" in rel:
                    continue
                files.append((n, os.path.join(HERE, *parts)))
            rels = {os.path.relpath(d, HERE).replace("\\", "/") for _, d in files}
            if not {"hapq_server.py", "hapq.html"} <= rels:
                raise ApiError("İndirilen güncelleme beklenen dosyaları içermiyor.")
            backup = os.path.join(HERE, ".eski_surum")
            shutil.rmtree(backup, ignore_errors=True)
            for n, dest in files:
                if os.path.isfile(dest):
                    b = os.path.join(backup, os.path.relpath(dest, HERE))
                    os.makedirs(os.path.dirname(b), exist_ok=True)
                    shutil.copy2(dest, b)
            for n, dest in files:
                os.makedirs(os.path.dirname(dest), exist_ok=True)
                with open(dest + ".yeni", "wb") as f:
                    f.write(z.read(n))
                os.replace(dest + ".yeni", dest)
                if dest.endswith(".command"):
                    os.chmod(dest, 0o755)
    except zipfile.BadZipFile:
        raise ApiError("İndirilen güncelleme bozuk.")
    finally:
        try:
            os.unlink(tmp.name)
        except OSError:
            pass
    restart = not IS_WIN
    if restart:
        threading.Timer(0.8, _restart).start()
    return {"ok": True, "version": info["latest"], "restart": restart}


WO_HOST_RE = re.compile(r"^[A-Za-z0-9][A-Za-z0-9.\-]{0,252}$")


def watchout_status(q):
    """WATCHOUT 7 Director'ın HTTP API'sine (port 3019) kısa bir /info isteği atar."""
    host = ((q.get("host") or [""])[0] or "127.0.0.1").strip()
    if not WO_HOST_RE.match(host):
        raise ApiError("WATCHOUT adresi geçersiz.")
    url = "http://%s:3019/info" % host
    try:
        req = urllib.request.Request(url, headers={"User-Agent": UA})
        with urllib.request.urlopen(req, timeout=2) as r:
            raw = r.read(65536)
    except Exception:  # noqa: BLE001
        return {"ok": False, "host": host}
    ver = ""
    try:
        j = json.loads(raw)
        stack = [j]
        while stack and not ver:
            o = stack.pop()
            if isinstance(o, dict):
                for k, v in o.items():
                    if isinstance(v, str) and "version" in k.lower() and re.match(r"\d", v):
                        ver = v
                        break
                    if isinstance(v, (dict, list)):
                        stack.append(v)
            elif isinstance(o, list):
                stack.extend(o)
    except ValueError:
        pass
    return {"ok": True, "host": host, "version": ver[:32]}


def _restart():
    """Mac/Linux: aynı pencerede yeni sürümle yeniden başlar."""
    try:
        if SRV:
            SRV.server_close()
        sys.stdout.flush()
        args = [a for a in sys.argv[1:]]
        if "--no-browser" not in args:
            args.append("--no-browser")
        os.execv(sys.executable, [sys.executable, os.path.abspath(__file__)] + args)
    except Exception as ex:  # noqa: BLE001
        print("Yeniden başlatılamadı (%s); programı kapatıp yeniden açın." % ex)


# ---------------------------------------------------------------- tarama

def analyze(path):
    e = {"src": path, "name": os.path.basename(path), "notes": [], "ok": True,
         "w": 0, "h": 0, "dur": 0.0, "fps": 0.0, "frames": 0, "audio": None}
    try:
        e["size"] = os.path.getsize(path)
    except OSError:
        e["size"] = 0
    try:
        r = run([FFPROBE, "-v", "error", "-show_streams", "-show_format", "-of", "json", path], 120)
        data = json.loads(txt(r.stdout) or "{}")
    except Exception:  # noqa: BLE001
        data = {}
    streams = data.get("streams") or []
    v = next((s for s in streams if s.get("codec_type") == "video"
              and not (s.get("disposition") or {}).get("attached_pic")), None)
    if not v:
        e["ok"] = False
        e["notes"].append(["err", "Video akışı bulunamadı (dosya bozuk ya da video değil)."])
        return e

    w, h = int(v.get("width") or 0), int(v.get("height") or 0)
    pf = v.get("pix_fmt") or ""
    cs = (v.get("color_space") or "").lower()
    cr = (v.get("color_range") or "").lower()
    rgb = bool(RGB_RE.match(pf)) or cs == "gbr"
    tag = TAG2M.get(cs)
    if pf.startswith("yuvj"):
        rng, rng_tag = "pc", True
    elif cr in ("tv", "pc"):
        rng, rng_tag = cr, True
    else:
        rng, rng_tag = "tv", False
    # Etiketsiz dosyayı sıradan bir oynatıcı nasıl gösterir: HD ve üstü BT.709, SD BT.601
    player = tag or ("bt709" if (w >= 1280 or h >= 720) else "bt601")

    fps_r, fps_a = frac(v.get("r_frame_rate")), frac(v.get("avg_frame_rate"))
    fmt = data.get("format") or {}
    nb = str(v.get("nb_frames") or "")
    bpr = str(v.get("bits_per_raw_sample") or "")
    m = re.search(r"p(\d+)(le|be)$", pf)
    bits = int(bpr) if bpr.isdigit() else (int(m.group(1)) if m else 8)

    e.update({
        "vidx": int(v.get("index") or 0), "w": w, "h": h,
        "codec": v.get("codec_name") or "?", "pix_fmt": pf, "bits": bits,
        "fps": fps_a or fps_r, "fps_str": v.get("r_frame_rate") or "",
        "dur": frac(v.get("duration")) or frac(fmt.get("duration")),
        "frames": int(nb) if nb.isdigit() else 0,
        "alpha": bool(ALPHA_RE.match(pf)),
        "is_hap": (v.get("codec_name") or "") == "hap",
        "color": {"space": cs or "unknown", "range": rng, "range_tag": rng_tag,
                  "transfer": (v.get("color_transfer") or "unknown").lower(),
                  "primaries": (v.get("color_primaries") or "unknown").lower(),
                  "rgb": rgb, "tag": tag, "player": player},
    })
    auds = [s for s in streams if s.get("codec_type") == "audio"]
    if auds:
        a = auds[0]
        e["audio"] = {"n": len(auds), "rate": int(frac(a.get("sample_rate"))),
                      "ch": int(a.get("channels") or 0), "codec": a.get("codec_name") or "?"}

    if w % 4 or h % 4:
        e["ok"] = False
        e["notes"].append(["err", "Boyut %d×%d: HAP için en ve boy 4'ün katı olmalı. "
                                  "Kaynağı 4'ün katına kırpıp yeniden verin." % (w, h)])
    if e["is_hap"]:
        e["notes"].append(["info", "Zaten HAP; yeniden dönüştürmeye gerek yok."])
    if bits > 8:
        e["notes"].append(["info", "%d bit kaynak; HAP 8 bit saklar (normal)." % bits])
    if fps_r and fps_a and abs(fps_r - fps_a) / fps_r > 0.01:
        e["notes"].append(["warn", "Kare hızı değişken olabilir (ortalama %.3f, nominal %.3f). "
                                   "Ayarlardan kare hızını sabitleyin." % (fps_a, fps_r)])
    if not e["dur"]:
        e["notes"].append(["info", "Süre okunamadı; ilerleme yüzdesi gösterilemez."])
    return e


def list_videos(ind, rec, outd):
    outn = os.path.normcase(os.path.abspath(outd))

    def ok(name):
        return not name.startswith(".") and os.path.splitext(name)[1].lower() in VIDEO_EXT

    res = []
    if rec:
        for root, dirs, files in os.walk(ind):
            # önceki çıktı klasörleri (hapq) kaynak sanılmasın
            dirs[:] = sorted((d for d in dirs if not d.startswith(".")
                              and d.lower() not in ("_hata_loglari", "hapq")
                              and os.path.normcase(os.path.abspath(os.path.join(root, d))) != outn),
                             key=str.lower)
            res += [os.path.join(root, f) for f in sorted(files, key=str.lower) if ok(f)]
    else:
        res = [os.path.join(ind, f) for f in sorted(os.listdir(ind), key=str.lower)
               if ok(f) and os.path.isfile(os.path.join(ind, f))]
    return res


def plan_outputs(entries, ind, outd):
    """Çıkış adlarını belirler: aynı adlı kaynaklar (a.mp4 + a.mov) çakışmaz,
    çıkış klasörü kaynak klasörüyse kaynağın üstüne yazılmaz."""
    groups = {}
    for e in entries:
        od = os.path.normpath(os.path.join(outd, os.path.relpath(os.path.dirname(e["src"]), ind)))
        stem = os.path.splitext(e["name"])[0]
        groups.setdefault((os.path.normcase(od), stem.lower()), []).append((e, od, stem))
    for lst in groups.values():
        for e, od, stem in lst:
            s = stem
            if len(lst) > 1:
                s += "_" + os.path.splitext(e["name"])[1][1:].lower()
            if os.path.normcase(od) == os.path.normcase(os.path.dirname(e["src"])):
                s += "_hapq"
            e["out"] = os.path.join(od, s + ".mov")
            e["logdir"] = os.path.join(outd, "_hata_loglari")


def disk_free(path):
    p = os.path.abspath(path)
    while p and not os.path.exists(p):
        parent = os.path.dirname(p)
        if parent == p:
            break
        p = parent
    try:
        return shutil.disk_usage(p).free
    except OSError:
        return None


SCAN = {}
SCAN_META = {"input": "", "output": "", "recursive": False, "free": None, "order": []}
SCAN_LOCK = threading.Lock()


def scan(body):
    if RUNNER.state == "running":
        raise ApiError("Dönüştürme sürerken yeniden taranamaz.")
    ind = (body.get("input") or "").strip()
    outd = (body.get("output") or "").strip()
    if not ind or not os.path.isdir(ind):
        raise ApiError("Giriş klasörü bulunamadı: %s" % ind)
    ind = os.path.abspath(ind)
    outd = os.path.abspath(outd) if outd else os.path.join(ind, "hapq")
    rec = bool(body.get("recursive"))
    paths = list_videos(ind, rec, outd)
    with ThreadPoolExecutor(max_workers=6) as ex:
        entries = list(ex.map(analyze, paths))
    for i, e in enumerate(entries):
        e["id"] = str(i)
        e["rel"] = os.path.relpath(e["src"], ind)
    plan_outputs(entries, ind, outd)
    for e in entries:
        e["exists"] = os.path.exists(e["out"])
        e["out_rel"] = os.path.relpath(e["out"], outd)
    with SCAN_LOCK:
        SCAN.clear()
        SCAN.update({e["id"]: e for e in entries})
        SCAN_META.update(input=ind, output=outd, recursive=rec, free=disk_free(outd),
                         order=[e["id"] for e in entries])
    return session()


def session():
    with SCAN_LOCK:
        files = [SCAN[i] for i in SCAN_META["order"] if i in SCAN]
        meta = dict(SCAN_META)
    for e in files:  # dönüştürme sonrası "var" bilgisi güncel kalsın
        if "out" in e:
            e["exists"] = os.path.exists(e["out"])
    return {"input": meta["input"], "output": meta["output"], "recursive": meta["recursive"],
            "free": disk_free(meta["output"]) if meta["output"] else None,
            "files": files, "runner": RUNNER.snapshot()}


# ---------------------------------------------------------------- dönüştürme

def src_chain(e, matrix):
    """Kaynağı RGB'ye çeviren filtre başı. RGB kaynakta matris yok."""
    if e["color"]["rgb"] or not matrix:
        return ""
    return "scale=in_color_matrix=%s:in_range=%s" % (matrix, e["color"]["range"])


def build_cmd(e, s, part):
    cmd = [FFMPEG, "-hide_banner", "-nostdin", "-y", "-loglevel", "error",
           "-progress", "pipe:1", "-nostats", "-i", e["src"], "-map", "0:%d" % e["vidx"]]
    if s["audio"] != "none" and e.get("audio"):
        cmd += ["-map", "0:a?", "-c:a", s["audio"]]
    else:
        cmd += ["-an"]
    chain = [c for c in (src_chain(e, e["matrix"]), "format=rgba") if c]
    cmd += ["-vf", ",".join(chain)]
    if s["cfr"]:
        r = s["cfr"] if s["cfr"] != "src" else (e.get("fps_str") or "25")
        if re.match(r"^\d+(\.\d+)?(/\d+)?$", r):
            cmd += ["-r", r]
    cmd += ["-c:v", "hap", "-format", s["format"], "-compressor", s["compressor"]]
    if s["compressor"] == "snappy":
        cmd += ["-chunks", str(s["chunks"])]
    cmd += ["-f", "mov", part]
    return cmd


def small_size(w, h, W):
    W = max(16, min(W, w or W))
    H = max(8, int(round(W * (h or W) / float(w or W) / 2.0)) * 2)
    return W, H


def grab(path, mapspec, t, pre, W, H, png=False):
    chain = (pre + "," if pre else "") + "format=rgb24,scale=%d:%d:flags=area" % (W, H)
    cmd = [FFMPEG, "-v", "error", "-nostdin"]
    if t > 0:
        cmd += ["-ss", "%.3f" % t]
    cmd += ["-i", path, "-map", mapspec, "-frames:v", "1", "-vf", chain]
    if png:
        cmd += ["-f", "image2pipe", "-c:v", "png", "pipe:1"]
    else:
        cmd += ["-f", "rawvideo", "-pix_fmt", "rgb24", "pipe:1"]
    r = run(cmd, 300)
    if png:
        return r.stdout if r.stdout[:4] == b"\x89PNG" else None
    return r.stdout if len(r.stdout) == W * H * 3 else None


MNAME = {"bt709": "BT.709", "bt601": "BT.601", "bt2020": "BT.2020", "smpte240m": "SMPTE 240M", "fcc": "FCC"}


def verify(e, out):
    """Çıktıyı, kaynağın sıradan bir oynatıcıda göründüğü hâliyle karşılaştırır.
    Ayrıca kaynağın başka bir renk yorumuyla da karşılaştırır: çıktı o yoruma daha
    yakınsa renk kayması var demektir. (Hareket ya da sıkıştırma farkı iki
    karşılaştırmayı eşit etkiler; renk kayması etkilemez.)
    Değerler 0-255 ölçeğinde ortalama farktır."""
    W, H = small_size(e["w"], e["h"], 256)
    c = e["color"]
    ref = c["player"]
    alt = None if c["rgb"] else ("bt601" if ref != "bt601" else "bt709")
    ts = [e["dur"] * k for k in (0.2, 0.5, 0.8)] if e["dur"] > 1 else [0]
    sums, ab_ref, ab_alt, n = [0, 0, 0], 0, 0, 0
    for t in ts:
        b = grab(out, "0:v:0", t, "", W, H)
        a = grab(e["src"], "0:%d" % e["vidx"], t, src_chain(e, ref), W, H)
        if not a or not b:
            continue
        d = [y - x for x, y in zip(a, b)]
        for ch in range(3):
            sums[ch] += sum(d[ch::3])
        ab_ref += sum(map(abs, d))
        if alt:
            a2 = grab(e["src"], "0:%d" % e["vidx"], t, src_chain(e, alt), W, H)
            if a2:
                ab_alt += sum(abs(y - x) for x, y in zip(a2, b))
        n += len(d) // 3
    if not n:
        return {"lvl": "warn", "msg": "Doğrulama karesi alınamadı."}
    mad = round(ab_ref / float(n * 3), 2)
    mad_alt = round(ab_alt / float(n * 3), 2) if alt and ab_alt else None
    res = {"bias": [round(s / float(n), 2) for s in sums], "mad": mad, "mad_alt": mad_alt,
           "ref": ref, "alt": alt, "used": e["matrix"]}
    closer_to_alt = mad_alt is not None and mad > 2 and mad > mad_alt * 1.25
    if closer_to_alt:
        res["lvl"] = "warn"
        why = "etiketi" if c["tag"] else "boyutuna göre çoğu oynatıcı"
        res["msg"] = ("Renk kayması var: çıktı kaynağın %s yorumuna uyuyor, oysa dosyanın %s "
                      "%s kullanıyor." % (MNAME[alt], why, MNAME[ref]))
    elif max(abs(x) for x in res["bias"]) >= 2:
        res["lvl"] = "warn"
        res["msg"] = "Beklenmeyen renk sapması. Önizlemeyi kontrol edin."
    elif mad >= 4:
        res["lvl"] = "info"
        res["msg"] = "Renk kayması yok; fark yüksek (hareketli sahnede kare kayması olabilir)."
    else:
        res["lvl"] = "ok"
        res["msg"] = "Renkler kaynakla aynı."
    return res


class Runner(object):
    def __init__(self):
        self.lock = threading.Lock()
        self.state = "idle"
        self.files = {}
        self.procs = set()
        self.cancelled = False
        self.started = None
        self.finished = None
        self.thread = None

    def snapshot(self):
        with self.lock:
            return {"state": self.state, "files": {k: dict(v) for k, v in self.files.items()},
                    "started": self.started, "finished": self.finished, "now": time.time()}

    def _set(self, fid, **kw):
        with self.lock:
            self.files[fid].update(kw)

    def start(self, items, settings):
        with self.lock:
            if self.state == "running":
                raise ApiError("Zaten bir dönüştürme sürüyor.")
            self.state = "running"
            self.cancelled = False
            self.started, self.finished = time.time(), None
            self.files = {e["id"]: {"status": "waiting", "progress": 0.0, "speed": "", "msg": "",
                                    "verify": None, "matrix": e["matrix"]} for e in items}
        self.thread = threading.Thread(target=self._all, args=(items, settings), daemon=True)
        self.thread.start()

    def cancel(self):
        with self.lock:
            self.cancelled = True
            procs = list(self.procs)
        for p in procs:
            try:
                p.terminate()
            except OSError:
                pass

    def _all(self, items, s):
        with ThreadPoolExecutor(max_workers=s["jobs"]) as ex:
            list(ex.map(lambda e: self._one(e, s), items))
        with self.lock:
            self.state = "cancelled" if self.cancelled else "done"
            self.finished = time.time()

    def _one(self, e, s):
        try:
            self._one_inner(e, s)
        except Exception as ex:  # noqa: BLE001
            self._set(e["id"], status="failed", msg=str(ex))

    def _one_inner(self, e, s):
        fid, out = e["id"], e["out"]
        if self.cancelled:
            self._set(fid, status="cancelled")
            return
        if os.path.exists(out) and s["skip_existing"]:
            self._set(fid, status="skipped", progress=1.0, msg="Çıktı zaten var, atlandı.")
            return
        od = os.path.dirname(out)
        os.makedirs(od, exist_ok=True)
        # Yazılırken video uzantısı taşımasın: izlenen klasörler (ör. WATCHOUT Asset Watcher)
        # yarım dosyayı almasın. Bitince asıl adına çevrilir.
        part = os.path.join(od, "." + os.path.splitext(os.path.basename(out))[0] + ".hapq-yaziliyor")
        fd, logp = tempfile.mkstemp(suffix=".log", prefix="hapq_")
        self._set(fid, status="running", progress=0.0)
        with os.fdopen(fd, "wb") as log:
            p = subprocess.Popen(build_cmd(e, s, part), stdout=subprocess.PIPE, stderr=log,
                                 stdin=subprocess.DEVNULL, creationflags=NOWIN)
            with self.lock:
                self.procs.add(p)
            dur = e.get("dur") or 0
            for raw in p.stdout:
                line = raw.decode("utf-8", "replace").strip()
                if line.startswith("out_time_us="):
                    v = line[12:]
                    if v.isdigit() and dur > 0:
                        self._set(fid, progress=min(0.999, int(v) / 1e6 / dur))
                elif line.startswith("speed="):
                    self._set(fid, speed=line[6:].strip())
            p.wait()
            with self.lock:
                self.procs.discard(p)
        with open(logp, "rb") as f:
            err = txt(f.read()).strip()
        try:
            os.remove(logp)
        except OSError:
            pass

        if self.cancelled:
            self._rm(part)
            self._set(fid, status="cancelled", msg="Durduruldu.")
            return
        if p.returncode != 0 or not os.path.exists(part):
            self._rm(part)
            msg = "\n".join(err.splitlines()[-3:]) or ("ffmpeg çıkış kodu %s" % p.returncode)
            logfile = ""
            try:
                os.makedirs(e["logdir"], exist_ok=True)
                logfile = os.path.join(e["logdir"], os.path.splitext(os.path.basename(out))[0] + ".log")
                with open(logfile, "w", encoding="utf-8") as f:
                    f.write(" ".join('"%s"' % a if " " in a else a for a in build_cmd(e, s, part)))
                    f.write("\n\n" + err + "\n")
            except OSError:
                pass
            self._set(fid, status="failed", msg=msg, log=logfile)
            return
        os.replace(part, out)
        if s["verify"]:
            self._set(fid, status="verifying", progress=1.0)
            try:
                self._set(fid, verify=verify(e, out))
            except Exception as ex:  # noqa: BLE001
                self._set(fid, verify={"lvl": "warn", "msg": "Doğrulama yapılamadı: %s" % ex})
        self._set(fid, status="done", progress=1.0, size=os.path.getsize(out))

    @staticmethod
    def _rm(path):
        try:
            os.remove(path)
        except OSError:
            pass


RUNNER = Runner()


def start(body):
    s = body.get("settings") or {}
    cfr = str(s.get("cfr") or "")
    settings = {
        "format": s.get("format") if s.get("format") in FORMATS else "hap_q",
        "compressor": "none" if s.get("compressor") == "none" else "snappy",
        "chunks": clamp(s.get("chunks"), 1, 64, 8),
        "jobs": clamp(s.get("jobs"), 1, 16, 2),
        "audio": s.get("audio") if s.get("audio") in AUDIO else "pcm_s24le",
        "cfr": cfr if (cfr == "src" or re.match(r"^\d+(\.\d+)?(/\d+)?$", cfr)) else "",
        "skip_existing": bool(s.get("skip_existing", True)),
        "verify": bool(s.get("verify", True)),
    }
    matrices = body.get("matrices") or {}
    items = []
    with SCAN_LOCK:
        for fid in body.get("ids") or []:
            e = SCAN.get(str(fid))
            if not e or not e["ok"]:
                continue
            m = matrices.get(str(fid))
            if e["color"]["rgb"]:
                m = None
            elif m not in MATRICES:
                m = e["color"]["tag"] or "bt709"
            items.append(dict(e, matrix=m))
    if not items:
        raise ApiError("Dönüştürülecek dosya seçilmedi.")
    RUNNER.start(items, settings)
    return RUNNER.snapshot()


def thumb(q):
    fid = (q.get("id") or [""])[0]
    which = (q.get("which") or ["src"])[0]
    m = (q.get("m") or [""])[0]
    with SCAN_LOCK:
        e = SCAN.get(fid)
    if not e or not e.get("w"):
        raise ApiError("Dosya bulunamadı.")
    W, H = small_size(e["w"], e["h"], 1280)
    t = e["dur"] * 0.5 if e["dur"] > 1 else 0
    if which == "out":
        if not os.path.exists(e["out"]):
            raise ApiError("Çıktı henüz yok.")
        img = grab(e["out"], "0:v:0", t, "", W, H, png=True)
    else:
        img = grab(e["src"], "0:%d" % e["vidx"], t,
                   src_chain(e, m if m in MATRICES else e["color"]["player"]), W, H, png=True)
    if not img:
        raise ApiError("Kare alınamadı.")
    return img


# ---------------------------------------------------------------- klasör seçimi

PS_PICK = r"""
Add-Type -AssemblyName System.Windows.Forms
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$owner = New-Object System.Windows.Forms.Form
$owner.TopMost = $true
$d = New-Object System.Windows.Forms.FolderBrowserDialog
$d.Description = $env:HAPQ_TITLE
$d.ShowNewFolderButton = $true
if ($env:HAPQ_START -and (Test-Path -LiteralPath $env:HAPQ_START)) { $d.SelectedPath = $env:HAPQ_START }
if ($d.ShowDialog($owner) -eq [System.Windows.Forms.DialogResult]::OK) { Write-Output $d.SelectedPath }
$owner.Dispose()
"""

TK_PICK = r"""
import os, sys, tkinter as tk
from tkinter import filedialog
r = tk.Tk(); r.withdraw(); r.attributes('-topmost', True)
p = filedialog.askdirectory(title=os.environ.get('HAPQ_TITLE', ''), initialdir=os.environ.get('HAPQ_START') or None)
sys.stdout.buffer.write((p or '').encode('utf-8'))
"""


def pick_folder(title, start_dir):
    env = dict(os.environ, HAPQ_TITLE=title, HAPQ_START=start_dir or "")
    out = None
    try:
        if IS_MAC:
            esc = lambda s: s.replace("\\", "\\\\").replace('"', '\\"')  # noqa: E731
            script = 'POSIX path of (choose folder with prompt "%s"' % esc(title)
            if start_dir and os.path.isdir(start_dir):
                script += ' default location (POSIX file "%s")' % esc(start_dir)
            script += ")"
            r = run(["osascript", "-e", "activate", "-e", script], 3600)
            out = txt(r.stdout).strip() if r.returncode == 0 else ""
        elif IS_WIN:
            enc = base64.b64encode(PS_PICK.encode("utf-16-le")).decode("ascii")
            r = run(["powershell", "-NoProfile", "-STA", "-ExecutionPolicy", "Bypass",
                     "-EncodedCommand", enc], 3600, env)
            out = txt(r.stdout).strip() if r.returncode == 0 else None
        elif shutil.which("zenity"):
            r = run(["zenity", "--file-selection", "--directory", "--title", title], 3600)
            out = txt(r.stdout).strip() if r.returncode == 0 else ""
    except (OSError, subprocess.SubprocessError):
        out = None
    if out is None:  # yedek: tkinter
        try:
            r = run([sys.executable, "-c", TK_PICK], 3600, env)
            out = txt(r.stdout).strip()
        except (OSError, subprocess.SubprocessError):
            raise ApiError("Klasör penceresi açılamadı; yolu kutuya yapıştırın.")
    out = (out or "").rstrip("/\\") or ""
    return {"path": out}


def open_folder(path):
    if not path or not os.path.isdir(path):
        raise ApiError("Klasör henüz yok.")
    if IS_WIN:
        os.startfile(path)  # noqa: S606
    elif IS_MAC:
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])
    return {"ok": True}


# ---------------------------------------------------------------- HTTP

class Handler(BaseHTTPRequestHandler):
    server_version = "HAPQ/1"

    def log_message(self, *a):
        pass

    def _host_ok(self):
        host = (self.headers.get("Host") or "").rsplit(":", 1)[0]
        return host in ("127.0.0.1", "localhost")

    def _token_ok(self, q=None):
        tok = self.headers.get("X-Token") or ((q or {}).get("token") or [""])[0]
        return secrets.compare_digest(tok, TOKEN)

    def _send(self, code, body, ctype="application/json; charset=utf-8"):
        if isinstance(body, (dict, list)):
            body = json.dumps(body, ensure_ascii=False).encode("utf-8")
        elif isinstance(body, str):
            body = body.encode("utf-8")
        try:
            self.send_response(code)
            self.send_header("Content-Type", ctype)
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(body)
        except (BrokenPipeError, ConnectionResetError):
            pass

    def do_GET(self):  # noqa: N802
        if not self._host_ok():
            return self._send(403, {"error": "Yasak."})
        u = urlparse(self.path)
        q = parse_qs(u.query)
        if u.path in ("/", "/index.html"):
            with open(os.path.join(HERE, "hapq.html"), encoding="utf-8") as f:
                html = f.read().replace("__HAPQ_TOKEN__", TOKEN)
            return self._send(200, html, "text/html; charset=utf-8")
        if not u.path.startswith("/api/"):
            return self._send(404, {"error": "Bulunamadı."})
        if not self._token_ok(q):
            return self._send(403, {"error": "Oturum geçersiz; sayfayı yenileyin."})
        try:
            if u.path == "/api/env":
                return self._send(200, get_env())
            if u.path == "/api/session":
                return self._send(200, session())
            if u.path == "/api/status":
                return self._send(200, RUNNER.snapshot())
            if u.path == "/api/watchout":
                return self._send(200, watchout_status(q))
            if u.path == "/api/updates":
                return self._send(200, check_updates())
            if u.path == "/api/thumb":
                return self._send(200, thumb(q), "image/png")
        except ApiError as ex:
            return self._send(400, {"error": str(ex)})
        except Exception as ex:  # noqa: BLE001
            return self._send(500, {"error": "Beklenmeyen hata: %s" % ex})
        return self._send(404, {"error": "Bulunamadı."})

    def do_POST(self):  # noqa: N802
        if not self._host_ok() or not self._token_ok():
            return self._send(403, {"error": "Oturum geçersiz; sayfayı yenileyin."})
        try:
            n = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(n) or b"{}") if n else {}
            p = urlparse(self.path).path
            if p == "/api/pick":
                title = "Giriş klasörünü seçin" if body.get("kind") == "input" else "Çıkış klasörünü seçin"
                return self._send(200, pick_folder(title, body.get("start") or ""))
            if p == "/api/scan":
                return self._send(200, scan(body))
            if p == "/api/start":
                return self._send(200, start(body))
            if p == "/api/cancel":
                RUNNER.cancel()
                return self._send(200, RUNNER.snapshot())
            if p == "/api/update":
                return self._send(200, apply_update())
            if p == "/api/open":
                return self._send(200, open_folder(body.get("path") or ""))
        except ApiError as ex:
            return self._send(400, {"error": str(ex)})
        except Exception as ex:  # noqa: BLE001
            return self._send(500, {"error": "Beklenmeyen hata: %s" % ex})
        return self._send(404, {"error": "Bulunamadı."})


def main():
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:  # noqa: BLE001
        pass
    args = sys.argv[1:]
    port = 8770
    if "--port" in args:
        port = clamp(args[args.index("--port") + 1], 1024, 65535, 8770)
    srv = None
    for p in range(port, port + 30):
        try:
            srv = ThreadingHTTPServer(("127.0.0.1", p), Handler)
            port = p
            break
        except OSError:
            continue
    if srv is None:
        print("Boş port bulunamadı.")
        sys.exit(1)
    srv.daemon_threads = True
    global SRV
    SRV = srv
    url = "http://127.0.0.1:%d/" % port
    env = get_env()
    print("HAP Dönüştürücü %s çalışıyor: %s" % (VERSION, url))
    if env["problem"]:
        print("SORUN: %s" % env["problem"])
        if FF_FOUND:
            print("Bulunan ffmpeg kurulumları (hiçbiri HAP kodlayamıyor):")
            for f, _ in FF_FOUND:
                print("   %s" % f)
        print("Çözüm: " + ("Terminal'de  brew install ffmpeg-full" if IS_MAC else
                           "PowerShell'de  winget install Gyan.FFmpeg  (ya da ffmpeg.exe ve ffprobe.exe'yi bu klasöre koyun)"
                           if IS_WIN else "snappy destekli bir ffmpeg kurun"))
    else:
        print("ffmpeg: %s" % FFMPEG)
        print("        %s" % env["version"])
    print("Kapatmak için bu pencerede Ctrl+C'ye basın (ya da pencereyi kapatın).")
    if "--no-browser" not in args:
        threading.Timer(0.7, lambda: webbrowser.open(url)).start()
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        RUNNER.cancel()
        if RUNNER.thread:
            RUNNER.thread.join(timeout=10)
        print("\nKapatıldı.")


if __name__ == "__main__":
    main()
