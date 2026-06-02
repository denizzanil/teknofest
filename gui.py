import flet as ft
import flet.canvas as cv

class Turbin(ft.Container):
    def __init__(self, baslangic_x: float, baslangic_y: float):
        super().__init__()
        self.left = baslangic_x
        self.top = baslangic_y
        
        w = 150
        h = 110
        m = h * 0.25

        # 1. Sadece yamuğu çizmek için minimum arka plan
        yamuk_arkaplan = cv.Canvas(
            width=w, height=h,
            shapes=[
                cv.Path(
                    elements=[
                        cv.Path.MoveTo(0, m),
                        cv.Path.LineTo(w, 0),
                        cv.Path.LineTo(w, h),
                        cv.Path.LineTo(0, h - m),
                        cv.Path.Close()
                    ],
                    paint=ft.Paint(style=ft.PaintingStyle.FILL, color=ft.Colors.BLACK)
                )
            ]
        )

        # 2. Eski "kare" mantığındaki gibi elemanları üst üste koyuyoruz
        # Yazıyı ve portları riskli canvas fonksiyonlarıyla değil, standart Flet elemanlarıyla ekliyoruz.
        icerik = ft.Stack(
            width=w, height=h,
            controls=[
                # En altta çizdiğimiz yamuk
                yamuk_arkaplan, 
                
                # Tam ortaya T harfi (Standart sorunsuz ft.Text)
                ft.Container(
                    width=w, height=h, 
                    alignment=ft.Alignment(0, 0), 
                    content=ft.Text("Turbine", size=24, weight=ft.FontWeight.NORMAL, color=ft.Colors.WHITE)
                ),
                
                # Yeşil Giriş Portu (Standart yuvarlak Container)
                ft.Container(
                    left=-6, top=h/2 - 6, 
                    width=12, height=12, border_radius=6, 
                    bgcolor=ft.Colors.GREEN_500
                ),
                
                # Kırmızı Çıkış Portu (Standart yuvarlak Container)
                ft.Container(
                    left=w-6, top=h/2 - 6, 
                    width=12, height=12, border_radius=6, 
                    bgcolor=ft.Colors.RED_500
                )
            ]
        )

        # 3. Sorunsuz çalışan sürükle bırak algılayıcısı
        self.content = ft.GestureDetector(
            mouse_cursor=ft.MouseCursor.MOVE,
            on_pan_update=self.hareket_ettir,
            content=icerik
        )

    def hareket_ettir(self, e: ft.DragUpdateEvent):
        self.left += e.local_delta.x
        self.top += e.local_delta.y
        self.update()


def main(page: ft.Page):
    page.title = "Termodinamik Arayüz"
    page.bgcolor = "#8173A7"
    page.padding = 0

    # Türbini ekranın ortasına koyuyoruz
    turbin_1 = Turbin(baslangic_x=300, baslangic_y=200)

    # Serbest taşıma için ana tuval
    tuval = ft.Stack(
        controls=[turbin_1],
        expand=True
    )

    page.add(tuval)


ft.run(main)