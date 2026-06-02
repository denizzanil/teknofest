import flet as ft
import flet.canvas as cv

class MakineDugumu(ft.Container):
    def __init__(self, isim: str, baslangic_x: float, baslangic_y: float, hareket_callback):
        super().__init__()
        self.left = baslangic_x
        self.top = baslangic_y
        self.hareket_callback = hareket_callback
        
        self.w = 120
        self.h = 80

        # Termodinamik eleman tasarımı
        icerik = ft.Stack(
            width=self.w, height=self.h,
            controls=[
                # Ana Gövde
                ft.Container(
                    width=self.w, height=self.h, 
                    bgcolor=ft.Colors.with_opacity(0.15, ft.Colors.BLUE),
                    border=ft.Border(
                        top=ft.BorderSide(2, ft.Colors.BLUE_400),
                        bottom=ft.BorderSide(2, ft.Colors.BLUE_400),
                        left=ft.BorderSide(2, ft.Colors.BLUE_400),
                        right=ft.BorderSide(2, ft.Colors.BLUE_400),
                    ),
                    alignment=ft.Alignment(0, 0),
                    content=ft.Text(isim, size=16, weight=ft.FontWeight.BOLD, color=ft.Colors.WHITE)
                ),
                # Giriş Portu (Yeşil)
                ft.Container(left=-6, top=self.h/2 - 6, width=12, height=12, border_radius=6, bgcolor=ft.Colors.GREEN_500),
                # Çıkış Portu (Kırmızı)
                ft.Container(left=self.w-6, top=self.h/2 - 6, width=12, height=12, border_radius=6, bgcolor=ft.Colors.RED_500)
            ]
        )

        self.content = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.MOVE,
            on_pan_update=self.hareket_ettir,
            content=icerik
        )

    # --- PORT KOORDİNAT HESAPLAMALARI ---
    def giris_portu_kordinatlari(self):
        """Yeşil portun anlık (X, Y) merkezini verir."""
        return (self.left, self.top + self.h / 2)
        
    def cikis_portu_kordinatlari(self):
        """Kırmızı portun anlık (X, Y) merkezini verir."""
        return (self.left + self.w, self.top + self.h / 2)

    def hareket_ettir(self, e: ft.DragUpdateEvent):
        self.left += e.local_delta.x
        self.top += e.local_delta.y
        self.update()
        
        # Eleman hareket ettiğinde ana sayfadaki kablo çiziciyi uyar!
        if self.hareket_callback:
            self.hareket_callback()


def main(page: ft.Page):
    page.title = "Dinamik Boru/Kablo Bağlantısı"
    page.bgcolor = "#0a0f1a"
    page.padding = 0

    # Kabloları çizeceğimiz arka plan tuvali
    kablo_tuvali = cv.Canvas(expand=True)

    def kablolari_ciz():
        """Bileşenler arası bağlantı çizgilerini günceller."""
        kablo_tuvali.shapes.clear() # Eski çizgileri temizle

        # 1. Kompresörden çıkış koordinatını al
        cikis_x, cikis_y = kompresor.cikis_portu_kordinatlari()
        
        # 2. Türbinden giriş koordinatını al
        giris_x, giris_y = turbin.giris_portu_kordinatlari()

        # 3. İki nokta arasına boru hattını (çizgi) çek
        boru_hatti = cv.Path(
            elements=[
                cv.Path.MoveTo(cikis_x, cikis_y),
                cv.Path.LineTo(giris_x, giris_y)
            ],
            paint=ft.Paint(
                color=ft.Colors.LIGHT_BLUE_400, 
                stroke_width=3, 
                style=ft.PaintingStyle.STROKE
            )
        )
        
        kablo_tuvali.shapes.append(boru_hatti)
        kablo_tuvali.update()

    # İki farklı makine elemanı oluşturuyoruz
    kompresor = MakineDugumu("Kompresör", 100, 200, kablolari_ciz)
    turbin = MakineDugumu("Türbin", 400, 200, kablolari_ciz)

    # Başlangıçta kabloyu bir kez çizdiriyoruz
    kablolari_ciz()

    # Stack hiyerarşisi önemlidir: Önce kablo tuvali (alta), sonra makineler (üste)
    ana_ekran = ft.Stack(
        controls=[kablo_tuvali, kompresor, turbin],
        expand=True
    )

    page.add(ana_ekran)

ft.run(main)