class CycleSolver:
    def __init__(self):
        self.components = []
        self.states = []

    def add_component(self, component):
        """Sisteme bir makine elemanı ekler."""
        self.components.append(component)

    def add_state(self, state):
        """Sisteme bir durum noktası ekler."""
        self.states.append(state)

    def solve(self, max_iterations=50):
        """
        Sistemdeki tüm elemanları ve durumları, artık yeni bir parametre 
        hesaplanamayana kadar döngüsel olarak çözer (Constraint Propagation).
        """
        print("--- Çözücü Başlatıldı ---")
        
        for iteration in range(max_iterations):
            something_solved = False

            # 1. Adım: Önce tüm durum noktalarını (State) kendi içinde güncellemeyi dene
            for state in self.states:
                if state.update():
                    something_solved = True

            # 2. Adım: Tüm makine elemanlarının (Component) kütle/enerji denklemlerini çalıştır
            for component in self.components:
                if component.solve():
                    something_solved = True

            # Eğer bu turda hiçbir yeni veri hesaplanamadıysa, sistem çözülmüştür veya kilitlenmiştir
            if not something_solved:
                print(f"Çözüm tamamlandı. Toplam döngü sayısı: {iteration + 1}")
                return True

        print("Uyarı: Maksimum döngü sayısına ulaşıldı, bazı parametreler eksik kalmış olabilir!")
        return False