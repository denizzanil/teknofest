import CoolProp.CoolProp as CP

class State:
    def __init__(self, fluid="Water"):
        self.fluid = fluid
        self.P = None      # Basınç [Pa]
        self.T = None      # Sıcaklık [K]
        self.h = None      # Entalpi [J/kg]
        self.s = None      # Entropi [J/kg-K]
        self.m_dot = None  # Kütlesel debi [kg/s]

    def update(self):
        """
        Bilinen iki bağımsız termodinamik özellikten (P, T, h, s) 
        geri kalan eksik özellikleri CoolProp yardımıyla otomatik hesaplar.
        """
        try:
            # 1. Basınç ve Sıcaklık biliniyorsa
            if self.P is not None and self.T is not None and self.h is None:
                self.h = CP.PropsSI('H', 'P', self.P, 'T', self.T, self.fluid)
                self.s = CP.PropsSI('S', 'P', self.P, 'T', self.T, self.fluid)
                return True
                
            # 2. Basınç ve Entalpi biliniyorsa (Örn: Türbin/Kompresör çıkışı)
            elif self.P is not None and self.h is not None and self.T is None:
                self.T = CP.PropsSI('T', 'P', self.P, 'H', self.h, self.fluid)
                self.s = CP.PropsSI('S', 'P', self.P, 'H', self.h, self.fluid)
                return True
                
            # 3. Basınç ve Entropi biliniyorsa (İzantropik işlemler için ideal çıkış)
            elif self.P is not None and self.s is not None and self.h is None:
                self.T = CP.PropsSI('T', 'P', self.P, 'S', self.s, self.fluid)
                self.h = CP.PropsSI('H', 'P', self.P, 'S', self.s, self.fluid)
                return True
                
            # 4. Sıcaklık ve Entropi biliniyorsa
            elif self.T is not None and self.s is not None and self.P is None:
                self.P = CP.PropsSI('P', 'T', self.T, 'S', self.s, self.fluid)
                self.h = CP.PropsSI('H', 'T', self.T, 'S', self.s, self.fluid)
                return True
                
        except ValueError as e:
            # CoolProp bazen faz sınırlarında veya geçersiz değerlerde hata verebilir, bunu yakalıyoruz
            print(f"CoolProp Hesaplama Hatası: {e}")
            return False
            
        return False # Eğer yeni bir parametre hesaplanamadıysa False döner