from core.cpwrap import PropsSI

class Component:

    def __init__(self, name):
        self.name = name
        self.inlet_states = []
        self.outlet_states = []
        
      
        self.is_isobaric = False    # Sabit basınçlı mı? (dP = 0)
        self.is_isothermal = False  # Sabit sıcaklıklı mı? (dT = 0)
        self.is_isenthalpic = False # Sabit entalpili mi? (Vana / Kısılma valfi)

    def add_inlet(self, state):
        self.inlet_states.append(state)

    def add_outlet(self, state):
        self.outlet_states.append(state)

    def apply_assumptions(self):

        solved_something = False
        
        # Sadece 1 giriş ve 1 çıkışı olan elemanlar için temel kopyalama
        if len(self.inlet_states) == 1 and len(self.outlet_states) == 1:
            inlet = self.inlet_states[0]
            outlet = self.outlet_states[0]

            # 0. KÜTLE KORUNUMU (Tüm 1-1 elemanlarda sabittir)
            if inlet.m_dot is not None and outlet.m_dot is None and not outlet.is_fixed('m_dot'):
                outlet.set_value('m_dot', inlet.m_dot)
                solved_something = True
            elif outlet.m_dot is not None and inlet.m_dot is None and not inlet.is_fixed('m_dot'):
                inlet.set_value('m_dot', outlet.m_dot)
                solved_something = True

            # 1. İZOBARİK (Sabit Basınç) Varsayımı
            if self.is_isobaric:
                if inlet.P is not None and outlet.P is None and not outlet.is_fixed('P'):
                    outlet.set_value('P', inlet.P)
                    solved_something = True
                elif outlet.P is not None and inlet.P is None and not inlet.is_fixed('P'):
                    inlet.set_value('P', outlet.P)
                    solved_something = True

            # 2. İZOTERMAL (Sabit Sıcaklık) Varsayımı
            if self.is_isothermal:
                if inlet.T is not None and outlet.T is None and not outlet.is_fixed('T'):
                    outlet.set_value('T', inlet.T)
                    solved_something = True
                elif outlet.T is not None and inlet.T is None and not inlet.is_fixed('T'):
                    inlet.set_value('T', outlet.T)
                    solved_something = True
                    
            # 3. İZENTALPİK (Sabit Entalpi) Varsayımı
            if self.is_isenthalpic:
                if inlet.h is not None and outlet.h is None and not outlet.is_fixed('h'):
                    outlet.set_value('h', inlet.h)
                    solved_something = True
                elif outlet.h is not None and inlet.h is None and not inlet.is_fixed('h'):
                    inlet.set_value('h', outlet.h)
                    solved_something = True

        return solved_something

    def solve(self):
        raise NotImplementedError("solve() metodu alt sınıfta tanımlanmalıdır.")


class Turbine(Component):
    """Akışkandan iş elde edilen genişleme elemanı."""
    def __init__(self, name, isentropic_efficiency=1.0):
        super().__init__(name)
        self.eta_s = isentropic_efficiency

    def solve(self):
        # Ata sınıftaki varsayımları ve kütle korunumunu çalıştır
        solved_something = self.apply_assumptions()
        
        inlet = self.inlet_states[0]
        outlet = self.outlet_states[0]

        # Enerji Dengesi (İzantropik verim üzerinden)
        if inlet.h is not None and inlet.s is not None and outlet.P is not None and outlet.h is None and not outlet.is_fixed('h'):
            try:
                h_out_s = PropsSI('H', 'P', outlet.P, 'S', inlet.s, inlet.fluid)
                new_h = inlet.h - self.eta_s * (inlet.h - h_out_s)
                if not outlet.is_fixed('h'):
                    outlet.set_value('h', new_h)
                    if outlet.update():
                        solved_something = True
            except ValueError as e:
                print(f"{self.name} hesaplanırken hata: {e}")

        return solved_something


class Compressor(Component):
    """Akışkanın basıncını artırmak için iş harcanan sıkıştırma elemanı."""
    def __init__(self, name, isentropic_efficiency=1.0):
        super().__init__(name)
        self.eta_s = isentropic_efficiency

    def solve(self):
        # Ata sınıftaki varsayımları ve kütle korunumunu çalıştır
        solved_something = self.apply_assumptions()
        
        inlet = self.inlet_states[0]
        outlet = self.outlet_states[0]

        # Enerji Dengesi (İzantropik verim üzerinden)
        if inlet.h is not None and inlet.s is not None and outlet.P is not None and outlet.h is None and not outlet.is_fixed('h'):
            try:
                h_out_s = PropsSI('H', 'P', outlet.P, 'S', inlet.s, inlet.fluid)
                new_h = inlet.h + (h_out_s - inlet.h) / self.eta_s
                if not outlet.is_fixed('h'):
                    outlet.set_value('h', new_h)
                    if outlet.update():
                        solved_something = True
            except ValueError as e:
                print(f"{self.name} hesaplanırken hata: {e}")

        return solved_something


class SimpleHeatExchanger(Component):
    """Sisteme ısı ekleyen veya atan, ideal (izobarik) ısı değiştirici."""
    def __init__(self, name):
        super().__init__(name)
        # CyclePad arayüzünde varsayılan olarak izobarik kabul ediyoruz
        self.is_isobaric = True 

    def solve(self):
        # Kütle korunumunu ve izobarik varsayımı (basınç eşitlemeyi) yapar
        return self.apply_assumptions()


class Recuperator(Component):
    """
    Sıcak akım ile soğuk akım arasında ısı transferi yapan 2 girişli, 2 çıkışlı eleman.
    inlet_states[0] = Sıcak Giriş  |  inlet_states[1] = Soğuk Giriş
    outlet_states[0]= Sıcak Çıkış  |  outlet_states[1]= Soğuk Çıkış
    """
    def __init__(self, name, effectiveness=0.85):
        super().__init__(name)
        self.epsilon = effectiveness

    def solve(self):
        if len(self.inlet_states) < 2 or len(self.outlet_states) < 2:
            return False

        hot_in, cold_in = self.inlet_states[0], self.inlet_states[1]
        hot_out, cold_out = self.outlet_states[0], self.outlet_states[1]
        solved_something = False

        # 1. Kütlenin Korunumu
        if hot_in.m_dot is not None and hot_out.m_dot is None and not hot_out.is_fixed('m_dot'):
            hot_out.set_value('m_dot', hot_in.m_dot)
            solved_something = True
        if cold_in.m_dot is not None and cold_out.m_dot is None and not cold_out.is_fixed('m_dot'):
            cold_out.set_value('m_dot', cold_in.m_dot)
            solved_something = True

        # 2. Basınç Dengesi (İdealde basınç düşümü yok kabul ediyoruz)
        if hot_in.P is not None and hot_out.P is None and not hot_out.is_fixed('P'):
            hot_out.set_value('P', hot_in.P)
            solved_something = True
        if cold_in.P is not None and cold_out.P is None and not cold_out.is_fixed('P'):
            cold_out.set_value('P', cold_in.P)
            solved_something = True

        # 3. Enerji Dengesi ve Verim (Effectiveness) Hesaplaması
        if hot_in.T is not None and cold_in.T is not None and hot_in.m_dot is not None and cold_in.m_dot is not None:
            if cold_out.h is None or hot_out.h is None:
                try:
                    h_cold_max = PropsSI('H', 'T', hot_in.T, 'P', cold_in.P, cold_in.fluid)
                    max_heat_transfer_cold = cold_in.m_dot * (h_cold_max - cold_in.h)
                    
                    h_hot_min = PropsSI('H', 'T', cold_in.T, 'P', hot_in.P, hot_in.fluid)
                    max_heat_transfer_hot = hot_in.m_dot * (hot_in.h - h_hot_min)

                    Q_max = min(max_heat_transfer_cold, max_heat_transfer_hot)
                    Q_actual = self.epsilon * Q_max

                    if cold_out.h is None and not cold_out.is_fixed('h'):
                        cold_out.set_value('h', cold_in.h + (Q_actual / cold_in.m_dot))
                        if cold_out.update():
                            solved_something = True

                    if hot_out.h is None and not hot_out.is_fixed('h'):
                        hot_out.set_value('h', hot_in.h - (Q_actual / hot_in.m_dot))
                        if hot_out.update():
                            solved_something = True

                except ValueError as e:
                    print(f"{self.name} hesaplanırken hata: {e}")

        return solved_something


class Splitter(Component):
    """
    1 Giriş hattını, belirlenen oranlarda birden fazla çıkış hattına bölen eleman.
    split_fractions: Her bir çıkışa gidecek debi oranlarının listesi (Örn: [0.6, 0.4]).
    """
    def __init__(self, name, split_fractions):
        super().__init__(name)
        self.fractions = split_fractions
        if abs(sum(self.fractions) - 1.0) > 1e-5:
            raise ValueError(f"{name}: Bölme oranlarının toplamı 1.0 olmalıdır!")

    def solve(self):
        inlet = self.inlet_states[0]
        solved_something = False

        # Girişteki tüm termodinamik özellikleri çıkışlara kopyala
        for outlet in self.outlet_states:
            if inlet.P is not None and outlet.P is None and not outlet.is_fixed('P'):
                outlet.set_value('P', inlet.P)
                solved_something = True
            if inlet.T is not None and outlet.T is None and not outlet.is_fixed('T'):
                outlet.set_value('T', inlet.T)
                solved_something = True
            if inlet.h is not None and outlet.h is None and not outlet.is_fixed('h'):
                outlet.set_value('h', inlet.h)
                solved_something = True
            if inlet.s is not None and outlet.s is None and not outlet.is_fixed('s'):
                outlet.set_value('s', inlet.s)
                solved_something = True

        # Kütlenin Korunumu (Debi Bölünmesi)
        if inlet.m_dot is not None:
            for idx, outlet in enumerate(self.outlet_states):
                expected_m_dot = inlet.m_dot * self.fractions[idx]
                if outlet.m_dot is None and not outlet.is_fixed('m_dot'):
                    outlet.set_value('m_dot', expected_m_dot)
                    solved_something = True
                    
        # Tersine çözüm (Çıkış belliyse girişi bulma)
        elif any(out.m_dot is not None for out in self.outlet_states):
            for idx, outlet in enumerate(self.outlet_states):
                if outlet.m_dot is not None and inlet.m_dot is None and not inlet.is_fixed('m_dot'):
                    inlet.set_value('m_dot', outlet.m_dot / self.fractions[idx])
                    solved_something = True

        return solved_something


class Mixer(Component):
    """Birden fazla giriş hattını tek bir çıkış hattında birleştiren eleman."""
    def __init__(self, name):
        super().__init__(name)

    def solve(self):
        outlet = self.outlet_states[0]
        solved_something = False

        # 1. Basınç Dengesi
        known_P = outlet.P
        if known_P is None:
            for inlet in self.inlet_states:
                if inlet.P is not None:
                    known_P = inlet.P
                    break
        
        if known_P is not None:
            if outlet.P is None and not outlet.is_fixed('P'):
                outlet.set_value('P', known_P)
                solved_something = True
            for inlet in self.inlet_states:
                if inlet.P is None and not inlet.is_fixed('P'):
                    inlet.set_value('P', known_P)
                    solved_something = True

        # 2. Kütlenin Korunumu
        if all(inlet.m_dot is not None for inlet in self.inlet_states) and outlet.m_dot is None and not outlet.is_fixed('m_dot'):
            outlet.set_value('m_dot', sum(inlet.m_dot for inlet in self.inlet_states))
            solved_something = True

        # 3. Enerji Dengesi (Karışım Entalpisi)
        if outlet.m_dot is not None and outlet.h is None and not outlet.is_fixed('h'):
            if all(inlet.m_dot is not None and inlet.h is not None for inlet in self.inlet_states):
                total_energy = sum(inlet.m_dot * inlet.h for inlet in self.inlet_states)
                outlet.set_value('h', total_energy / outlet.m_dot)
                if outlet.update():
                    solved_something = True

        return solved_something

class Pump(Component):
    """Sıvı akışkanın basıncını artırmak için iş harcanan makine elemanı."""
    def __init__(self, name, isentropic_efficiency=1.0):
        super().__init__(name)
        self.eta_s = isentropic_efficiency

    def solve(self):
        # Ata sınıftaki kütle korunumunu çalıştır
        solved_something = self.apply_assumptions()
        
        inlet = self.inlet_states[0]
        outlet = self.outlet_states[0]

        # Enerji Dengesi (İzantropik verim üzerinden, kompresör ile aynı matematik)
        if inlet.h is not None and inlet.s is not None and outlet.P is not None and outlet.h is None and not outlet.is_fixed('h'):
            try:
                h_out_s = PropsSI('H', 'P', outlet.P, 'S', inlet.s, inlet.fluid)
                new_h = inlet.h + (h_out_s - inlet.h) / self.eta_s
                if not outlet.is_fixed('h'):
                    outlet.set_value('h', new_h)
                    if outlet.update():
                        solved_something = True
            except ValueError as e:
                print(f"{self.name} (Pompa) hesaplanırken hata: {e}")

        return solved_something

class Valve(Component):
    """Basınç düşürücü, sabit entalpili (izentalpik) genleşme valfi."""
    def __init__(self, name):
        super().__init__(name)
        # CyclePad varsayımı: Vanalarda entalpi sabittir.
        self.is_isenthalpic = True 

    def solve(self):
        # Tüm kütle ve entalpi eşitleme işini ata sınıfa devret
        return self.apply_assumptions()


class Heater(Component):
    """Basit ısıtıcı / entalpi sağlayıcı. Giriş akışına belirli bir
    birim kütle başına entalpi artışı (delta_h [J/kg]) veya güç (W)
    uygulayarak çıkış entalpisi hesaplar."""
    def __init__(self, name, delta_h: float = None, power_W: float = None):
        super().__init__(name)
        self.delta_h = delta_h
        self.power_W = power_W
        # İzobarik kabul edilebilir varsayım
        self.is_isobaric = True

    def solve(self):
        solved = self.apply_assumptions()
        if len(self.inlet_states) != 1 or len(self.outlet_states) != 1:
            return solved

        inlet = self.inlet_states[0]
        outlet = self.outlet_states[0]

        # Basınç eşitle
        if inlet.P is not None and outlet.P is None and not outlet.is_fixed('P'):
            outlet.set_value('P', inlet.P)
            solved = True

        # Eğer giriş entalpisi ve debi bilinirse entalpi artırılabilir
        if inlet.h is not None and outlet.h is None and not outlet.is_fixed('h'):
            try:
                if self.delta_h is not None:
                    outlet.set_value('h', inlet.h + self.delta_h)
                    if outlet.update():
                        solved = True
                elif self.power_W is not None and inlet.m_dot:
                    outlet.set_value('h', inlet.h + (self.power_W / inlet.m_dot))
                    if outlet.update():
                        solved = True
            except ValueError as e:
                print(f"{self.name} hesaplanırken hata: {e}")

        return solved


class Reactor(Heater):
    """Reaktör: güç (MW) verilen ve akışa entalpi veren özel ısı kaynağı.
    `power_mw` parametresi MW cinsinden verilir ve içerde W'ye çevrilir."""
    def __init__(self, name, power_mw: float = None):
        super().__init__(name)
        self.power_mw = power_mw

    def solve(self):
        # convert to W and delegate to Heater logic
        if self.power_mw is not None:
            self.power_W = float(self.power_mw) * 1e6
        return super().solve()


class Cooler(Component):
    """Soğutucu / entalpi azaltıcı eleman. İsteğe bağlı hedef sıcaklık
    (`target_T`) veya birim-kütle başına entalpi değişimi (`delta_h`)."""
    def __init__(self, name, target_T: float = None, delta_h: float = None):
        super().__init__(name)
        self.target_T = target_T
        self.delta_h = delta_h
        self.is_isobaric = True

    def solve(self):
        solved = self.apply_assumptions()
        if len(self.inlet_states) != 1 or len(self.outlet_states) != 1:
            return solved

        inlet = self.inlet_states[0]
        outlet = self.outlet_states[0]

        if inlet.P is not None and outlet.P is None and not outlet.is_fixed('P'):
            outlet.set_value('P', inlet.P)
            solved = True

        # Eğer hedef sıcaklık verilmişse entalpi buradan hesapla
        try:
            if self.target_T is not None and outlet.h is None and inlet.P is not None and not outlet.is_fixed('h') and not outlet.is_fixed('T'):
                outlet.set_value('T', self.target_T)
                outlet.set_value('h', PropsSI('H', 'P', inlet.P, 'T', outlet.T, inlet.fluid))
                if outlet.update():
                    solved = True
            elif self.delta_h is not None and inlet.h is not None and outlet.h is None and not outlet.is_fixed('h'):
                outlet.set_value('h', inlet.h - abs(self.delta_h))
                if outlet.update():
                    solved = True
        except ValueError as e:
            print(f"{self.name} hesaplanırken hata: {e}")

        return solved


class Source(Component):
    """Açık çevrim için kaynak (örn: çevre). Sadece çıkış portu vardır ve
    burada belirtilen temel sınır şartlarını çıkış `State`'ine yazar."""
    def __init__(self, name, P: float = None, T: float = None, h: float = None, m_dot: float = None, fluid: str = None):
        super().__init__(name)
        self.P = P
        self.T = T
        self.h = h
        self.m_dot = m_dot
        self.fluid = fluid

    def solve(self):
        solved = False
        if len(self.outlet_states) < 1:
            return solved
        out = self.outlet_states[0]
        # yazılan varsayılanları çıkış state'e uygula (kullanıcıya öncelik verilmez burada)
        if self.fluid is not None and not out.is_fixed('fluid'):
            out.fluid = self.fluid
            solved = True
        if self.P is not None and out.P is None and not out.is_fixed('P'):
            out.set_value('P', self.P)
            solved = True
        if self.T is not None and out.T is None and not out.is_fixed('T'):
            out.set_value('T', self.T)
            solved = True
        if self.h is not None and out.h is None and not out.is_fixed('h'):
            out.set_value('h', self.h)
            solved = True
        if self.m_dot is not None and out.m_dot is None and not out.is_fixed('m_dot'):
            out.set_value('m_dot', self.m_dot)
            solved = True

        if out.update():
            solved = True

        return solved


class Sink(Component):
    """Açık çevrim için sinyal (boşaltma). Genelde sadece giriş kabul eder; burada
    giriş state'inin verilerini korur (passthrough)."""
    def __init__(self, name):
        super().__init__(name)

    def solve(self):
        # Basitçe kütleyi ve basıncı inlet->outlet yoksa koru
        # Sink genelde tek girişlidir; herhangi bir ilave işlem yapmayız
        return self.apply_assumptions()