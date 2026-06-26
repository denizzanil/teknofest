from core.cpwrap import PropsSI

class State:
    def __init__(self, fluid="Water"):
        self.fluid = fluid
        self.P = None      # Basınç [Pa]
        self.T = None      # Sıcaklık [K]
        self.h = None      # Entalpi [J/kg]
        self.s = None      # Entropi [J/kg-K]
        self.m_dot = None  # Kütlesel debi [kg/s]
        # hangi alanların kullanıcı tarafından sabitlendiğini tut
        self.fixed = set()

    def set_value(self, name, value, fixed=False):
        setattr(self, name, value)
        if fixed:
            try:
                self.fixed.add(name)
            except Exception:
                pass

    def is_fixed(self, name):
        return name in self.fixed

    def update(self):
        """
        Bilinen iki bağımsız termodinamik özellikten (P, T, h, s) 
        geri kalan eksik özellikleri CoolProp yardımıyla otomatik hesaplar.
        Sadece sabitlenmemis alanlara yazmaya çalışır.
        """
        try:
            # Debug: hangi akışkan ile hangi değerlerle update çağrıldı?
            try:
                print(f"State.update(): fluid={self.fluid} P={self.P} T={self.T} h={self.h} s={self.s} m_dot={self.m_dot} fixed={sorted(list(self.fixed))}")
            except Exception:
                pass

            # 1. Basınç ve Sıcaklık biliniyorsa
            if self.P is not None and self.T is not None and self.h is None:
                # sadece yazılmamış (veya sabit değil) alanları doldur
                if self.h is None and not self.is_fixed('h'):
                    self.h = PropsSI('H', 'P', self.P, 'T', self.T, self.fluid)
                if self.s is None and not self.is_fixed('s'):
                    self.s = PropsSI('S', 'P', self.P, 'T', self.T, self.fluid)
                return True

            # 2. Basınç ve Entalpi biliniyorsa (Örn: Türbin/Kompresör çıkışı)
            elif self.P is not None and self.h is not None and self.T is None:
                if self.T is None and not self.is_fixed('T'):
                    self.T = PropsSI('T', 'P', self.P, 'H', self.h, self.fluid)
                if self.s is None and not self.is_fixed('s'):
                    self.s = PropsSI('S', 'P', self.P, 'H', self.h, self.fluid)
                return True

            # 3. Basınç ve Entropi biliniyorsa (İzantropik işlemler için ideal çıkış)
            elif self.P is not None and self.s is not None and self.h is None:
                if self.T is None and not self.is_fixed('T'):
                    self.T = PropsSI('T', 'P', self.P, 'S', self.s, self.fluid)
                if self.h is None and not self.is_fixed('h'):
                    self.h = PropsSI('H', 'P', self.P, 'S', self.s, self.fluid)
                return True

            # 4. Sıcaklık ve Entropi biliniyorsa
            elif self.T is not None and self.s is not None and self.P is None:
                if self.P is None and not self.is_fixed('P'):
                    self.P = PropsSI('P', 'T', self.T, 'S', self.s, self.fluid)
                if self.h is None and not self.is_fixed('h'):
                    self.h = PropsSI('H', 'T', self.T, 'S', self.s, self.fluid)
                return True

        except ValueError as e:
            # CoolProp bazen faz sınırlarında veya geçersiz değerlerde hata verebilir, bunu yakalıyoruz
            print(f"CoolProp Hesaplama Hatası: {e}")
            return False

        return False # Eğer yeni bir parametre hesaplanamadıysa False döner
