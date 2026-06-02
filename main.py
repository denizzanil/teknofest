import core.components as comp
from core.states import State
from core.engine import CycleSolver

def recompression_cycle_test():
    solver = CycleSolver()

    # 1. Durum Noktalarını Oluştur
    s1 = State("CarbonDioxide")   # Ana Komp. Giriş
    s2 = State("CarbonDioxide")   # Ana Komp. cıkış / LTR Soguk Giriş
    s3 = State("CarbonDioxide")   # LTR Soguk cıkış / Mikser Giriş 1
    s4 = State("CarbonDioxide")   # Recomp. Giriş
    s5 = State("CarbonDioxide")   # Recomp. cıkış / Mikser Giriş 2
    s6 = State("CarbonDioxide")   # Mikser cıkış / HTR Soguk Giriş
    s7 = State("CarbonDioxide")   # HTR Soguk cıkış / Reaktor Giriş
    s8 = State("CarbonDioxide")   # Reaktor cıkış / Türbin Giriş
    s9 = State("CarbonDioxide")   # Türbin cıkış / HTR Sıcak Giriş
    s10 = State("CarbonDioxide")  # HTR Sıcak cıkış / LTR Sıcak Giriş
    s11 = State("CarbonDioxide")  # LTR Sıcak cıkış / Splitter Giriş
    s_cool = State("CarbonDioxide") # Splitter cıkış 1 / Radyator Giriş

    for s in [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11, s_cool]:
        solver.add_state(s)

    # 2. Sınır Şartları (Girdiler)
   
    s8.m_dot = 100  
    s8.T = 823.0     # Reaktor cıkış Sıcaklıgı (527 °C)
    
    # Basınc Sınırları
    s2.P = 21.0e6    # Yüksek Basınc Hattı (Ana Kompresor cıkışı)
    s9.P = 7.5e6     # Alcak Basınc Hattı (Türbin cıkışı)

    s1.T = 305.0     # Radyator cıkışı (Kompresor oncesi en soguk nokta)

    # MÜHENDISLIK NOTU: HTR ve LTR birbirine seri baglı oldugu icin, cozücünün 
    # cebirsel dongüye (algebraic loop) girmesini engellemek adına aradaki 
    # geciş sıcaklıgını bir "Tasarım Kriteri" olarak veriyoruz.
    s10.T = 530.0    

    # 3. Makine Elemanları
    main_comp = comp.Compressor("Ana_Kompresor", 0.89)
    re_comp = comp.Compressor("Recompressor", 0.89)
    turbine = comp.Turbine("Turbin", 0.92)
    
    htr = comp.Recuperator("HTR", 0.95)
    ltr = comp.Recuperator("LTR", 0.95)
    
    reactor = comp.SimpleHeatExchanger("Reaktor")
    cooler = comp.SimpleHeatExchanger("Radyator")
    
    # Akışın 65'i sogutucuya, 35'i dogrudan yeniden sıkıştırmaya
    splitter = comp.Splitter("Splitter", [0.65, 0.35]) 
    mixer = comp.Mixer("Mikser")

    for c in [main_comp, re_comp, turbine, htr, ltr, reactor, cooler, splitter, mixer]:
        solver.add_component(c)

   
    cooler.add_inlet(s_cool)
    cooler.add_outlet(s1)

    main_comp.add_inlet(s1)
    main_comp.add_outlet(s2)

    ltr.add_inlet(s10)  # Sıcak
    ltr.add_inlet(s2)   # Soguk
    ltr.add_outlet(s11)
    ltr.add_outlet(s3)

    splitter.add_inlet(s11)
    splitter.add_outlet(s_cool)  # %65 -> Radyator
    splitter.add_outlet(s4)      # %35 -> Recompressor

    re_comp.add_inlet(s4)
    re_comp.add_outlet(s5)

    mixer.add_inlet(s3)
    mixer.add_inlet(s5)
    mixer.add_outlet(s6)

    htr.add_inlet(s9)   # Sıcak
    htr.add_inlet(s6)   # Soguk
    htr.add_outlet(s10)
    htr.add_outlet(s7)

    reactor.add_inlet(s7)
    reactor.add_outlet(s8)

    turbine.add_inlet(s8)
    turbine.add_outlet(s9)

  
    solver.solve(max_iterations=100)

    print("\n" + "="*85)
    print(" DURUM NOKTALARI (STATES) DETAYLI RAPORU")
    print("="*85)
    
    state_names = [
        ("s1", "Ana Komp. Giris", s1),
        ("s2", "Ana Komp. cikis / LTR Sog. In", s2),
        ("s3", "LTR Soguk cikis. / Mikser In 1", s3),
        ("s4", "Recomp. Giris", s4),
        ("s5", "Recomp. cikis / Mikser In 2", s5),
        ("s6", "Mikser cikis / HTR Soguk In", s6),
        ("s7", "HTR Soguk cikis / Reaktor In", s7),
        ("s8", "Reaktor cikis / Turbin Giris", s8),
        ("s9", "Turbin cikis / HTR Sicak In", s9),
        ("s10", "HTR Sicak cikis / LTR Sicak In", s10),
        ("s11", "LTR Sicak cikis / Splitter In", s11),
        ("s_cool", "Radyator Giris", s_cool)
    ]
    
    for tag, desc, s in state_names:
        if s.T is not None and s.P is not None and s.h is not None and s.m_dot is not None:
            print(f"[{tag:^6}] {desc:<32} | T: {s.T:6.2f} K | P: {s.P/1e6:5.2f} MPa | h: {s.h/1e3:7.2f} kJ/kg | m_dot: {s.m_dot:5.2f} kg/s")
        else:
            print(f"[{tag:^6}] {desc:<32} | HESAPLANAMADI!")

    print("-" * 85)

    print("\n" + "="*50)
    print(" RECOMPRESSION sCO2 BRAYTON CEVRIMI RAPORU")
    print("="*50)
    
    if all(s.h is not None for s in [s1, s2, s3, s4, s5, s6, s7, s8, s9, s10, s11]):
        W_main_comp = s1.m_dot * (s2.h - s1.h) / 1e3
        W_re_comp = s4.m_dot * (s5.h - s4.h) / 1e3
        W_turb = s8.m_dot * (s8.h - s9.h) / 1e3
        
        W_net = W_turb - W_main_comp - W_re_comp
        Q_in = s8.m_dot * (s8.h - s7.h) / 1e3
        eta_th = (W_net / Q_in) * 100

        print(f"Ana Kompresor Isi      : {W_main_comp:7.2f} kW")
        print(f"Recompressor Isi       : {W_re_comp:7.2f} kW")
        print(f"Turbin Isi (uretilen)  : {W_turb:7.2f} kW")
        print("-" * 50)
        print(f"NET Guc cIKTISI (W_net): {W_net:7.2f} kW")
        print(f"Reaktorden Alinan Isi  : {Q_in:7.2f} kW")
        print(f"TERMAL VERIM (eta)     : % {eta_th:.2f}")
    else:
        print("Sistem tam olarak cozulemedigi icin performans hesaplanamadi.")
    print("="*50)

if __name__ == "__main__":
    recompression_cycle_test()