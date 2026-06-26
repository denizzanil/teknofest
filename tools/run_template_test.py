import sys
sys.path.append('c:/Users/USER/Desktop/Dersler/4.sınıf bahar/TEKNOFEST')
from gui import UygulamaDurumu


def run_with_fluid(fluid_name):
    app = UygulamaDurumu()
    # avoid flet page interactions
    app.page = None
    app.cizim_alani = type('X', (), {'controls': []})()
    app.sag_panel_icerik = None
    app.baglanti_canvas = None
    app.rota_yakalayici = None
    app._akiskan_dd_ref = None

    app.sablon_yukle('Basit Brayton')
    app.akiskan = fluid_name
    print('\n=== Running with', fluid_name, '===')
    app.coz()
    # print results
    for b in app.baglantilar:
        s = b.cozulmus_durum
        print(f"{b.etiket}: fluid={s.fluid} P={s.P} T={s.T} h={s.h} m_dot={s.m_dot}")

if __name__ == '__main__':
    run_with_fluid('CarbonDioxide')
    run_with_fluid('Nitrogen')
