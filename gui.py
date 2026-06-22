"""
sCO2 Termodinamik Çevrim Tasarımcısı — TEKNOFEST
Bu dosya, masaüstü Flet uygulamasının ana giriş noktasıdır.
- `gui.py` çalıştırıldığında pencere açılır, bileşen yerleştirme,
  port bağlama, sınır şartı girişi ve çözüm sonuçları gösterilir.
- Hesaplama motoru `core/` altındaki modüllerden yüklenir.
- CoolProp kurulumu yoksa GUI yine açılır ancak hesaplama devresi
  çalıştırıldığında kullanıcıya uyarı verir.
"""

import flet as ft
import flet.canvas as cv
import math

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 0: ARKA PLAN MOTORU (güvenli yükleme)
# ─────────────────────────────────────────────────────────────────────────────
# Bileşen motorunu güvenli biçimde yükle. Eğer bağımlılık yoksa GUI yine
# başlar, ancak çözüm fonksiyonu hata yerine kullanıcıya bilgi gösterir.
try:
    from core.components import (Turbine, Compressor, Recuperator,
                                  SimpleHeatExchanger, Splitter, Mixer)
    from core.states import State
    from core.engine import CycleSolver
    MOTOR_HAZIR = True
except ImportError:
    MOTOR_HAZIR = False

# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 1: YAPILANDIRMA SABİTLERİ
# ─────────────────────────────────────────────────────────────────────────────
W, H = 100, 50  # Bileşen boyutları (piksel)

BILESEN_CONFIGS = {
    "Turbine": {
        "renk": ft.Colors.ORANGE_700,
        "etiket": "T",
        "portlar": [
            {"ad": "Giriş",  "x": 0, "y": H // 2, "giris": True},
            {"ad": "Çıkış",  "x": W, "y": H // 2, "giris": False},
        ],
        "params": {"verim": 0.92},
    },
    "Compressor": {
        "renk": ft.Colors.BLUE_700,
        "etiket": "C",
        "portlar": [
            {"ad": "Giriş",  "x": 0, "y": H // 2, "giris": True},
            {"ad": "Çıkış",  "x": W, "y": H // 2, "giris": False},
        ],
        "params": {"verim": 0.89},
    },
    "Recuperator": {
        "renk": ft.Colors.PURPLE_600,
        "etiket": "REC",
        "portlar": [
            {"ad": "Sıcak Giriş",  "x": 0, "y": H // 4,     "giris": True},
            {"ad": "Soğuk Giriş",  "x": 0, "y": 3*H // 4,   "giris": True},
            {"ad": "Sıcak Çıkış",  "x": W, "y": H // 4,     "giris": False},
            {"ad": "Soğuk Çıkış",  "x": W, "y": 3*H // 4,   "giris": False},
        ],
        "params": {"etkinlik": 0.95},
    },
    "Heat Exchanger": {
        "renk": ft.Colors.RED_600,
        "etiket": "HX",
        "portlar": [
            {"ad": "Giriş",  "x": 0, "y": H // 2, "giris": True},
            {"ad": "Çıkış",  "x": W, "y": H // 2, "giris": False},
        ],
        "params": {},
    },
    "Splitter": {
        "renk": ft.Colors.GREY_600,
        "etiket": "SPL",
        "portlar": [
            {"ad": "Giriş",   "x": 0, "y": H // 2,   "giris": True},
            {"ad": "Çıkış 1", "x": W, "y": H // 4,   "giris": False},
            {"ad": "Çıkış 2", "x": W, "y": 3*H // 4, "giris": False},
        ],
        "params": {"oran_1": 0.65, "oran_2": 0.35},
    },
    "Mixer": {
        "renk": ft.Colors.TEAL_600,
        "etiket": "MIX",
        "portlar": [
            {"ad": "Giriş 1", "x": 0, "y": H // 4,   "giris": True},
            {"ad": "Giriş 2", "x": 0, "y": 3*H // 4, "giris": True},
            {"ad": "Çıkış",   "x": W, "y": H // 2,   "giris": False},
        ],
        "params": {},
    },
}

AKISKANLAR = ["CarbonDioxide", "Water", "Nitrogen", "Helium", "Air", "Hydrogen"]

def port_anahtari(ad: str) -> str:
    """Turkce/mojibake farklarindan etkilenmeden port adlarini eslestir."""
    ceviri = str.maketrans({
        "ı": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
        "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
        "Å": "s", "Ÿ": "g", "Ä": "", "±": "i", "‡": "c", "§": "s",
        "Ã": "", "¼": "u", "¶": "o",
    })
    return "".join(ch for ch in ad.translate(ceviri).lower() if ch.isalnum())


def port_bul(tip: str, ad: str):
    hedef = port_anahtari(ad)
    return next(
        (p for p in BILESEN_CONFIGS[tip]["portlar"] if port_anahtari(p["ad"]) == hedef),
        None,
    )

# ─────────────────────────────────────────────────────────────────────────────
# HAZIR SABLON TANIMLARI
# ─────────────────────────────────────────────────────────────────────────────
# Her sablon: bilesenler listesi + baglantilar listesi
# bilesen: {"tip", "isim", "left", "top", "ayarlar"}
# baglanti: {"kaynak_isim", "kaynak_port", "hedef_isim", "hedef_port", "sinir_sartlari"}
SABLONLAR = {
    "Basit Brayton": {
        "akiskan": "CarbonDioxide",
        "bilesenler": [
            {"tip": "Compressor",    "isim": "C1",       "left": 150, "top": 200, "ayarlar": {"verim": 0.89}},
            {"tip": "Heat Exchanger","isim": "Reaktor",  "left": 330, "top": 200, "ayarlar": {}},
            {"tip": "Turbine",       "isim": "T1",       "left": 510, "top": 200, "ayarlar": {"verim": 0.92}},
            {"tip": "Heat Exchanger","isim": "Radyator", "left": 330, "top": 340, "ayarlar": {}},
        ],
        "baglantilar": [
            {"kaynak_isim": "C1",      "kaynak_port": "Cikis",  "hedef_isim": "Reaktor",  "hedef_port": "Giris",  "sinir_sartlari": {"P": 21000000.0}},
            {"kaynak_isim": "Reaktor", "kaynak_port": "Cikis",  "hedef_isim": "T1",       "hedef_port": "Giris",  "sinir_sartlari": {"T": 823.0}},
            {"kaynak_isim": "T1",      "kaynak_port": "Cikis",  "hedef_isim": "Radyator", "hedef_port": "Giris",  "sinir_sartlari": {}},
            {"kaynak_isim": "Radyator","kaynak_port": "Cikis",  "hedef_isim": "C1",       "hedef_port": "Giris",  "sinir_sartlari": {"T": 305.0, "P": 7500000.0, "m_dot": 100.0}},
        ],
    },
    "Rejeneratif Brayton": {
        "akiskan": "CarbonDioxide",
        "bilesenler": [
            {"tip": "Compressor",    "isim": "C1",    "left": 120, "top": 220, "ayarlar": {"verim": 0.89}},
            {"tip": "Recuperator",   "isim": "REC1",  "left": 290, "top": 160, "ayarlar": {"etkinlik": 0.92}},
            {"tip": "Heat Exchanger","isim": "Reaktor","left": 490, "top": 160, "ayarlar": {}},
            {"tip": "Turbine",       "isim": "T1",    "left": 660, "top": 160, "ayarlar": {"verim": 0.92}},
            {"tip": "Heat Exchanger","isim": "Radyator","left": 290, "top": 320, "ayarlar": {}},
        ],
        "baglantilar": [
            {"kaynak_isim": "C1",      "kaynak_port": "Cikis",       "hedef_isim": "REC1",    "hedef_port": "Soguk Giris", "sinir_sartlari": {"P": 21000000.0}},
            {"kaynak_isim": "REC1",    "kaynak_port": "Soguk Cikis", "hedef_isim": "Reaktor", "hedef_port": "Giris",       "sinir_sartlari": {}},
            {"kaynak_isim": "Reaktor", "kaynak_port": "Cikis",       "hedef_isim": "T1",      "hedef_port": "Giris",       "sinir_sartlari": {"T": 823.0}},
            {"kaynak_isim": "T1",      "kaynak_port": "Cikis",       "hedef_isim": "REC1",    "hedef_port": "Sicak Giris", "sinir_sartlari": {}},
            {"kaynak_isim": "REC1",    "kaynak_port": "Sicak Cikis", "hedef_isim": "Radyator","hedef_port": "Giris",       "sinir_sartlari": {}},
            {"kaynak_isim": "Radyator","kaynak_port": "Cikis",       "hedef_isim": "C1",      "hedef_port": "Giris",       "sinir_sartlari": {"T": 305.0, "P": 7500000.0, "m_dot": 100.0}},
        ],
    },
    "Recompression sCO2": {
        "akiskan": "CarbonDioxide",
        "bilesenler": [
            {"tip": "Heat Exchanger", "isim": "CLR1",    "left": 80,  "top": 315, "ayarlar": {}},
            {"tip": "Compressor",     "isim": "CMP1",    "left": 250, "top": 315, "ayarlar": {"verim": 0.89}},
            {"tip": "Recuperator",    "isim": "LTR1",    "left": 405, "top": 255, "ayarlar": {"etkinlik": 0.95}},
            {"tip": "Splitter",       "isim": "SPL1",    "left": 590, "top": 255, "ayarlar": {"oran_1": 0.65, "oran_2": 0.35}},
            {"tip": "Compressor",     "isim": "RCMP1",   "left": 690, "top": 365, "ayarlar": {"verim": 0.89}},
            {"tip": "Mixer",          "isim": "MIX1",    "left": 840, "top": 305, "ayarlar": {}},
            {"tip": "Recuperator",    "isim": "HTR1",    "left": 990, "top": 205, "ayarlar": {"etkinlik": 0.95}},
            {"tip": "Heat Exchanger", "isim": "REACT1",  "left": 1170,"top": 205, "ayarlar": {}},
            {"tip": "Turbine",        "isim": "TUR1",    "left": 1340,"top": 205, "ayarlar": {"verim": 0.92}},
        ],
        "baglantilar": [
            {"etiket": "S1",  "kaynak_isim": "CLR1",   "kaynak_port": "Cikis",       "hedef_isim": "CMP1",   "hedef_port": "Giris",       "sinir_sartlari": {"T": 305.0, "P": 7500000.0}},
            {"etiket": "S2",  "kaynak_isim": "CMP1",   "kaynak_port": "Cikis",       "hedef_isim": "LTR1",   "hedef_port": "Soguk Giris", "sinir_sartlari": {"P": 21000000.0}},
            {"etiket": "S3",  "kaynak_isim": "LTR1",   "kaynak_port": "Soguk Cikis", "hedef_isim": "SPL1",   "hedef_port": "Giris",       "sinir_sartlari": {}},
            {"etiket": "S4",  "kaynak_isim": "SPL1",   "kaynak_port": "Cikis 1",     "hedef_isim": "CLR1",   "hedef_port": "Giris",       "sinir_sartlari": {"m_dot": 65.0}},
            {"etiket": "S5",  "kaynak_isim": "SPL1",   "kaynak_port": "Cikis 2",     "hedef_isim": "RCMP1",  "hedef_port": "Giris",       "sinir_sartlari": {"m_dot": 35.0}},
            {"etiket": "S6",  "kaynak_isim": "RCMP1",  "kaynak_port": "Cikis",       "hedef_isim": "MIX1",   "hedef_port": "Giris 2",     "sinir_sartlari": {"P": 21000000.0}},
            {"etiket": "S7",  "kaynak_isim": "LTR1",   "kaynak_port": "Sicak Cikis", "hedef_isim": "MIX1",   "hedef_port": "Giris 1",     "sinir_sartlari": {"T": 530.0}},
            {"etiket": "S8",  "kaynak_isim": "MIX1",   "kaynak_port": "Cikis",       "hedef_isim": "HTR1",   "hedef_port": "Soguk Giris", "sinir_sartlari": {}},
            {"etiket": "S9",  "kaynak_isim": "HTR1",   "kaynak_port": "Soguk Cikis", "hedef_isim": "REACT1", "hedef_port": "Giris",       "sinir_sartlari": {}},
            {"etiket": "S10", "kaynak_isim": "REACT1", "kaynak_port": "Cikis",       "hedef_isim": "TUR1",   "hedef_port": "Giris",       "sinir_sartlari": {"T": 823.0, "m_dot": 100.0}},
            {"etiket": "S11", "kaynak_isim": "TUR1",   "kaynak_port": "Cikis",       "hedef_isim": "HTR1",   "hedef_port": "Sicak Giris", "sinir_sartlari": {"P": 7500000.0}},
            {"etiket": "S12", "kaynak_isim": "HTR1",   "kaynak_port": "Sicak Cikis", "hedef_isim": "LTR1",   "hedef_port": "Sicak Giris", "sinir_sartlari": {"T": 530.0}},
        ],
    },
}


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 2: VERİ SINIFLARI
# ─────────────────────────────────────────────────────────────────────────────
class Baglanti:
    """İki bileşen portu arasındaki akış bağlantısını temsil eder.

    Bağlantı nesnesi şunları saklar:
    - kaynak/hedef widget referansları
    - bağlantının port konfigürasyonları
    - kullanıcı tarafından girilen sınır şartları
    - motorun çözdüğü durumu
    - otomatik yayılım ve görsel rota verileri
    """

    def __init__(self, kaynak_widget, kaynak_port, hedef_widget, hedef_port, etiket=None):
        self.kaynak_widget = kaynak_widget
        self.kaynak_port   = kaynak_port
        self.hedef_widget  = hedef_widget
        self.hedef_port    = hedef_port
        self.etiket        = etiket
        self.sinir_sartlari: dict = {}  # T, P, m_dot
        self.kullanici_girdileri: dict = {}
        # Örnek: {"P": 21000000.0, "T": 823.0}
        # Kullanıcının elle girdiği değerler burada saklanır.
        # sinir_sartlari ile aynı içeriğe sahip olacak,
        # ama ayrı tutulacak çünkü renk kodlaması için
        # hangi değerin kullanıcıdan geldiğini bilmemiz gerekiyor.
        self.motor_sonuclari: dict = {}
        # Örnek: {"h": 354800.0, "s": 1507.0}
        # Motor çözdükten sonra hesaplanan değerler buraya yazılır.
        self.cozulmus_durum = None      # State nesnesi, çözümden sonra dolar
        self.yayilim_girdileri: dict = {}
        self.orta_nokta_widget = None
        self.rota_noktalari = []
        self.rota_widgetlari = []
        self.durum_kutusu_widget = None
        self.initial_direction = None

    def kaynak_konum(self):
        return self.kaynak_widget.port_gercek_konum(self.kaynak_port)

    def hedef_konum(self):
        return self.hedef_widget.port_gercek_konum(self.hedef_port)

    def orta_konum(self):
        x1, y1 = self.kaynak_konum()
        x2, y2 = self.hedef_konum()
        noktalar = [(x1, y1)] + self.rota() + [(x2, y2)]
        en_uzun = None
        max_uzunluk = -1.0
        for (xa, ya), (xb, yb) in zip(noktalar, noktalar[1:]):
            seg_uzunluk = math.hypot(xb - xa, yb - ya)
            if seg_uzunluk > max_uzunluk:
                max_uzunluk = seg_uzunluk
                en_uzun = (xa, ya, xb, yb)
        if en_uzun is None:
            return ((x1 + x2) / 2, (y1 + y2) / 2)
        xa, ya, xb, yb = en_uzun
        return ((xa + xb) / 2, (ya + yb) / 2)

    def varsayilan_rota(self):
        x1, y1 = self.kaynak_konum()
        x2, y2 = self.hedef_konum()
        if x1 == x2 or y1 == y2:
            return []
        if abs(x2 - x1) >= abs(y2 - y1):
            return [(x2, y1)]
        return [(x1, y2)]

    def rota(self):
        return self.rota_noktalari


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 3: UYGULAMA DURUMU
# ─────────────────────────────────────────────────────────────────────────────
class UygulamaDurumu:
    """Uygulama durumu ve kullanıcı etkileşimlerini yöneten ana sınıf."""
    def __init__(self):
        self.page               = None
        self.cizim_alani        = None
        self.baglanti_canvas    = None
        self.rota_yakalayici    = None
        self.sag_panel_icerik   = None
        self.durum_metni        = None
        self.akiskan: str       = "CarbonDioxide"
        self._akiskan_dd_ref = None

        self.bilesenler: list   = []
        self.baglantilar: list  = []
        self.bekleyen_port      = None  # (BilesenWidget, port_dict)
        self.gecici_rota        = []
        self.gecici_mouse       = None
        self.bekleyen_initial_direction = None
        self.sayac: dict        = {}
        self.durum_sayac        = 0
        self._aktif_dlg         = None

    # ── İsimlendirme ──────────────────────────────────────────────────────
    def yeni_isim(self, tip: str) -> str:
        self.sayac[tip] = self.sayac.get(tip, 0) + 1
        kisalt = {
            "Turbine": "T", "Compressor": "C", "Recuperator": "REC",
            "Heat Exchanger": "HX", "Splitter": "SPL", "Mixer": "MIX",
        }
        return f"{kisalt.get(tip, tip[:3])}{self.sayac[tip]}"

    def yeni_durum_etiketi(self) -> str:
        self.durum_sayac += 1
        return f"S{self.durum_sayac}"

    def durum_sayacini_guncelle(self):
        en_buyuk = 0
        for b in self.baglantilar:
            if b.etiket and b.etiket.upper().startswith("S"):
                try:
                    en_buyuk = max(en_buyuk, int(b.etiket[1:]))
                except ValueError:
                    pass
        self.durum_sayac = en_buyuk

    # ── Bileşen Yönetimi ──────────────────────────────────────────────────
    def bilesen_ekle(self, tip: str):
        isim = self.yeni_isim(tip)
        widget = BilesenWidget(tip, isim, self)
        n = len(self.bilesenler)
        widget.left = 110 + (n % 6) * 140
        widget.top  = 90  + (n // 6) * 130
        self.bilesenler.append(widget)
        self.cizim_alani.controls.append(widget)
        self.cizim_alani.update()
        self._durum(f"+ {isim} eklendi")

    def bilesen_sil(self, widget):
        ilgili = [b for b in self.baglantilar
                  if b.kaynak_widget is widget or b.hedef_widget is widget]
        for b in ilgili:
            self._orta_nokta_sil(b)
        self.baglantilar = [b for b in self.baglantilar if b not in ilgili]
        if widget in self.cizim_alani.controls:
            self.cizim_alani.controls.remove(widget)
        if widget in self.bilesenler:
            self.bilesenler.remove(widget)
        self._ciz_baglantilar()
        self.cizim_alani.update()
        self._durum(f"{widget.isim} silindi")

    def _orta_nokta_sil(self, b):
        if b.orta_nokta_widget and b.orta_nokta_widget in self.cizim_alani.controls:
            self.cizim_alani.controls.remove(b.orta_nokta_widget)
        for w in getattr(b, "rota_widgetlari", []):
            if w in self.cizim_alani.controls:
                self.cizim_alani.controls.remove(w)
        b.rota_widgetlari = []
        if b.durum_kutusu_widget and b.durum_kutusu_widget in self.cizim_alani.controls:
            self.cizim_alani.controls.remove(b.durum_kutusu_widget)
        b.durum_kutusu_widget = None

    def _baglanti_widgetleri_ekle(self, b):
        b.rota_widgetlari = []
        for i in range(len(b.rota_noktalari)):
            nokta = RotaNoktasi(b, self, i)
            b.rota_widgetlari.append(nokta)
            self.cizim_alani.controls.append(nokta)
        b.orta_nokta_widget = BaglantiBolumu(b, self)
        self.cizim_alani.controls.append(b.orta_nokta_widget)

    def durum_penceresi_ac(self, b):
        if b.durum_kutusu_widget and b.durum_kutusu_widget in self.cizim_alani.controls:
            self.cizim_alani.controls.remove(b.durum_kutusu_widget)
            b.durum_kutusu_widget = None
            self.cizim_alani.update()
            return
        if b.durum_kutusu_widget is None:
            b.durum_kutusu_widget = DurumKutusu(b, self)
        self.cizim_alani.controls.append(b.durum_kutusu_widget)
        self.cizim_alani.update()

    def durum_penceresi_kapat(self, b):
        if b.durum_kutusu_widget and b.durum_kutusu_widget in self.cizim_alani.controls:
            self.cizim_alani.controls.remove(b.durum_kutusu_widget)
            b.durum_kutusu_widget = None
            self.cizim_alani.update()

    def rota_noktasi_ekle(self, b, index=None):
        if not b.rota_noktalari:
            b.rota_noktalari = b.varsayilan_rota()
        if index is None:
            index = len(b.rota_noktalari) - 1
        x, y = b.rota_noktalari[index]
        yeni = (x + 55, y)
        b.rota_noktalari.insert(index + 1, yeni)
        self._orta_nokta_sil(b)
        self._baglanti_widgetleri_ekle(b)
        self._ciz_baglantilar()
        self.cizim_alani.update()
        self._durum(f"{b.etiket} icin yeni kirik nokta eklendi")

    def rota_widgetlarini_guncelle(self, b):
        for w in getattr(b, "rota_widgetlari", []):
            w.konumu_guncelle()
        if b.orta_nokta_widget and b.orta_nokta_widget in self.cizim_alani.controls:
            b.orta_nokta_widget.konumu_guncelle()
        if b.durum_kutusu_widget and b.durum_kutusu_widget in self.cizim_alani.controls:
            b.durum_kutusu_widget.verileri_guncelle()

    def _event_xy(self, e):
        for x_ad, y_ad in (
            ("local_x", "local_y"),
            ("x", "y"),
            ("global_x", "global_y"),
        ):
            if hasattr(e, x_ad) and hasattr(e, y_ad):
                x, y = getattr(e, x_ad), getattr(e, y_ad)
                if x is not None and y is not None:
                    return float(x), float(y)
        if hasattr(e, "local_position"):
            p = e.local_position
            if hasattr(p, "x") and hasattr(p, "y"):
                return float(p.x), float(p.y)
            if isinstance(p, (tuple, list)) and len(p) >= 2:
                return float(p[0]), float(p[1])
        return None

    def _infer_direction_from_delta(self, src_xy, dest_xy):
        dx = dest_xy[0] - src_xy[0]
        dy = dest_xy[1] - src_xy[1]
        if abs(dy) >= abs(dx):
            return "UP" if dy < 0 else "DOWN"
        return "RIGHT" if dx > 0 else "LEFT"

    def _son_rota_noktasi(self):
        if self.gecici_rota:
            return self.gecici_rota[-1]
        if self.bekleyen_port:
            w, p = self.bekleyen_port
            return w.port_gercek_konum(p)
        return None

    def _eksen_kilitli_nokta(self, x, y):
        son = self._son_rota_noktasi()
        if not son:
            return (x, y)
        sx, sy = son
        if abs(x - sx) >= abs(y - sy):
            return (x, sy)
        return (sx, y)

    def gecici_rota_hareket(self, e):
        if not self.bekleyen_port:
            return
        xy = self._event_xy(e)
        if xy is None:
            return
        # determine last fixed point
        son = self._son_rota_noktasi()
        if not son:
            return
        # determine next segment orientation
        if self.bekleyen_initial_direction is None and not self.gecici_rota:
            # infer from mouse relative to source port
            src_w, src_p = self.bekleyen_port
            src_xy = src_w.port_gercek_konum(src_p)
            dir_guess = self._infer_direction_from_delta(src_xy, xy)
            orient_vertical = dir_guess in ("UP", "DOWN")
        else:
            # if initial known or there are waypoints, compute parity
            if self.bekleyen_initial_direction is None:
                dir0 = self._infer_direction_from_delta(self._son_rota_noktasi(), xy)
            else:
                dir0 = self.bekleyen_initial_direction
            # determine number of fixed segments so far
            seg_index = len(self.gecici_rota) + 1
            # seg_index orientation: if initial vertical then odd segments vertical
            initial_vert = dir0 in ("UP", "DOWN")
            orient_vertical = initial_vert if (seg_index % 2 == 1) else not initial_vert

        # compute preview bend
        lx, ly = son
        mx, my = xy
        if orient_vertical:
            bend = (lx, my)
        else:
            bend = (mx, ly)
        self.gecici_mouse = bend
        self._ciz_baglantilar()

    def gecici_rota_tikla(self, e):
        if not self.bekleyen_port:
            return
        xy = self._event_xy(e)
        if xy is None:
            return
        src_w, src_p = self.bekleyen_port
        last = self._son_rota_noktasi()
        if last is None:
            return
        # determine orientation for next segment
        if self.bekleyen_initial_direction is None and not self.gecici_rota:
            dir_guess = self._infer_direction_from_delta(src_w.port_gercek_konum(src_p), xy)
        else:
            dir_guess = self.bekleyen_initial_direction or self._infer_direction_from_delta(last, xy)
        seg_index = len(self.gecici_rota) + 1
        initial_vert = dir_guess in ("UP", "DOWN")
        orient_vertical = initial_vert if (seg_index % 2 == 1) else not initial_vert

        lx, ly = last
        cx, cy = xy
        if orient_vertical:
            new_wp = (lx, cy)
        else:
            new_wp = (cx, ly)

        # set initial_direction if first waypoint
        if not self.gecici_rota:
            # infer signed direction relative to source port
            src_xy = src_w.port_gercek_konum(src_p)
            if abs(cy - src_xy[1]) >= abs(cx - src_xy[0]):
                self.bekleyen_initial_direction = "UP" if cy < src_xy[1] else "DOWN"
            else:
                self.bekleyen_initial_direction = "LEFT" if cx < src_xy[0] else "RIGHT"

        if not self.gecici_rota or self.gecici_rota[-1] != new_wp:
            self.gecici_rota.append(new_wp)
        self.gecici_mouse = new_wp
        self._ciz_baglantilar()
        self._durum("Kirik nokta eklendi; fareyi yeni yone goturup devam edin")

    def tumu_temizle(self):
        self.baglantilar.clear()
        self.bilesenler.clear()
        self.bekleyen_port = None
        self.gecici_rota = []
        self.gecici_mouse = None
        self.sayac.clear()
        self.durum_sayac = 0
        self.cizim_alani.controls = [self.baglanti_canvas, self.rota_yakalayici]
        self._ciz_baglantilar()
        self.cizim_alani.update()
        self._sag_panel_sifirla()
        self._durum("Tuval temizlendi")

    # ── Port ve Bağlantı ──────────────────────────────────────────────────
    def port_tikla(self, widget, port_cfg: dict):
        if self.bekleyen_port is None:
            self.bekleyen_port = (widget, port_cfg)
            self.gecici_rota = []
            self.gecici_mouse = widget.port_gercek_konum(port_cfg)
            self._ciz_baglantilar()
            self._durum(
                f"[{widget.isim}] {port_cfg['ad']} secildi — hedef porta tiklayin"
            )
            return

        src_w, src_p = self.bekleyen_port
        if src_w is widget and src_p is port_cfg:
            self.bekleyen_port = None
            self.gecici_rota = []
            self.gecici_mouse = None
            self.bekleyen_initial_direction = None
            self._ciz_baglantilar()
            self._durum("Baglanti iptal edildi")
            return

        for b in self.baglantilar:
            if ((b.kaynak_widget is src_w  and b.kaynak_port is src_p) or
                (b.hedef_widget  is src_w  and b.hedef_port  is src_p) or
                (b.kaynak_widget is widget and b.kaynak_port is port_cfg) or
                (b.hedef_widget  is widget and b.hedef_port  is port_cfg)):
                self._durum("Bu port zaten bagli!")
                return

        b = Baglanti(src_w, src_p, widget, port_cfg, self.yeni_durum_etiketi())
        if self.gecici_rota:
            b.rota_noktalari = list(self.gecici_rota)
        else:
            src_xy = src_w.port_gercek_konum(src_p)
            dst_xy = widget.port_gercek_konum(port_cfg)
            if self.gecici_mouse and self.gecici_mouse not in (src_xy, dst_xy):
                b.rota_noktalari = [self.gecici_mouse]
            elif src_xy[0] != dst_xy[0] and src_xy[1] != dst_xy[1]:
                if abs(dst_xy[0] - src_xy[0]) >= abs(dst_xy[1] - src_xy[1]):
                    b.rota_noktalari = [(dst_xy[0], src_xy[1])]
                else:
                    b.rota_noktalari = [(src_xy[0], dst_xy[1])]
            else:
                b.rota_noktalari = []
        self.baglantilar.append(b)
        self._baglanti_widgetleri_ekle(b)
        # finalize initial_direction for the connection
        if self.bekleyen_initial_direction is not None:
            b.initial_direction = self.bekleyen_initial_direction
        else:
            # infer from first waypoint or directly from src->dst
            src_xy = src_w.port_gercek_konum(src_p)
            dst_xy = widget.port_gercek_konum(port_cfg)
            if b.rota_noktalari:
                first = b.rota_noktalari[0]
                d = self._infer_direction_from_delta(src_xy, first)
            else:
                d = self._infer_direction_from_delta(src_xy, dst_xy)
            b.initial_direction = d
        self.bekleyen_initial_direction = None
        self.bekleyen_port = None
        self.gecici_rota = []
        self.gecici_mouse = None
        self._ciz_baglantilar()
        self.cizim_alani.update()
        self._durum(
            f"Baglandi: [{src_w.isim}] {src_p['ad']} -> [{widget.isim}] {port_cfg['ad']}"
        )

    def baglantilari_yenile(self):
        """Bileşen hareket ettiğinde çizgileri ve orta noktaları güncelle."""
        # sync first/last waypoint to moving ports per Manhattan rules
        for b in self.baglantilar:
            try:
                src_xy = b.kaynak_konum()
                dst_xy = b.hedef_konum()
                # update first waypoint follow source according to initial_direction
                if b.rota_noktalari:
                    # first waypoint
                    x0, y0 = b.rota_noktalari[0]
                    if b.initial_direction in ("UP", "DOWN"):
                        # x should follow source
                        if x0 != src_xy[0]:
                            b.rota_noktalari[0] = (src_xy[0], y0)
                    elif b.initial_direction in ("LEFT", "RIGHT"):
                        if y0 != src_xy[1]:
                            b.rota_noktalari[0] = (x0, src_xy[1])
                    # last waypoint follow destination for last segment orientation
                    last = b.rota_noktalari[-1]
                    if len(b.rota_noktalari) >= 1:
                        prev = b.rota_noktalari[-2] if len(b.rota_noktalari) >= 2 else src_xy
                        # determine orientation of last segment prev -> last
                        if prev[0] == last[0]:
                            # vertical segment -> last.x fixed, last.y should follow dst if needed
                            if last[0] != dst_xy[0]:
                                # keep x same but allow y to follow dst
                                b.rota_noktalari[-1] = (last[0], dst_xy[1])
                        elif prev[1] == last[1]:
                            # horizontal segment
                            if last[1] != dst_xy[1]:
                                b.rota_noktalari[-1] = (dst_xy[0], last[1])
                else:
                    # no waypoints: nothing to sync except segments drawn directly
                    pass
            except Exception:
                pass
        self._ciz_baglantilar()
        for b in self.baglantilar:
            self.rota_widgetlarini_guncelle(b)

    def _ciz_baglantilar(self):
        shapes = []
        for b in self.baglantilar:
            src = b.kaynak_konum()
            dst = b.hedef_konum()
            pts = [src] + list(b.rota() or []) + [dst]
            renk = ft.Colors.GREEN_300 if b.cozulmus_durum else ft.Colors.CYAN_400
            paint = ft.Paint(
                stroke_width=2.5,
                color=renk,
                style=ft.PaintingStyle.STROKE,
                stroke_cap=ft.StrokeCap.ROUND,
                stroke_join=ft.StrokeJoin.ROUND,
            )
            # draw each Manhattan segment (must be axis-aligned)
            longest_len = -1.0
            longest_seg = None
            for (x1, y1), (x2, y2) in zip(pts, pts[1:]):
                # straight line between points (should be axis-aligned)
                shapes.append(cv.Path(elements=[cv.Path.MoveTo(x1, y1), cv.Path.LineTo(x2, y2)], paint=paint))
                seg_len = math.hypot(x2 - x1, y2 - y1)
                if seg_len > longest_len:
                    longest_len = seg_len
                    longest_seg = (x1, y1, x2, y2)
                # arrow at 60% of segment
                ax = x1 + 0.6 * (x2 - x1)
                ay = y1 + 0.6 * (y2 - y1)
                if x1 == x2:
                    # vertical
                    dir_down = y2 > y1
                    if dir_down:
                        wing1 = (ax - 6, ay - 6)
                        wing2 = (ax + 6, ay - 6)
                    else:
                        wing1 = (ax - 6, ay + 6)
                        wing2 = (ax + 6, ay + 6)
                else:
                    # horizontal
                    dir_right = x2 > x1
                    if dir_right:
                        wing1 = (ax - 6, ay - 6)
                        wing2 = (ax - 6, ay + 6)
                    else:
                        wing1 = (ax + 6, ay - 6)
                        wing2 = (ax + 6, ay + 6)
                shapes.append(cv.Path(elements=[
                    cv.Path.MoveTo(ax, ay), cv.Path.LineTo(*wing1),
                    cv.Path.MoveTo(ax, ay), cv.Path.LineTo(*wing2)
                ], paint=paint))
            # store longest segment for possible state placement (BaglantiBolumu widget uses orta_konum)
        # preview drawing during active connection (rubber-band)
        if self.bekleyen_port:
            src_w, src_p = self.bekleyen_port
            src = src_w.port_gercek_konum(src_p)
            preview_pts = [src] + list(self.gecici_rota) + ([self.gecici_mouse] if self.gecici_mouse else [])
            preview_paint_fixed = ft.Paint(stroke_width=2.5, color=ft.Colors.CYAN_200,
                                           style=ft.PaintingStyle.STROKE)
            preview_paint_preview = ft.Paint(stroke_width=2.5, color=ft.Colors.AMBER_300,
                                             style=ft.PaintingStyle.STROKE)
            # draw fixed segments (from src through existing waypoints)
            for (x1, y1), (x2, y2) in zip(preview_pts, preview_pts[1:]):
                # if this is last segment and ends at gecici_mouse, draw with preview paint
                if (x2, y2) == (self.gecici_mouse):
                    shapes.append(cv.Path(elements=[cv.Path.MoveTo(x1, y1), cv.Path.LineTo(x2, y2)], paint=preview_paint_preview))
                else:
                    shapes.append(cv.Path(elements=[cv.Path.MoveTo(x1, y1), cv.Path.LineTo(x2, y2)], paint=preview_paint_fixed))
        self.baglanti_canvas.shapes = shapes
        self.baglanti_canvas.update()

    # ── Diyaloglar ────────────────────────────────────────────────────────
    def _dlg_ac(self, dlg):
        self._aktif_dlg = dlg
        self.page.show_dialog(dlg)

    def _dlg_kapat(self, e=None):
        if self._aktif_dlg:
            self.page.pop_dialog()
            self._aktif_dlg = None

    def bilesen_menu_ac(self, widget):
        dlg = ft.AlertDialog(
            title=ft.Text(widget.isim, size=14, weight="bold", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE_GREY_800,
            actions=[
                ft.TextButton(
                    "Ozellikler",
                    on_click=lambda e: [self._dlg_kapat(), self.ozellikleri_goster(widget)],
                ),
                ft.TextButton(
                    "90 Derece Dondur",
                    on_click=lambda e: [self._dlg_kapat(), self._dondur(widget)],
                ),
                ft.TextButton(
                    "Yansit (Flip)",
                    on_click=lambda e: [self._dlg_kapat(), self._yansit(widget)],
                ),
                ft.TextButton(
                    "Sil",
                    on_click=lambda e: [self._dlg_kapat(), self.bilesen_sil(widget)],
                    style=ft.ButtonStyle(color=ft.Colors.RED_400),
                ),
                ft.TextButton("Iptal", on_click=self._dlg_kapat),
            ],
        )
        self._dlg_ac(dlg)

    def _dondur(self, widget):
        widget._aci_adet = (widget._aci_adet + 1) % 4
        widget._aci = widget._aci_adet * math.pi / 2
        widget.rotate = ft.Rotate(angle=widget._aci, alignment=ft.Alignment(0, 0))
        widget.update()
        self.baglantilari_yenile()

    def _yansit(self, widget):
        widget._yansima *= -1
        # Tum widget'i aynala (sekil icin)
        widget.scale = ft.Scale(
            scale_x=widget._yansima,
            scale_y=1,
            alignment=ft.Alignment(0, 0),
        )
        # Metin containerlarini ters yonde aynala (metin iki kere aynalaninca duz kalir)
        for cont in getattr(widget, "_metin_containerlar", []):
            cont.scale = ft.Scale(
                scale_x=widget._yansima,
                scale_y=1,
                alignment=ft.Alignment(0, 0),
            )
        widget.update()

    def ozellikleri_goster(self, widget):
        alanlar: dict = {}
        girdiler = []

        isim_alan = ft.TextField(
            label="Bilesen Adi",
            value=widget.isim,
            dense=True,
            border_color=ft.Colors.BLUE_GREY_500,
            focused_border_color=ft.Colors.CYAN_400,
            text_style=ft.TextStyle(color=ft.Colors.WHITE),
            label_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_300),
        )
        girdiler.append(isim_alan)

        if "verim" in widget.ayarlar:
            f = ft.TextField(
                label="Izantropik Verim (0-1)",
                value=str(widget.ayarlar["verim"]),
                dense=True,
                border_color=ft.Colors.BLUE_GREY_500,
                focused_border_color=ft.Colors.CYAN_400,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
                label_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_300),
            )
            alanlar["verim"] = f
            girdiler.append(f)

        if "etkinlik" in widget.ayarlar:
            f = ft.TextField(
                label="Etkinlik / Effectiveness (0-1)",
                value=str(widget.ayarlar["etkinlik"]),
                dense=True,
                border_color=ft.Colors.BLUE_GREY_500,
                focused_border_color=ft.Colors.CYAN_400,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
                label_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_300),
            )
            alanlar["etkinlik"] = f
            girdiler.append(f)

        if "oran_1" in widget.ayarlar:
            f1 = ft.TextField(
                label="Cikis 1 Orani",
                value=str(widget.ayarlar["oran_1"]),
                dense=True,
                border_color=ft.Colors.BLUE_GREY_500,
                focused_border_color=ft.Colors.CYAN_400,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
                label_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_300),
            )
            f2 = ft.TextField(
                label="Cikis 2 Orani",
                value=str(widget.ayarlar["oran_2"]),
                dense=True,
                border_color=ft.Colors.BLUE_GREY_500,
                focused_border_color=ft.Colors.CYAN_400,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
                label_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_300),
            )
            alanlar["oran_1"] = f1
            alanlar["oran_2"] = f2
            girdiler.extend([f1, f2])

        def kaydet(e):
            widget.isim = isim_alan.value.strip() or widget.isim
            for k, f in alanlar.items():
                try:
                    widget.ayarlar[k] = float(f.value)
                except ValueError:
                    pass
            self._dlg_kapat()
            self._durum(f"{widget.isim} guncellendi")

        dlg = ft.AlertDialog(
            title=ft.Text(f"{widget.tip} Ozellikleri", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE_GREY_800,
            content=ft.Container(
                width=300,
                content=ft.Column(controls=girdiler, spacing=10),
            ),
            actions=[
                ft.TextButton(
                    "Kaydet",
                    on_click=kaydet,
                    style=ft.ButtonStyle(color=ft.Colors.CYAN_400),
                ),
                ft.TextButton("Iptal", on_click=self._dlg_kapat),
            ],
        )
        self._dlg_ac(dlg)

    def _sinir_sartlarini_coz(self, sartlar: dict):
        if not MOTOR_HAZIR:
            return None
        s = State(self.akiskan)
        for k in ("T", "P", "h", "s", "m_dot"):
            if k in sartlar:
                setattr(s, k, sartlar[k])
        s.update()
        return s

    def _sicaklik_gosterim_c(self, t_kelvin):
        if t_kelvin is None:
            return ""
        return t_kelvin - 273.15

    def _sicaklik_kayit_k(self, t_value):
        if t_value is None:
            return None
        # GUI kullanicisi sicakligi C girer; eski kayitlarda 32/50 gibi
        # degerler varsa onlari da C kabul edip core tarafina K gonderiyoruz.
        return t_value + 273.15 if t_value < 200 else t_value

    def _filtreli_sinir_sartlari(self, sartlar: dict):
        temiz = {}
        for k in ("T", "P", "h", "s", "m_dot"):
            if k in sartlar and sartlar[k] is not None:
                temiz[k] = self._sicaklik_kayit_k(sartlar[k]) if k == "T" else sartlar[k]
        return temiz

    def _yayilan_parametreler(self, b) -> dict:
        """
        Baglanti b icin, kaynak bilesenden otomatik yayilan
        parametreleri hesapla.
        """
        yayilan = {}
        src = b.kaynak_widget
        tip = src.tip

        # Kaynak bilesene giren baglantiyi bul
        giris_b = next((x for x in self.baglantilar if x.hedef_widget is src), None)
        if giris_b is None:
            return yayilan

        # Oncelik sirasi: cozulmus_durum > kullanici_girdileri
        #                 > yayilim_girdileri > sinir_sartlari
        def deger_al(alan):
            s = giris_b.cozulmus_durum
            if s and getattr(s, alan, None) is not None:
                return getattr(s, alan)
            return (giris_b.kullanici_girdileri.get(alan)
                    or giris_b.yayilim_girdileri.get(alan)
                    or giris_b.sinir_sartlari.get(alan))

        # KURAL 1: m_dot her bilesende korunur (Splitter/Mixer disinda)
        if tip not in ("Splitter", "Mixer"):
            m = deger_al("m_dot")
            if m is not None:
                yayilan["m_dot"] = m

        # KURAL 2: P sadece izobarik sayilan bilesenlerde korunur
        if tip in ("Heat Exchanger", "Recuperator"):
            p = deger_al("P")
            if p is not None:
                yayilan["P"] = p

        return yayilan

    def sinir_sartlari_goster(self, b):
        # compute propagated inputs first
        b.yayilim_girdileri = self._yayilan_parametreler(b)
        alanlar: dict = {}
        # termodinamik alanlar sayaci (T,P,h,s) kullanici+yayilim
        termodinamik_bilinen = sum(1 for a in ("T", "P", "h", "s") if (a in b.kullanici_girdileri or a in b.yayilim_girdileri))
        n = termodinamik_bilinen
        if n >= 2:
            sayac_renk = "#22C55E"
            sayac_ikon = "✓ Çözülebilir"
        elif n == 1:
            sayac_renk = "#F59E0B"
            sayac_ikon = "⚠ Eksik (1 parametre daha gerekli)"
        else:
            sayac_renk = "#6B7280"
            sayac_ikon = "Veri yok"

        girdiler = [
            ft.Text(
                b.etiket or "Durum",
                size=16,
                weight="bold",
                color=ft.Colors.CYAN_300,
            ),
            ft.Text(
                f"{b.kaynak_widget.isim} [{b.kaynak_port['ad']}]  ->  "
                f"{b.hedef_widget.isim} [{b.hedef_port['ad']}]",
                size=11,
                color=ft.Colors.BLUE_GREY_300,
            ),
            ft.Text(
                f"{n} / 2 parametre girildi — {sayac_ikon}",
                size=11,
                color=sayac_renk,
            ),
            ft.Divider(color=ft.Colors.BLUE_GREY_600),
        ]

        tanim = [
            ("T",     "Sıcaklık T [C]",     "UNKNOWN"),
            ("P",     "Basınç P [Pa]",      "UNKNOWN"),
            ("h",     "Entalpi h [J/kg]",   "UNKNOWN"),
            ("s",     "Entropi s [J/kgK]",  "UNKNOWN"),
            ("m_dot", "Kütlesel Debi [kg/s]", "UNKNOWN"),
        ]

        for k, label, hint in tanim:
            kullanici_var = k in b.kullanici_girdileri
            yayilim_var = k in b.yayilim_girdileri and not kullanici_var
            motor_var = k in b.motor_sonuclari and not kullanici_var and not yayilim_var

            if kullanici_var:
                if k == "T":
                    deger = self._sicaklik_gosterim_c(b.kullanici_girdileri[k])
                else:
                    deger = b.kullanici_girdileri[k]
                value = f"{deger:.2f}" if deger is not None else ""
                border_color = "#22C55E"
                label_color = "#22C55E"
                read_only = False
            elif yayilim_var:
                if k == "T":
                    deger = self._sicaklik_gosterim_c(b.yayilim_girdileri[k])
                else:
                    deger = b.yayilim_girdileri[k]
                value = f"(yayilim) {deger:.2f}"
                border_color = "#A855F7"
                label_color = "#A855F7"
                read_only = True
            elif motor_var:
                if k == "T":
                    deger = self._sicaklik_gosterim_c(b.motor_sonuclari[k])
                else:
                    deger = b.motor_sonuclari[k]
                value = f"(motor) {deger:.2f}"
                border_color = "#3B82F6"
                label_color = "#3B82F6"
                read_only = True
            else:
                value = ""
                border_color = ft.Colors.BLUE_GREY_500
                label_color = ft.Colors.BLUE_GREY_300
                read_only = False

            f = ft.TextField(
                label=label,
                value=value,
                hint_text=hint,
                dense=True,
                read_only=read_only,
                border_color=border_color,
                focused_border_color=border_color,
                text_style=ft.TextStyle(color=ft.Colors.WHITE),
                label_style=ft.TextStyle(color=label_color),
                hint_style=ft.TextStyle(color=ft.Colors.BLUE_GREY_500, size=10),
            )
            alanlar[k] = f
            girdiler.append(f)

        # Onizleme icin kullanici + yayilim degerlerini birlestir (kullanici baskindir)
        merged = dict(b.yayilim_girdileri)
        merged.update(b.kullanici_girdileri)
        onizleme = self._sinir_sartlarini_coz(self._filtreli_sinir_sartlari(merged))
        if onizleme and (onizleme.h is not None or onizleme.s is not None):
            h_text = f"{onizleme.h / 1000:.3f} kJ/kg" if onizleme.h is not None else "-"
            s_text = f"{onizleme.s / 1000:.5f} kJ/kgK" if onizleme.s is not None else "-"
            girdiler.extend([
                ft.Divider(color=ft.Colors.BLUE_GREY_600),
                ft.Text("State.update() ile otomatik hesaplanan:", size=10, color=ft.Colors.BLUE_GREY_300),
                ft.Text(f"h = {h_text}", size=11, color=ft.Colors.CYAN_200),
                ft.Text(f"s = {s_text}", size=11, color=ft.Colors.CYAN_200),
            ])
        else:
            girdiler.extend([
                ft.Divider(color=ft.Colors.BLUE_GREY_600),
                ft.Text(
                    "h ve s otomatik gelir; hesap icin genelde T + P gerekir.",
                    size=10,
                    color=ft.Colors.BLUE_GREY_400,
                ),
            ])

        def kaydet(e):
            yeni_kullanici = {}
            for k, f in alanlar.items():
                if f.value.strip() and not f.read_only:
                    try:
                        deger = float(f.value)
                        if k == "T":
                            deger = self._sicaklik_kayit_k(deger)
                        yeni_kullanici[k] = deger
                    except ValueError:
                        pass
            b.kullanici_girdileri = yeni_kullanici
            b.sinir_sartlari = dict(yeni_kullanici)
            if b.durum_kutusu_widget and b.durum_kutusu_widget in self.cizim_alani.controls:
                b.durum_kutusu_widget.verileri_guncelle()
            self._dlg_kapat()
            self._durum(f"{b.etiket or 'Durum'} sinir sartlari guncellendi")

        dlg = ft.AlertDialog(
            title=ft.Text("Akis Sinir Sartlari", color=ft.Colors.WHITE),
            bgcolor=ft.Colors.BLUE_GREY_800,
            content=ft.Container(
                width=320,
                content=ft.Column(controls=girdiler, spacing=10),
            ),
            actions=[
                ft.TextButton(
                    "Kaydet",
                    on_click=kaydet,
                    style=ft.ButtonStyle(color=ft.Colors.CYAN_400),
                ),
                ft.TextButton("Iptal", on_click=self._dlg_kapat),
            ],
        )
        self._dlg_ac(dlg)

    # ── Şablon Yükleme ────────────────────────────────────────────────────
    def sablon_yukle(self, isim: str):
        veri = SABLONLAR.get(isim)
        if not veri:
            return
        self.tumu_temizle()
        self.akiskan = veri.get("akiskan", "CarbonDioxide")
        # update dropdown widget if main stored a reference
        if hasattr(self, "_akiskan_dd_ref") and self._akiskan_dd_ref:
            try:
                self._akiskan_dd_ref.value = self.akiskan
                self._akiskan_dd_ref.update()
            except Exception:
                pass
        isim_map = {}
        for bd in veri["bilesenler"]:
            w = BilesenWidget(bd["tip"], bd["isim"], self)
            w.left    = bd["left"]
            w.top     = bd["top"]
            w.ayarlar = dict(bd.get("ayarlar", {}))
            self.bilesenler.append(w)
            self.cizim_alani.controls.append(w)
            isim_map[bd["isim"]] = w
        for bd in veri["baglantilar"]:
            src_w = isim_map.get(bd["kaynak_isim"])
            dst_w = isim_map.get(bd["hedef_isim"])
            if not src_w or not dst_w:
                continue
            src_p = port_bul(src_w.tip, bd["kaynak_port"])
            dst_p = port_bul(dst_w.tip, bd["hedef_port"])
            if not src_p or not dst_p:
                continue
            b = Baglanti(src_w, src_p, dst_w, dst_p, bd.get("etiket"))
            b.kullanici_girdileri = self._filtreli_sinir_sartlari(dict(bd.get("kullanici_girdileri", bd.get("sinir_sartlari", {}))))
            b.sinir_sartlari = dict(b.kullanici_girdileri)
            b.yayilim_girdileri = self._filtreli_sinir_sartlari(dict(bd.get("yayilim_girdileri", {})))
            b.motor_sonuclari = self._filtreli_sinir_sartlari(dict(bd.get("motor_sonuclari", {})))
            if bd.get("rota"):
                b.rota_noktalari = [tuple(p) for p in bd["rota"]]
            self.baglantilar.append(b)
            self._baglanti_widgetleri_ekle(b)
        self.durum_sayacini_guncelle()
        self._ciz_baglantilar()
        self.cizim_alani.update()
        self._durum(f"Sablon yuklendi: {isim}")

    # ── Kaydet / Yukle ────────────────────────────────────────────────────
    def devreyi_kaydet(self):
        # Dosya tabanlı devre kaydetme/yükleme kaldırıldı.
        raise NotImplementedError("devreyi_kaydet removed")

    def devreyi_yukle(self):
        # `devre.json` artık kullanılmıyor; bu uygulama doğrudan GUI üzerinden çalışır.
        raise NotImplementedError("devreyi_yukle removed")

    # ── Verim Hesaplama ───────────────────────────────────────────────────
    def _verim_hesapla(self):
        W_net = 0.0
        Q_in  = 0.0
        Q_out = 0.0

        for widget in self.bilesenler:
            tip = widget.tip
            try:
                if tip in ("Turbine", "Compressor"):
                    giris_b = next(
                        (b for b in self.baglantilar
                         if b.hedef_widget is widget), None
                    )
                    cikis_b = next(
                        (b for b in self.baglantilar
                         if b.kaynak_widget is widget), None
                    )
                    if giris_b and cikis_b:
                        si = giris_b.cozulmus_durum
                        so = cikis_b.cozulmus_durum
                        if (si and so
                                and si.h is not None
                                and so.h is not None
                                and si.m_dot is not None):
                            dW = si.m_dot * (si.h - so.h)
                            W_net += dW

                elif tip == "Heat Exchanger":
                    giris_b = next(
                        (b for b in self.baglantilar
                         if b.hedef_widget is widget), None
                    )
                    cikis_b = next(
                        (b for b in self.baglantilar
                         if b.kaynak_widget is widget), None
                    )
                    if giris_b and cikis_b:
                        si = giris_b.cozulmus_durum
                        so = cikis_b.cozulmus_durum
                        if (si and so
                                and si.h is not None
                                and so.h is not None
                                and si.m_dot is not None):
                            dQ = si.m_dot * (so.h - si.h)
                            if dQ > 0:
                                Q_in  += dQ
                            else:
                                Q_out += abs(dQ)

            except Exception:
                pass

        eta = (W_net / Q_in * 100) if Q_in > 1 else None
        return W_net, Q_in, Q_out, eta

    # ── Çözücü ────────────────────────────────────────────────────────────
    def coz(self):
        if not MOTOR_HAZIR:
            self._durum("Hata: Motor yuklenemedi — CoolProp kurulu mu?")
            return
        if not self.bilesenler:
            self._durum("Tuval bos! Once bilesen ekleyin.")
            return
        if not self.baglantilar:
            self._durum("Baglanti yok! Portlari birbirine baglayin.")
            return

        try:
            self._durum("Cozum hesaplaniyor...")
            self.page.update()

            solver = CycleSolver()

            for b in self.baglantilar:
                # clear prior solution so failed solves don't leave stale data
                b.cozulmus_durum = None
                s = State(self.akiskan)
                b.sinir_sartlari = self._filtreli_sinir_sartlari(b.sinir_sartlari)
                for k, v in b.sinir_sartlari.items():
                    setattr(s, k, v)
                b.cozulmus_durum = s
                solver.add_state(s)

            port_map: dict = {}
            for b in self.baglantilar:
                port_map[(id(b.kaynak_widget), b.kaynak_port["ad"])] = b
                port_map[(id(b.hedef_widget),  b.hedef_port["ad"])]  = b

            for widget in self.bilesenler:
                tip, ayar = widget.tip, widget.ayarlar

                if tip == "Turbine":
                    obj = Turbine(widget.isim, ayar.get("verim", 0.92))
                elif tip == "Compressor":
                    obj = Compressor(widget.isim, ayar.get("verim", 0.89))
                elif tip == "Recuperator":
                    obj = Recuperator(widget.isim, ayar.get("etkinlik", 0.95))
                elif tip == "Heat Exchanger":
                    obj = SimpleHeatExchanger(widget.isim)
                elif tip == "Splitter":
                    obj = Splitter(
                        widget.isim,
                        [ayar.get("oran_1", 0.65), ayar.get("oran_2", 0.35)],
                    )
                elif tip == "Mixer":
                    obj = Mixer(widget.isim)
                else:
                    continue

                solver.add_component(obj)

                for p in BILESEN_CONFIGS[tip]["portlar"]:
                    key = (id(widget), p["ad"])
                    bcon = port_map.get(key)
                    state = bcon.cozulmus_durum if bcon is not None else None
                    if p["giris"]:
                        obj.add_inlet(state)
                    else:
                        obj.add_outlet(state)

            # Yayilim girdilerini hesapla (component-based propagation)
            for b in self.baglantilar:
                b.yayilim_girdileri = self._yayilan_parametreler(b)

            basarili = solver.solve(max_iterations=100)
            for b in self.baglantilar:
                b.sinir_sartlari = self._filtreli_sinir_sartlari(b.sinir_sartlari)
                b.kullanici_girdileri = dict(b.sinir_sartlari)
                s = b.cozulmus_durum
                if s is None:
                    continue
                b.motor_sonuclari = {}
                for alan in ("T", "P", "h", "s", "m_dot"):
                    if (alan not in b.kullanici_girdileri and alan not in b.yayilim_girdileri):
                        deger = getattr(s, alan, None)
                        if deger is not None:
                            b.motor_sonuclari[alan] = deger
            self._ciz_baglantilar()
            for b in self.baglantilar:
                if b.durum_kutusu_widget:
                    b.durum_kutusu_widget.verileri_guncelle()
            W_net, Q_in, Q_out, eta = self._verim_hesapla()
            self._sonuclari_goster(basarili, W_net, Q_in, Q_out, eta)

        except Exception as ex:
            self._durum(f"Hata: {ex}")
            self._sag_panel_icerik_guncelle(
                ft.Column(
                    controls=[
                        ft.Text("HATA", size=14, weight="bold", color=ft.Colors.RED_400),
                        ft.Divider(color=ft.Colors.RED_700),
                        ft.Text(str(ex), size=11, color=ft.Colors.RED_200, selectable=True),
                    ]
                )
            )

    def _sonuclari_goster(self, basarili: bool, W_net=None, Q_in=None, Q_out=None, eta=None):
        renk = ft.Colors.GREEN_400 if basarili else ft.Colors.ORANGE_400
        ozet = "Cozum tamamlandi" if basarili else "Kismi cozum — bazi degerler eksik"
        self._durum(ozet)

        satirlar = []
        for i, b in enumerate(self.baglantilar):
            s = b.cozulmus_durum
            if s is None:
                continue

            def _f(v, scale=1.0, digits=2, birim=""):
                return f"{v * scale:.{digits}f} {birim}".strip() if v is not None else "—"

            t_str = _f(s.T - 273.15 if s.T is not None else None, digits=1, birim="C")
            p_str = _f(s.P, 1e-6, 3, "MPa")
            h_str = _f(s.h, 1e-3, 2, "kJ/kg")
            m_str = _f(s.m_dot, digits=2, birim="kg/s")

            satirlar.append(
                ft.Container(
                    padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                    border_radius=6,
                    bgcolor=ft.Colors.BLUE_GREY_700,
                    margin=ft.Margin(bottom=5),
                    content=ft.Column(
                        spacing=3,
                        controls=[
                            ft.Text(
                                f"{b.etiket or f'S{i + 1}'}  {b.kaynak_widget.isim} -> {b.hedef_widget.isim}",
                                size=10,
                                weight="bold",
                                color=ft.Colors.CYAN_300,
                            ),
                            ft.Row(spacing=6, controls=[
                                ft.Text(f"T = {t_str}", size=10, color=ft.Colors.WHITE70),
                                ft.Text(f"P = {p_str}", size=10, color=ft.Colors.WHITE70),
                            ]),
                            ft.Row(spacing=6, controls=[
                                ft.Text(f"h = {h_str}", size=10, color=ft.Colors.WHITE70),
                                ft.Text(f"m = {m_str}", size=10, color=ft.Colors.WHITE70),
                            ]),
                        ],
                    ),
                )
            )

        self._sag_panel_icerik_guncelle(
            ft.Column(
                scroll=ft.ScrollMode.AUTO,
                controls=[
                    ft.Text("COZUM SONUCLARI", size=11, weight="bold",
                            color=ft.Colors.CYAN_300),
                    ft.Text(ozet, size=11, color=renk),
                    ft.Divider(color=ft.Colors.BLUE_GREY_600),
                    # —— Verim Paneli ——
                    ft.Container(
                        bgcolor=ft.Colors.BLUE_GREY_700,
                        border_radius=6,
                        padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                        margin=ft.Margin(bottom=6),
                        content=ft.Column(spacing=3, controls=[
                            ft.Text("PERFORMANS", size=9, weight="bold", color=ft.Colors.AMBER_400),
                            ft.Text(f"W_net  = {W_net/1000:.1f} kW" if W_net is not None else "W_net  = —",
                                    size=10, color=ft.Colors.WHITE70),
                            ft.Text(f"Q_in   = {Q_in/1000:.1f} kW" if Q_in  is not None else "Q_in   = —",
                                    size=10, color=ft.Colors.WHITE70),
                            ft.Text(f"Q_out  = {Q_out/1000:.1f} kW" if Q_out is not None else "Q_out  = —",
                                    size=10, color=ft.Colors.WHITE70),
                            ft.Text(f"eta_th = {eta:.2f} %" if eta is not None else "eta_th = —",
                                    size=10, weight="bold",
                                    color=ft.Colors.GREEN_400 if eta and eta > 30 else ft.Colors.ORANGE_400),
                        ]),
                    ),
                    ft.Divider(color=ft.Colors.BLUE_GREY_600),
                    *satirlar,
                ],
            )
        )

    # ── Yardımcılar ───────────────────────────────────────────────────────
    def _durum(self, mesaj: str):
        if self.durum_metni:
            self.durum_metni.value = mesaj
            self.durum_metni.update()

    def _sag_panel_sifirla(self):
        self._sag_panel_icerik_guncelle(
            ft.Text(
                "Bilesen eklemek icin\nsol panelden tiklayin.\n\n"
                "Porta tiklayin; baglanti\nfareyi takip eder.\n\n"
                "S etiketine tiklayarak\ndurum penceresini acin.\n\n"
                "Bos alana tiklayarak\nx/y ekseninde yon kirin.\n\n"
                "Coz butonuyla hesaplayin.",
                color=ft.Colors.BLUE_GREY_400,
                size=12,
                text_align=ft.TextAlign.CENTER,
            )
        )

    def _sag_panel_icerik_guncelle(self, icerik):
        if self.sag_panel_icerik:
            self.sag_panel_icerik.content = icerik
            self.sag_panel_icerik.update()


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 4: BİLEŞEN WIDGET
# ─────────────────────────────────────────────────────────────────────────────
class BilesenWidget(ft.Stack):
    """Her bir termodinamik bileşeni ekranda gösteren ve kullanıcı etkileşimini yöneten widget."""
    def __init__(self, tip: str, isim: str, durum):
        super().__init__()
        self.tip      = tip
        self.isim     = isim
        self.durum    = durum
        self.ayarlar  = dict(BILESEN_CONFIGS[tip]["params"])

        self.left     = 100
        self.top      = 100
        self.width    = W
        self.height   = H
        self._aci      = 0.0
        self._aci_adet = 0   # 90 derece adim sayisi (0-3)
        self._yansima  = 1
        self._metin_containerlar = []

        self.controls = [self._gorsel_olustur(), self._kalkan_olustur(), *self._portlar_olustur(), self._ayar_btn_olustur(), self._dondur_btn_olustur()]

    def port_gercek_konum(self, port_cfg):
        """Port konumunu rotasyon dikkate alarak hesapla."""
        cx, cy = W / 2, H / 2
        px, py = port_cfg["x"] - cx, port_cfg["y"] - cy
        # Once yansitmayi uygula (rotasyondan once)
        px = px * self._yansima

        # Sonra rotasyonu uygula
        n = self._aci_adet % 4
        for _ in range(n):
            px, py = -py, px
        return (self.left + px + cx, self.top + py + cy)

    def _ayar_btn_olustur(self):
        """Sag ust kosede ozellikleri acan buton."""
        return ft.GestureDetector(
            left=W - 16, top=0, width=16, height=16,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda e: self.durum.ozellikleri_goster(self),
            content=ft.Container(
                border_radius=3,
                bgcolor=ft.Colors.BLUE_GREY_600,
                alignment=ft.Alignment(0, 0),
                content=ft.Text("\u2699", size=10, color=ft.Colors.WHITE),
            ),
        )

    def _dondur_btn_olustur(self):
        """Sol ust kosede dondurmek icin buton."""
        return ft.GestureDetector(
            left=0, top=0, width=16, height=16,
            mouse_cursor=ft.MouseCursor.CLICK,
            on_tap=lambda e: self.durum._dondur(self),
            content=ft.Container(
                border_radius=3,
                bgcolor=ft.Colors.BLUE_GREY_600,
                alignment=ft.Alignment(0, 0),
                content=ft.Text("\u21bb", size=10, color=ft.Colors.WHITE),
            ),
        )

    def _portlar_olustur(self):
        """Port GestureDetector'larını ayrı bir liste olarak döndürür (kalkanın üstüne konacak)."""
        cfg = BILESEN_CONFIGS[self.tip]
        portlar = []
        for p in cfg["portlar"]:
            _port_renk = ft.Colors.GREEN_500 if p.get("giris") else ft.Colors.RED_500
            portlar.append(
                ft.GestureDetector(
                    left=p["x"] - 7, top=p["y"] - 7, width=14, height=14,
                    mouse_cursor=ft.MouseCursor.CLICK,
                    on_tap=lambda e, _p=p: self.durum.port_tikla(self, _p),
                    content=ft.Container(
                        border_radius=7,
                        bgcolor=ft.Colors.BLACK87,
                        border=ft.Border(
                            top=ft.BorderSide(2, _port_renk),
                            bottom=ft.BorderSide(2, _port_renk),
                            left=ft.BorderSide(2, _port_renk),
                            right=ft.BorderSide(2, _port_renk),
                        ),
                        tooltip=p["ad"],
                    ),
                )
            )
        return portlar

    def _gorsel_olustur(self):
        cfg  = BILESEN_CONFIGS[self.tip]
        renk = cfg["renk"]
        m    = H * 0.2

        if self.tip == "Turbine":
            pts = [cv.Path.MoveTo(0, m), cv.Path.LineTo(W, 0),
                   cv.Path.LineTo(W, H), cv.Path.LineTo(0, H - m), cv.Path.Close()]
        elif self.tip == "Compressor":
            pts = [cv.Path.MoveTo(0, 0), cv.Path.LineTo(W, m),
                   cv.Path.LineTo(W, H - m), cv.Path.LineTo(0, H), cv.Path.Close()]
        elif self.tip == "Splitter":
            pts = [cv.Path.MoveTo(0, m * 1.5), cv.Path.LineTo(W, 0),
                   cv.Path.LineTo(W, H), cv.Path.LineTo(0, H - m * 1.5), cv.Path.Close()]
        elif self.tip == "Mixer":
            pts = [cv.Path.MoveTo(0, 0), cv.Path.LineTo(W, m * 1.5),
                   cv.Path.LineTo(W, H - m * 1.5), cv.Path.LineTo(0, H), cv.Path.Close()]
        else:  # Recuperator, Heat Exchanger — dikdortgen
            pts = [cv.Path.MoveTo(0, 0), cv.Path.LineTo(W, 0),
                   cv.Path.LineTo(W, H), cv.Path.LineTo(0, H), cv.Path.Close()]

        sekil = cv.Canvas(
            width=W, height=H,
            shapes=[cv.Path(elements=pts,
                            paint=ft.Paint(style=ft.PaintingStyle.FILL, color=renk))],
        )

        # Metin containerlarini ayri olusturup sakla, boylece aynalama sonrasi
        # metinleri tersine cevirip okunur tutabiliriz.
        _etiket_cont = ft.Container(
            width=W, height=H,
            alignment=ft.Alignment(0, 0),
            content=ft.Text(cfg["etiket"], size=18, weight="bold", color=ft.Colors.WHITE),
        )
        _isim_cont = ft.Container(
            top=2, width=W,
            content=ft.Text(self.isim, size=8, color=ft.Colors.WHITE60, text_align=ft.TextAlign.CENTER),
        )
        # kaydet
        self._metin_containerlar = [_etiket_cont, _isim_cont]

        return ft.Stack(
            width=W, height=H,
            controls=[
                sekil,
                _etiket_cont,
                _isim_cont,
            ],
        )

    def _kalkan_olustur(self):
        return ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.MOVE,
            on_pan_update=self._hareket,
            on_secondary_tap=self._sag_tik,
            on_long_press=self._sag_tik,
            on_double_tap=self._cift_tik,
            content=ft.Container(
                width=W, height=H,
                bgcolor=ft.Colors.with_opacity(0, "black"),
            ),
        )

    def _hareket(self, e):
        self.left += e.local_delta.x * self._yansima
        self.top  += e.local_delta.y
        self.update()
        self.durum.baglantilari_yenile()

    def _sag_tik(self, e):
        self.durum.bilesen_menu_ac(self)

    def _cift_tik(self, e):
        self.durum.ozellikleri_goster(self)


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 5: BAĞLANTI ORTA NOKTA BUTONU  (sinir sarti girmek icin)
# ─────────────────────────────────────────────────────────────────────────────
class DurumKutusu(ft.GestureDetector):
    """Bağlantı üzerindeki geçerli durumu gösteren küçük bilgi penceresi."""
    def __init__(self, baglanti, durum):
        self._baglanti = baglanti
        self._durum = durum
        mx, my = baglanti.orta_konum()
        super().__init__(
            left=mx + 18,
            top=my - 42,
            width=165,
            height=134,
            mouse_cursor=ft.MouseCursor.MOVE,
            on_tap=lambda e: None,
            on_pan_update=self._surukle,
            content=self._icerik(),
        )

    def _fmt(self, v, scale=1.0, digits=2, birim=""):
        if v is None:
            return "-"
        return f"{v * scale:.{digits}f}{(' ' + birim) if birim else ''}"

    def _alan_goster(self, etiket, alan, deger, birim, scale=1.0, digits=2):
        b = self._baglanti
        # priority: kullanici -> yayilim -> motor -> unknown
        if alan in b.kullanici_girdileri:
            raw = b.kullanici_girdileri[alan]
            if alan == "T":
                val = self._durum._sicaklik_gosterim_c(raw)
            else:
                val = raw
            deger_str = f"{val * scale:.{digits}f} {birim}"
            renk = "#22C55E"
            on_ek = ""
        elif alan in b.yayilim_girdileri:
            raw = b.yayilim_girdileri[alan]
            if alan == "T":
                val = self._durum._sicaklik_gosterim_c(raw)
            else:
                val = raw
            deger_str = f"{val * scale:.{digits}f} {birim}"
            renk = "#A855F7"
            on_ek = "~ "
        elif alan in b.motor_sonuclari:
            raw = b.motor_sonuclari[alan]
            if alan == "T":
                val = self._durum._sicaklik_gosterim_c(raw)
            else:
                val = raw
            deger_str = f"{val * scale:.{digits}f} {birim}"
            renk = "#3B82F6"
            on_ek = ""
        else:
            deger_str = "UNKNOWN"
            renk = "#6B7280"
            on_ek = ""
        return ft.Text(f"{etiket} = {on_ek}{deger_str}", size=10, color=renk)

    def _icerik(self):
        b = self._baglanti
        # build preview state from yayilim + kullanici (kullanici baskindir)
        merged = dict(b.yayilim_girdileri)
        merged.update(b.kullanici_girdileri)
        s = b.cozulmus_durum
        if s is None:
            s = self._durum._sinir_sartlarini_coz(self._durum._filtreli_sinir_sartlari(merged))
        t = s.T if s else None
        p = s.P if s else None
        h = s.h if s else None
        ent = s.s if s else None
        m = s.m_dot if s else None
        t_c = self._durum._sicaklik_gosterim_c(t) if t is not None else None
        if t is not None and t_c is not None:
            t_display = t_c
        else:
            t_display = None
        return ft.Container(
            border_radius=3,
            bgcolor=ft.Colors.BLUE_GREY_50,
            border=ft.Border(
                top=ft.BorderSide(1, ft.Colors.BLUE_GREY_300),
                bottom=ft.BorderSide(1, ft.Colors.BLUE_GREY_300),
                left=ft.BorderSide(1, ft.Colors.BLUE_GREY_300),
                right=ft.BorderSide(1, ft.Colors.BLUE_GREY_300),
            ),
            padding=0,
            tooltip="Surukle: pencereyi tasi",
            content=ft.Column(
                spacing=0,
                controls=[
                    ft.Container(
                        height=22,
                        bgcolor=ft.Colors.BLUE_GREY_200,
                        padding=ft.Padding(left=6, right=3, top=2, bottom=2),
                        content=ft.Row(
                            spacing=4,
                            controls=[
                                ft.Text(self._baglanti.etiket or "S?", size=11, weight="bold", color=ft.Colors.BLUE_GREY_900),
                                ft.Container(expand=True),
                                ft.TextButton(
                                    "Duzenle",
                                    height=18,
                                    style=ft.ButtonStyle(
                                        padding=ft.Padding(left=4, right=4, top=0, bottom=0),
                                        color=ft.Colors.BLUE_700,
                                    ),
                                    on_click=lambda e: self._durum.sinir_sartlari_goster(self._baglanti),
                                ),
                                ft.TextButton(
                                    "x",
                                    height=18,
                                    style=ft.ButtonStyle(
                                        padding=ft.Padding(left=4, right=4, top=0, bottom=0),
                                        color=ft.Colors.RED_700,
                                    ),
                                    on_click=lambda e: self._durum.durum_penceresi_kapat(self._baglanti),
                                ),
                            ],
                        ),
                    ),
                    ft.Container(
                        padding=ft.Padding(left=8, right=8, top=6, bottom=6),
                        content=ft.Column(
                            spacing=2,
                            controls=[
                                self._alan_goster("T", "T", t_display, "C", scale=1.0, digits=2),
                                self._alan_goster("P", "P", p, "MPa", scale=1e-6, digits=3),
                                self._alan_goster("h", "h", h, "kJ/kg", scale=1e-3, digits=2),
                                self._alan_goster("s", "s", ent, "kJ/kgK", scale=1e-3, digits=3),
                                self._alan_goster("m", "m_dot", m, "kg/s", scale=1.0, digits=2),
                            ],
                        ),
                    ),
                ],
            ),
        )

    def _surukle(self, e):
        self.left += e.local_delta.x
        self.top += e.local_delta.y
        self.update()

    def _baglanti_butonu_renk(self, baglanti):
        n = len(baglanti.kullanici_girdileri)
        cozuldu = bool(baglanti.motor_sonuclari)
        if cozuldu:
            return ft.Colors.CYAN_800
        if n >= 2:
            return ft.Colors.GREEN_900
        if n == 1:
            return ft.Colors.ORANGE_900
        return ft.Colors.BLUE_GREY_700

    def _baglanti_butonu_ikon(self, baglanti):
        n = len(baglanti.kullanici_girdileri)
        cozuldu = bool(baglanti.motor_sonuclari)
        if cozuldu:
            return ""
        if n >= 2:
            return "✓"
        if n == 1:
            return "⚠"
        return "?"

    def verileri_guncelle(self):
        self.content = self._icerik()
        try:
            self.update()
        except Exception:
            pass


class RotaNoktasi(ft.GestureDetector):
    def __init__(self, baglanti, durum, index):
        self._baglanti = baglanti
        self._durum = durum
        self.index = index
        x, y = baglanti.rota_noktalari[index]
        super().__init__(
            left=x - 7,
            top=y - 7,
            width=14,
            height=14,
            mouse_cursor=ft.MouseCursor.MOVE,
            on_tap=lambda e: durum.durum_penceresi_ac(baglanti),
            on_double_tap=lambda e: durum.rota_noktasi_ekle(baglanti, self.index),
            on_secondary_tap=lambda e: durum.rota_noktasi_ekle(baglanti, self.index),
            on_pan_update=self._surukle,
            content=ft.Container(
                border_radius=7,
                bgcolor=ft.Colors.CYAN_900,
                border=ft.Border(
                    top=ft.BorderSide(2, ft.Colors.CYAN_200),
                    bottom=ft.BorderSide(2, ft.Colors.CYAN_200),
                    left=ft.BorderSide(2, ft.Colors.CYAN_200),
                    right=ft.BorderSide(2, ft.Colors.CYAN_200),
                ),
                alignment=ft.Alignment(0, 0),
                tooltip="Tikla: durum penceresi | Surukle: x/y ekseninde kir",
            ),
        )

    def _surukle(self, e):
        dx = e.local_delta.x
        dy = e.local_delta.y
        if abs(dx) >= abs(dy):
            dy = 0
        else:
            dx = 0
        self.left += dx
        self.top += dy
        ox = 7
        oy = 7
        self._baglanti.rota_noktalari[self.index] = (self.left + ox, self.top + oy)
        self.update()
        self._durum._ciz_baglantilar()

    def konumu_guncelle(self):
        x, y = self._baglanti.rota_noktalari[self.index]
        self.left = x - 7
        self.top = y - 7
        try:
            self.update()
        except Exception:
            pass


class BaglantiBolumu(ft.GestureDetector):
    def __init__(self, baglanti, durum):
        self._baglanti = baglanti
        self._durum    = durum
        self.ofset_x   = 0.0
        self.ofset_y   = 0.0
        mx, my = baglanti.orta_konum()
        super().__init__(
            left=mx - 8, top=my - 8,
            width=16, height=16,
            mouse_cursor=ft.MouseCursor.MOVE,
            on_tap=lambda e: durum.sinir_sartlari_goster(baglanti),
            on_pan_update=self._surukle,
            content=ft.Container(
                border_radius=8,
                bgcolor=self._baglanti_butonu_renk(baglanti),
                border=ft.Border(
                    top=ft.BorderSide(2, ft.Colors.CYAN_300),
                    bottom=ft.BorderSide(2, ft.Colors.CYAN_300),
                    left=ft.BorderSide(2, ft.Colors.CYAN_300),
                    right=ft.BorderSide(2, ft.Colors.CYAN_300),
                ),
                alignment=ft.Alignment(0, 0),
                content=ft.Text(f"{baglanti.etiket or 'S?'} {self._baglanti_butonu_ikon(baglanti)}", size=7, weight="bold", color=ft.Colors.WHITE),
                tooltip="Surukle: yolu degistir  |  Tikla: sinir sarti gir",
            ),
        )

    def _baglanti_butonu_renk(self, baglanti):
        n = len(baglanti.kullanici_girdileri)
        cozuldu = bool(baglanti.motor_sonuclari)
        if cozuldu:
            return ft.Colors.CYAN_800
        if n >= 2:
            return ft.Colors.GREEN_900
        if n == 1:
            return ft.Colors.ORANGE_900
        return ft.Colors.BLUE_GREY_700

    def _baglanti_butonu_ikon(self, baglanti):
        n = len(baglanti.kullanici_girdileri)
        cozuldu = bool(baglanti.motor_sonuclari)
        if cozuldu:
            return ""
        if n >= 2:
            return "✓"
        if n == 1:
            return "⚠"
        return "?"

    def _surukle(self, e):
        dx = e.local_delta.x
        dy = e.local_delta.y
        if abs(dx) >= abs(dy):
            dy = 0
        else:
            dx = 0
        self.ofset_x += dx
        self.ofset_y += dy
        self.left    += dx
        self.top     += dy
        self.update()
        self._durum._ciz_baglantilar()

    def konumu_guncelle(self):
        mx, my = self._baglanti.orta_konum()
        self.left = mx - 8 + self.ofset_x
        self.top  = my - 8 + self.ofset_y
        try:
            self.update()
        except Exception:
            pass


# ─────────────────────────────────────────────────────────────────────────────
# BÖLÜM 6: ANA UYGULAMA
# ─────────────────────────────────────────────────────────────────────────────
def main(page: ft.Page):
    """Flet sayfasını hazırlayıp uygulamanın ana görünümünü oluşturur.

    Sayfa, sol bileşen paleti, orta çizim alanı ve sağ sonuç paneli
    ile kullanıcının bir çevrim şeması oluşturmasını sağlar.
    """
    page.title   = "TEKNOFEST"
    page.bgcolor = ft.Colors.BLUE_GREY_900
    page.padding = 0
    page.window_min_width  = 960
    page.window_min_height = 640

    uygulama = UygulamaDurumu()
    uygulama.page = page

    # Baglanti cizim kanvasi
    baglanti_canvas = cv.Canvas(shapes=[], expand=True)
    uygulama.baglanti_canvas = baglanti_canvas

    rota_yakalayici = ft.GestureDetector(
        mouse_cursor=ft.MouseCursor.CLICK,
        on_hover=uygulama.gecici_rota_hareket,
        on_tap_down=uygulama.gecici_rota_tikla,
        content=ft.Container(expand=True, bgcolor=ft.Colors.with_opacity(0, "black")),
    )
    uygulama.rota_yakalayici = rota_yakalayici

    # Cizim alani (merkez Stack)
    cizim_alani = ft.Stack(expand=True, controls=[baglanti_canvas, rota_yakalayici])
    uygulama.cizim_alani = cizim_alani

    # Sag panel icerigi
    sag_panel_icerik = ft.Container(
        expand=True,
        padding=10,
        content=ft.Text(
            "Bilesen eklemek icin\nsol panelden tiklayin.\n\n"
            "Porta tiklayin; baglanti\nfareyi takip eder.\n\n"
            "S etiketine tiklayarak\ndurum penceresini acin.\n\n"
            "Bos alana tiklayarak\nyon degistirin; hedef porta\nbasinca baglanti biter.\n\n"
            "Coz butonuyla hesaplayin.",
            color=ft.Colors.BLUE_GREY_400,
            size=12,
            text_align=ft.TextAlign.CENTER,
        ),
    )
    uygulama.sag_panel_icerik = sag_panel_icerik

    sag_panel = ft.Container(
        width=235,
        bgcolor=ft.Colors.BLUE_GREY_800,
        border=ft.Border(left=ft.BorderSide(1, ft.Colors.BLUE_GREY_600)),
        content=ft.Column(
            controls=[
                ft.Container(
                    padding=ft.Padding(left=12, right=12, top=8, bottom=8),
                    content=ft.Text(
                        "OZELLIKLER / SONUCLAR",
                        size=10, weight="bold", color=ft.Colors.BLUE_GREY_400,
                    ),
                ),
                ft.Divider(color=ft.Colors.BLUE_GREY_600, height=1),
                sag_panel_icerik,
            ],
        ),
    )

    # Akiskan secimi
    def _akiskan_degis(e):
        uygulama.akiskan = akiskan_dd.value

    akiskan_dd = ft.Dropdown(
        value="CarbonDioxide",
        width=180,
        options=[ft.dropdown.Option(a) for a in AKISKANLAR],
    )
    akiskan_dd.on_change = _akiskan_degis
    uygulama._akiskan_dd_ref = akiskan_dd

    # Ust arac cubugu
    durum_metni = ft.Text("Hazir", color=ft.Colors.BLUE_GREY_400, size=11)
    uygulama.durum_metni = durum_metni

    toolbar = ft.Container(
        height=60,
        bgcolor=ft.Colors.BLUE_GREY_800,
        border=ft.Border(bottom=ft.BorderSide(1, ft.Colors.BLUE_GREY_600)),
        padding=ft.Padding(left=16, right=16, top=8, bottom=8),
        content=ft.Row(
            vertical_alignment=ft.CrossAxisAlignment.CENTER,
            controls=[
                ft.Text(
                    "ÇEVRİM TASARIMCI",
                    size=15, weight="bold", color=ft.Colors.CYAN_300,
                ),
                ft.Container(width=18),
                ft.Text("AKIŞKAN:", color=ft.Colors.WHITE70, size=12),
                akiskan_dd,
                ft.Container(width=10),
                ft.ElevatedButton(
                    "Çöz",
                    bgcolor=ft.Colors.GREEN_700,
                    color=ft.Colors.WHITE,
                    on_click=lambda _: uygulama.coz(),
                ),
                ft.Container(width=6),
                ft.ElevatedButton(
                    "Temizle",
                    bgcolor=ft.Colors.RED_900,
                    color=ft.Colors.WHITE,
                    on_click=lambda _: uygulama.tumu_temizle(),
                ),
                
                ft.Container(expand=True),
                durum_metni,
            ],
        ),
    )

    # Sol panel (bilesen paleti)
    def bilesen_btn(tip: str):
        cfg = BILESEN_CONFIGS[tip]
        return ft.Container(
            border_radius=8,
            bgcolor=ft.Colors.BLUE_GREY_700,
            margin=ft.Margin(bottom=5),
            padding=ft.Padding(left=8, right=8, top=6, bottom=6),
            ink=True,
            on_click=lambda _, t=tip: uygulama.bilesen_ekle(t),
            content=ft.Row(
                spacing=8,
                controls=[
                    ft.Container(
                        width=36, height=28, border_radius=4,
                        bgcolor=cfg["renk"],
                        alignment=ft.Alignment(0, 0),
                        content=ft.Text(cfg["etiket"], size=11, weight="bold",
                                        color=ft.Colors.WHITE),
                    ),
                    ft.Text(tip, size=12, color=ft.Colors.WHITE),
                ],
            ),
        )

    sol_panel = ft.Container(
        width=185,
        bgcolor=ft.Colors.BLUE_GREY_800,
        border=ft.Border(right=ft.BorderSide(1, ft.Colors.BLUE_GREY_600)),
        padding=12,
        content=ft.Column(
            controls=[
                ft.Text("BILESEN PALETI", size=10, weight="bold",
                        color=ft.Colors.BLUE_GREY_400),
                ft.Divider(color=ft.Colors.BLUE_GREY_600, height=1),
                *[bilesen_btn(t) for t in BILESEN_CONFIGS],
                ft.Divider(color=ft.Colors.BLUE_GREY_600, height=1),
                ft.Text("HAZIR SABLONLAR", size=10, weight="bold",
                        color=ft.Colors.BLUE_GREY_400),
                *[
                    ft.Container(
                        border_radius=6,
                        bgcolor=ft.Colors.INDIGO_900,
                        margin=ft.Margin(bottom=4),
                        padding=ft.Padding(left=8, right=8, top=5, bottom=5),
                        ink=True,
                        on_click=lambda _, s=sn: uygulama.sablon_yukle(s),
                        content=ft.Text(sn, size=11, color=ft.Colors.WHITE),
                    )
                    for sn in SABLONLAR
                ],
                ft.Divider(color=ft.Colors.BLUE_GREY_600, height=1),
                ft.Text("KULLANIM", size=10, weight="bold",
                        color=ft.Colors.BLUE_GREY_500),
                ft.Text(
                    "1) Tiklayarak bilesen ekle\n"
                    "2) Sari porta tikla -> baslat\n"
                    "3) Bos alana tikla -> yon kir\n"
                    "4) Hedef porta tikla -> bagla\n"
                    "5) S etiketi -> durum penceresi\n"
                    "6) Sag tikla -> menu\n"
                    "7) Coz butonuna bas",
                    size=10, color=ft.Colors.BLUE_GREY_500,
                ),
            ],
        ),
    )

    # Alt durum cubugu
    motor_renk  = ft.Colors.GREEN_400 if MOTOR_HAZIR else ft.Colors.RED_400
    motor_metin = "Motor: Aktif (CoolProp)" if MOTOR_HAZIR else "Motor: CoolProp bulunamadi"

    durum_cubugu = ft.Container(
        height=26,
        bgcolor=ft.Colors.BLUE_GREY_900,
        border=ft.Border(top=ft.BorderSide(1, ft.Colors.BLUE_GREY_700)),
        padding=ft.Padding(left=12, right=12, top=3, bottom=3),
        content=ft.Row(
            controls=[
                ft.Text(motor_metin, size=10, color=motor_renk),
                ft.VerticalDivider(color=ft.Colors.BLUE_GREY_600, width=20),
                ft.Text(
                    "Sari porta tikla -> baslat  |  Bos alana tikla -> x/y yon kir  |  Hedef porta tikla -> bagla  |  S etiketi -> pencere",
                    size=10, color=ft.Colors.BLUE_GREY_500,
                ),
            ],
        ),
    )

    # Ana duzen
    page.add(
        ft.Column(
            expand=True, spacing=0,
            controls=[
                toolbar,
                ft.Row(
                    expand=True, spacing=0,
                    controls=[
                        sol_panel,
                        ft.Container(content=cizim_alani, expand=True),
                        sag_panel,
                    ],
                ),
                durum_cubugu,
            ],
        )
    )


if __name__ == "__main__":
    ft.app(target=main)
 