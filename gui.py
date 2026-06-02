"""
P&ID Node Editörü — DearPyGui  v1.0
====================================
Termodinamik çözücü motoru için profesyonel P&ID arayüzü.

Kurulum:
    pip install dearpygui

Çalıştırma:
    python pid_editor.py

Özellikler:
  * Şeffaf DPG düğümler — yalnızca drawlist vektörleri görünür
  * Turbine, Compressor, Heater, Cooler, Recuperator, Splitter, Mixer
  * Sağ-tık menüsü: Copy / Delete / Rotate CW/CCW / Flip H/V
  * Ortogonal (Manhattan) bağlantı çizgileri + akış yönü okları
  * JSON topoloji dışa aktarma (topology.json)
"""

import math
import json
import uuid
import dearpygui.dearpygui as dpg

# ─────────────────────────────────────────────────────────────────────────────
# Renk paleti
# ─────────────────────────────────────────────────────────────────────────────
BG         = (10,  15,  26,  255)
WIRE_COL   = (30,  100, 200, 230)
WIRE_PREV  = (56,  189, 248, 200)
ARROW_COL  = (100, 180, 255, 230)
PORT_OUT   = (250, 204, 21,  240)   # sarı
PORT_IN    = (74,  222, 128, 240)   # yeşil

SHAPE_COL = {
    "turbine":    {"fill": (249, 115, 22,  50),  "stroke": (251, 146, 60,  230)},
    "compressor": {"fill": (59,  130, 246, 50),  "stroke": (96,  165, 250, 230)},
    "heater":     {"fill": (239, 68,  68,  50),  "stroke": (248, 113, 113, 230)},
    "cooler":     {"fill": (6,   182, 212, 50),  "stroke": (34,  211, 238, 230)},
    "recuperator":{"fill": (168, 85,  247, 50),  "stroke": (192, 132, 252, 230)},
    "splitter":   {"fill": (245, 158, 11,  50),  "stroke": (251, 191, 36,  230)},
    "mixer":      {"fill": (16,  185, 129, 50),  "stroke": (52,  211, 153, 230)},
}

# ─────────────────────────────────────────────────────────────────────────────
# Port tanımları  (normalized 0‑1)
# ─────────────────────────────────────────────────────────────────────────────
PORT_DEFS = {
    "turbine":    [("in",       "in",  0.0, 0.5 ),
                   ("out",      "out", 1.0, 0.5 )],
    "compressor": [("in",       "in",  0.0, 0.5 ),
                   ("out",      "out", 1.0, 0.5 )],
    "heater":     [("in",       "in",  0.0, 0.5 ),
                   ("out",      "out", 1.0, 0.5 )],
    "cooler":     [("in",       "in",  0.0, 0.5 ),
                   ("out",      "out", 1.0, 0.5 )],
    "recuperator":[("hot_in",   "in",  0.0, 0.3 ),
                   ("cold_in",  "in",  0.5, 0.0 ),
                   ("hot_out",  "out", 1.0, 0.7 ),
                   ("cold_out", "out", 0.5, 1.0 )],
    "splitter":   [("in",       "in",  0.0, 0.5 ),
                   ("out1",     "out", 1.0, 0.25),
                   ("out2",     "out", 1.0, 0.75)],
    "mixer":      [("in1",      "in",  0.0, 0.25),
                   ("in2",      "in",  0.0, 0.75),
                   ("out",      "out", 1.0, 0.5 )],
}

SHAPE_SIZES = {
    "turbine":    (120, 80),
    "compressor": (120, 80),
    "heater":     (110, 80),
    "cooler":     (110, 80),
    "recuperator":(110,110),
    "splitter":   ( 80, 80),
    "mixer":      ( 80, 80),
}

# ─────────────────────────────────────────────────────────────────────────────
# Geometri yardımcıları
# ─────────────────────────────────────────────────────────────────────────────
def _rot(px, py, cx, cy, deg):
    r = math.radians(deg)
    dx, dy = px - cx, py - cy
    return (cx + dx * math.cos(r) - dy * math.sin(r),
            cy + dx * math.sin(r) + dy * math.cos(r))

def _fh(px, py, cx):  return (2 * cx - px, py)
def _fv(px, py, cy):  return (px, 2 * cy - py)

def T(pts, cx, cy, rot, fh, fv):
    """Noktalar listesini dönüştür."""
    out = []
    for (px, py) in pts:
        if fh:  px, py = _fh(px, py, cx)
        if fv:  px, py = _fv(px, py, cy)
        if rot: px, py = _rot(px, py, cx, cy, rot)
        out.append((px, py))
    return out

def circle_pts(cx, cy, r, n=36):
    return [(cx + r * math.cos(2 * math.pi * i / n),
             cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]

def zigzag(x, y, w, h, steps=7):
    return [(x + 10 + (w - 20) * i / steps,
             y + h * (0.28 if i % 2 == 0 else 0.72)) for i in range(steps + 1)]

def ortho(p1, p2):
    """Ortogonal (L-şekli) koordinatlar: p1 → mid-H → mid-V → p2."""
    mx = (p1[0] + p2[0]) / 2
    return [p1, (mx, p1[1]), (mx, p2[1]), p2]

def draw_arrowhead(dl, p1, p2, col, size=7):
    dx, dy = p2[0] - p1[0], p2[1] - p1[1]
    ln = math.hypot(dx, dy)
    if ln < 1: return
    ux, uy = dx / ln, dy / ln
    px, py = -uy, ux
    tip = p2
    b1 = (tip[0] - ux * size + px * size * 0.45,
          tip[1] - uy * size + py * size * 0.45)
    b2 = (tip[0] - ux * size - px * size * 0.45,
          tip[1] - uy * size - py * size * 0.45)
    dpg.draw_triangle(b1, b2, tip, color=col, fill=col, parent=dl)

# ─────────────────────────────────────────────────────────────────────────────
# PIDNode
# ─────────────────────────────────────────────────────────────────────────────
class PIDNode:
    PORT_R = 5.5

    def __init__(self, kind: str, x: float = 200, y: float = 200):
        self.id     = uuid.uuid4().hex[:8]
        self.kind   = kind
        self.x      = x
        self.y      = y
        self.w, self.h = SHAPE_SIZES[kind]
        self.rot    = 0.0
        self.fh     = False
        self.fv     = False
        # DPG handles
        self.dpg_node = None
        self.dl       = None
        self.port_attrs: dict[str, int | str] = {}

    @property
    def cx(self): return self.w / 2
    @property
    def cy(self): return self.h / 2

    def port_abs_local(self, port_name) -> tuple[float, float]:
        """Şekil-yerel (0,0 kökenli) port koordinatı."""
        for (pn, _, nx, ny) in PORT_DEFS[self.kind]:
            if pn == port_name:
                raw = [(nx * self.w, ny * self.h)]
                return T(raw, self.cx, self.cy, self.rot, self.fh, self.fv)[0]
        return (0.0, 0.0)

    def redraw(self):
        dl = self.dl
        dpg.delete_item(dl, children_only=True)
        x, y, w, h = 0, 0, self.w, self.h
        cx, cy = self.cx, self.cy
        fc = SHAPE_COL[self.kind]["fill"]
        sc = SHAPE_COL[self.kind]["stroke"]
        t  = lambda pts: T(pts, cx, cy, self.rot, self.fh, self.fv)

        # ── Şekil ──
        if self.kind == "turbine":
            m = h * 0.2
            poly = t([(x, y+m), (x+w, y), (x+w, y+h), (x, y+h-m)])
            dpg.draw_polygon(poly, color=sc, fill=fc, thickness=2, parent=dl)
            for frac in (0.3, 0.5, 0.7):
                bx = x + w * frac
                top = (bx, y + m * frac + 2)
                bot = (bx, y + h - m * frac - 2)
                dpg.draw_line(t([top])[0], t([bot])[0],
                              color=(*sc[:3], 110), thickness=1.5, parent=dl)
            dpg.draw_text(t([(cx - 4, cy + 5)])[0], "T", color=sc, size=16, parent=dl)

        elif self.kind == "compressor":
            m = h * 0.2
            poly = t([(x, y), (x+w, y+m), (x+w, y+h-m), (x, y+h)])
            dpg.draw_polygon(poly, color=sc, fill=fc, thickness=2, parent=dl)
            for frac in (0.3, 0.5, 0.7):
                bx = x + w * frac
                top = (bx, y + m * (1 - frac) + 2)
                bot = (bx, y + h - m * (1 - frac) - 2)
                dpg.draw_line(t([top])[0], t([bot])[0],
                              color=(*sc[:3], 110), thickness=1.5, parent=dl)
            dpg.draw_text(t([(cx - 4, cy + 5)])[0], "C", color=sc, size=16, parent=dl)

        elif self.kind in ("heater", "cooler"):
            poly = t([(x, y), (x+w, y), (x+w, y+h), (x, y+h)])
            dpg.draw_polygon(poly, color=sc, fill=fc, thickness=2, parent=dl)
            zz = t(zigzag(x, y, w, h))
            dpg.draw_polyline(zz, color=sc, thickness=2, parent=dl)
            lbl = "HTR" if self.kind == "heater" else "CLR"
            dpg.draw_text(t([(cx - 12, y + h - 16)])[0], lbl, color=sc, size=11, parent=dl)

        elif self.kind == "recuperator":
            poly = t([(x, y), (x+w, y), (x+w, y+h), (x, y+h)])
            dpg.draw_polygon(poly, color=sc, fill=fc, thickness=2, parent=dl)
            # Sıcak akış — kırmızı
            hp1 = t([(x + 8, y + h * 0.65)])[0]
            hp2 = t([(x + w - 8, y + h * 0.35)])[0]
            dpg.draw_line(hp1, hp2, color=(248, 113, 113, 220), thickness=2, parent=dl)
            draw_arrowhead(dl, hp1, hp2, (248, 113, 113, 220))
            # Soğuk akış — mavi
            cp1 = t([(x + w - 8, y + h * 0.65)])[0]
            cp2 = t([(x + 8, y + h * 0.35)])[0]
            dpg.draw_line(cp1, cp2, color=(96, 165, 250, 220), thickness=2, parent=dl)
            draw_arrowhead(dl, cp1, cp2, (96, 165, 250, 220))
            dpg.draw_text(t([(cx - 7, cy + 4)])[0], "HX", color=sc, size=12, parent=dl)

        elif self.kind == "splitter":
            r = min(w, h) / 2 - 4
            circ = t(circle_pts(cx, cy, r))
            dpg.draw_polygon(circ, color=sc, fill=fc, thickness=2, parent=dl)
            ct = t([(cx, cy)])[0]
            dpg.draw_line(t([(x + 4, cy)])[0],          ct, color=sc, thickness=1.5, parent=dl)
            dpg.draw_line(ct, t([(x + w - 4, cy - h*0.25)])[0], color=sc, thickness=1.5, parent=dl)
            dpg.draw_line(ct, t([(x + w - 4, cy + h*0.25)])[0], color=sc, thickness=1.5, parent=dl)
            dpg.draw_text(t([(cx - 4, cy + 4)])[0], "S", color=sc, size=14, parent=dl)

        elif self.kind == "mixer":
            r = min(w, h) / 2 - 4
            circ = t(circle_pts(cx, cy, r))
            dpg.draw_polygon(circ, color=sc, fill=fc, thickness=2, parent=dl)
            ct = t([(cx, cy)])[0]
            dpg.draw_line(t([(x + 4, cy - h*0.25)])[0], ct, color=sc, thickness=1.5, parent=dl)
            dpg.draw_line(t([(x + 4, cy + h*0.25)])[0], ct, color=sc, thickness=1.5, parent=dl)
            dpg.draw_line(ct, t([(x + w - 4, cy)])[0],      color=sc, thickness=1.5, parent=dl)
            dpg.draw_text(t([(cx - 4, cy + 4)])[0], "M", color=sc, size=14, parent=dl)

        # ── Portlar ──
        for (pname, ptype, nx, ny) in PORT_DEFS[self.kind]:
            raw = (nx * w, ny * h)
            pt  = T([raw], cx, cy, self.rot, self.fh, self.fv)[0]
            col = PORT_OUT if ptype == "out" else PORT_IN
            dpg.draw_circle(pt, self.PORT_R,
                            color=col, fill=(*col[:3], 170),
                            thickness=1.5, parent=dl)


# ─────────────────────────────────────────────────────────────────────────────
# PIDEdge
# ─────────────────────────────────────────────────────────────────────────────
class PIDEdge:
    def __init__(self, fn, fp, tn, tp):
        self.id = uuid.uuid4().hex[:8]
        self.fn, self.fp = fn, fp   # from node id, from port name
        self.tn, self.tp = tn, tp   # to node id, to port name


# ─────────────────────────────────────────────────────────────────────────────
# Ana Uygulama
# ─────────────────────────────────────────────────────────────────────────────
class PIDApp:
    W, H    = 1440, 900
    ALPHA0  = (0, 0, 0, 0)

    def __init__(self):
        self.nodes: dict[str, PIDNode] = {}
        self.edges: list[PIDEdge]      = []
        self.ctx_id: str | None        = None
        self.wiring                    = False
        self.wire_fn: str | None       = None
        self.wire_fp: str | None       = None
        self._build()

    # ── Tema ──────────────────────────────────────────────────────────────────
    def _invis_node_theme(self):
        with dpg.theme() as t:
            with dpg.theme_component(dpg.mvNode):
                for col in (dpg.mvNodeCol_NodeBackground,
                            dpg.mvNodeCol_NodeBackgroundHovered,
                            dpg.mvNodeCol_NodeBackgroundSelected,
                            dpg.mvNodeCol_TitleBar,
                            dpg.mvNodeCol_TitleBarHovered,
                            dpg.mvNodeCol_TitleBarSelected,
                            dpg.mvNodeCol_NodeOutline):
                    dpg.add_theme_color(col, self.ALPHA0,
                                        category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_style(dpg.mvNodeStyleVar_NodePadding, 0, 0,
                                    category=dpg.mvThemeCat_Nodes)
        return t

    def _editor_theme(self):
        with dpg.theme() as t:
            with dpg.theme_component(dpg.mvNodeEditor):
                dpg.add_theme_color(dpg.mvNodeCol_GridBackground,
                                    (10, 15, 26, 255), category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_GridLine,
                                    (20, 40, 65, 140), category=dpg.mvThemeCat_Nodes)
                for lc in (dpg.mvNodeCol_Link, dpg.mvNodeCol_LinkHovered,
                           dpg.mvNodeCol_LinkSelected):
                    dpg.add_theme_color(lc, self.ALPHA0, category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_Pin,
                                    (250, 204, 21, 180), category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_color(dpg.mvNodeCol_PinHovered,
                                    (250, 204, 21, 255), category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_style(dpg.mvNodeStyleVar_PinCircleRadius, 1,
                                    category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_style(dpg.mvNodeStyleVar_GridSpacing, 20,
                                    category=dpg.mvThemeCat_Nodes)
                dpg.add_theme_style(dpg.mvNodeStyleVar_NodeBorderThickness, 0,
                                    category=dpg.mvThemeCat_Nodes)
        return t

    # ── Arayüz ────────────────────────────────────────────────────────────────
    def _build(self):
        dpg.create_context()
        dpg.create_viewport(title="P&ID Node Editörü",
                            width=self.W, height=self.H,
                            clear_color=BG)

        self._node_theme   = self._invis_node_theme()
        self._editor_th    = self._editor_theme()

        with dpg.window(tag="win", no_title_bar=True, no_resize=True,
                        no_move=True, no_scrollbar=True,
                        width=self.W, height=self.H, pos=(0, 0)):
            self._menubar()
            self._editor_area()
            self._statusbar()
            self._ctx_menu()

        dpg.set_primary_window("win", True)
        dpg.set_viewport_resize_callback(self._on_resize)

        with dpg.handler_registry():
            dpg.add_mouse_move_handler(callback=self._tick)
            dpg.add_mouse_click_handler(button=1, callback=self._right_click)
            dpg.add_key_press_handler(key=dpg.mvKey_Escape,
                                      callback=self._cancel_wire)

        dpg.setup_dearpygui()
        dpg.show_viewport()

    def _menubar(self):
        with dpg.menu_bar():
            with dpg.menu(label="  ⊕ Makine Elemanı Ekle  "):
                items = [
                    ("turbine",     "🔶  Turbine  — Türbin"),
                    ("compressor",  "🔷  Compressor  — Kompresör"),
                    ("heater",      "🔴  Heater  — Isıtıcı"),
                    ("cooler",      "🔵  Cooler  — Soğutucu"),
                    ("recuperator", "🟣  Recuperator  — Isı Geri Kazanım"),
                    ("splitter",    "🟡  Splitter  — Bölücü"),
                    ("mixer",       "🟢  Mixer  — Karıştırıcı"),
                ]
                for kind, lbl in items:
                    dpg.add_menu_item(label=lbl,
                                      callback=lambda s, a, u: self._add_node(u),
                                      user_data=kind)

            with dpg.menu(label="  Dosya  "):
                dpg.add_menu_item(label="JSON Dışa Aktar (topology.json)",
                                  callback=self._export)
                dpg.add_menu_item(label="Tüm Tuvali Temizle",
                                  callback=self._clear)

            with dpg.menu(label="  Yardım  "):
                for txt in ("Sol tık sürükle  →  taşı",
                            "Out porta tıkla →  kablo başlat",
                            "In porta tıkla  →  kabloyu bitir",
                            "ESC             →  kablo iptal",
                            "Sağ tık         →  dönüştür / sil"):
                    dpg.add_menu_item(label=f"  {txt}", enabled=False)

    def _editor_area(self):
        dpg.add_node_editor(
            tag="ne",
            callback=self._link_cb,
            delink_callback=None,
            minimap=True,
            minimap_location=dpg.mvNodeMiniMap_Location_BottomRight,
            height=self.H - 56,
        )
        dpg.bind_item_theme("ne", self._editor_th)

        # Üst çizim katmanı (kenarlar + wire preview)
        dpg.add_drawlist(tag="wdl",
                         width=self.W, height=self.H - 56,
                         parent="win", pos=(0, 24))

    def _statusbar(self):
        dpg.add_text(tag="sb",
                     default_value="  Hazır",
                     parent="win",
                     color=(71, 85, 105, 255))

    def _ctx_menu(self):
        with dpg.window(tag="ctx", show=False, no_title_bar=True,
                        no_resize=True, popup=True, width=190):
            dpg.add_text("  Dönüştür", color=(100, 116, 139, 255))
            dpg.add_separator()
            acts = [
                ("↻  90° Saat Yönü",     "rcw"),
                ("↺  90° Saat Karşı",    "rccw"),
                ("⇄  Yatay Aynala",      "fh"),
                ("⇅  Dikey Aynala",      "fv"),
            ]
            for lbl, a in acts:
                dpg.add_menu_item(label=lbl,
                                  callback=lambda s, ap, u: self._ctx_act(u),
                                  user_data=a)
            dpg.add_separator()
            dpg.add_menu_item(label="⧉  Kopyala",
                              callback=lambda: self._ctx_act("copy"))
            dpg.add_menu_item(label="✕  Sil",
                              callback=lambda: self._ctx_act("del"))

    # ── Node ekleme ───────────────────────────────────────────────────────────
    def _add_node(self, kind: str, x=None, y=None) -> PIDNode:
        n = PIDNode(kind, x or 150 + len(self.nodes) * 25,
                          y or 160 + len(self.nodes) * 18)
        with dpg.node(label="", parent="ne",
                      pos=(n.x, n.y), tag=f"dn_{n.id}"):
            dpg.bind_item_theme(f"dn_{n.id}", self._node_theme)
            n.dpg_node = f"dn_{n.id}"

            with dpg.node_attribute(attribute_type=dpg.mvNode_Attr_Static):
                dl = dpg.add_drawlist(width=n.w, height=n.h)
                n.dl = dl

            for (pname, ptype, _, _) in PORT_DEFS[kind]:
                attr_type = (dpg.mvNode_Attr_Output if ptype == "out"
                             else dpg.mvNode_Attr_Input)
                with dpg.node_attribute(
                    tag=f"at_{n.id}_{pname}",
                    attribute_type=attr_type,
                    shape=dpg.mvNode_PinShape_Circle,
                ):
                    n.port_attrs[pname] = f"at_{n.id}_{pname}"
                    dpg.add_text("", indent=0)

        n.redraw()
        self.nodes[n.id] = n
        self._sb(f"{kind} eklendi  [{n.id}]")
        return n

    # ── DPG link callback (bezier gizli, kendi kenarımıza çeviriyoruz) ────────
    def _link_cb(self, sender, app_data):
        a1, a2 = str(app_data[0]), str(app_data[1])
        # tag formatı: at_<nodeid>_<portname>
        def parse(t):
            _, nid, *rest = t.split("_", 2)
            return nid, rest[0] if rest else ""
        try:
            fn, fp = parse(a1)
            tn, tp = parse(a2)
        except Exception:
            return
        edge = PIDEdge(fn, fp, tn, tp)
        self.edges.append(edge)
        self._sb(f"Bağlantı: {fn}.{fp} → {tn}.{tp}")

    # ── Port tıklama (manuel kablo) ───────────────────────────────────────────
    def _start_wire(self, node_id, port_name):
        self.wiring  = True
        self.wire_fn = node_id
        self.wire_fp = port_name
        self._sb(f"Kablo: {node_id}.{port_name} → hedef In portuna tıkla  |  ESC iptal")

    def _finish_wire(self, node_id, port_name):
        if node_id != self.wire_fn:
            e = PIDEdge(self.wire_fn, self.wire_fp, node_id, port_name)
            self.edges.append(e)
            self._sb(f"Bağlantı kuruldu: {self.wire_fn}.{self.wire_fp} → {node_id}.{port_name}")
        self._cancel_wire()

    def _cancel_wire(self):
        self.wiring  = False
        self.wire_fn = None
        self.wire_fp = None

    # ── Render döngüsü: ortogonal kenarlar ────────────────────────────────────
    def _tick(self):
        dl = "wdl"
        dpg.delete_item(dl, children_only=True)

        # Node editor ekran ofseti
        try:
            ne_rect = dpg.get_item_rect_min("ne")
            ox, oy  = ne_rect[0], ne_rect[1]
        except Exception:
            ox, oy = 0, 24

        def screen_port(node: PIDNode, pname: str):
            try:
                npos = dpg.get_item_pos(node.dpg_node)   # ne-canvas koordinatları
            except Exception:
                npos = (node.x, node.y)
            lx, ly = node.port_abs_local(pname)
            return (ox + npos[0] + lx, oy + npos[1] + ly)

        # ── Tamamlanmış kenarlar ──
        for edge in self.edges:
            nf = self.nodes.get(edge.fn)
            nt = self.nodes.get(edge.tn)
            if not nf or not nt:
                continue
            try:
                p1 = screen_port(nf, edge.fp)
                p2 = screen_port(nt, edge.tp)
            except Exception:
                continue
            pts = ortho(p1, p2)
            dpg.draw_polyline(pts, color=WIRE_COL, thickness=2, parent=dl)
            # Ok ucu (orta segmente)
            mi = len(pts) // 2
            if mi > 0:
                draw_arrowhead(dl, pts[mi - 1], pts[mi], ARROW_COL)

        # ── Wire preview ──
        if self.wiring and self.wire_fn:
            nf = self.nodes.get(self.wire_fn)
            if nf:
                try:
                    p1 = screen_port(nf, self.wire_fp)
                    mx, my = dpg.get_mouse_pos(local=False)
                    pts = ortho(p1, (mx, my))
                    dpg.draw_polyline(pts, color=WIRE_PREV,
                                      thickness=2, parent=dl)
                except Exception:
                    pass

    # ── Sağ tık ──────────────────────────────────────────────────────────────
    def _right_click(self):
        mx, my = dpg.get_mouse_pos(local=False)
        try:
            ne_rect = dpg.get_item_rect_min("ne")
            ox, oy  = ne_rect[0], ne_rect[1]
        except Exception:
            ox, oy = 0, 24

        for nid, node in self.nodes.items():
            try:
                npos = dpg.get_item_pos(node.dpg_node)
            except Exception:
                continue
            sx, sy = ox + npos[0], oy + npos[1]
            if sx <= mx <= sx + node.w and sy <= my <= sy + node.h:
                self.ctx_id = nid
                dpg.configure_item("ctx", show=True, pos=(mx - 10, my - 10))
                return

    def _ctx_act(self, action: str):
        nid = self.ctx_id
        if not nid or nid not in self.nodes:
            return
        n = self.nodes[nid]

        if action == "rcw":
            n.rot = (n.rot + 90) % 360; n.redraw()
        elif action == "rccw":
            n.rot = (n.rot - 90) % 360; n.redraw()
        elif action == "fh":
            n.fh = not n.fh; n.redraw()
        elif action == "fv":
            n.fv = not n.fv; n.redraw()
        elif action == "copy":
            nn = self._add_node(n.kind, n.x + 40, n.y + 40)
            nn.rot, nn.fh, nn.fv = n.rot, n.fh, n.fv
            nn.redraw()
        elif action == "del":
            self.edges = [e for e in self.edges
                          if e.fn != nid and e.tn != nid]
            try: dpg.delete_item(n.dpg_node)
            except Exception: pass
            del self.nodes[nid]
            self._sb(f"Silindi: {nid}")
        self.ctx_id = None

    # ── JSON dışa aktarma ─────────────────────────────────────────────────────
    def _export(self):
        try:
            ne_rect = dpg.get_item_rect_min("ne")
        except Exception:
            ne_rect = (0, 24)

        data = {"nodes": [], "edges": []}
        for nid, n in self.nodes.items():
            try:
                pos = dpg.get_item_pos(n.dpg_node)
            except Exception:
                pos = (n.x, n.y)
            data["nodes"].append({
                "id": nid, "type": n.kind,
                "x": pos[0], "y": pos[1],
                "transform": {"rotate": n.rot, "flip_h": n.fh, "flip_v": n.fv},
            })
        for e in self.edges:
            data["edges"].append({
                "id": e.id,
                "from": {"node": e.fn, "port": e.fp},
                "to":   {"node": e.tn, "port": e.tp},
            })
        path = "topology.json"
        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)
        print(json.dumps(data, indent=2, ensure_ascii=False))
        self._sb(f"Kaydedildi → {path}  ({len(data['nodes'])} node, {len(data['edges'])} kenar)")

    def _clear(self):
        for n in list(self.nodes.values()):
            try: dpg.delete_item(n.dpg_node)
            except Exception: pass
        self.nodes.clear()
        self.edges.clear()
        self._cancel_wire()
        self._sb("Tuval temizlendi")

    def _sb(self, msg: str):
        try:
            dpg.set_value("sb",
                f"  {msg}  ·  ESC: kablo iptal  ·  Sağ Tık: dönüştür/sil")
        except Exception:
            pass

    def _on_resize(self):
        w, h = dpg.get_viewport_width(), dpg.get_viewport_height()
        dpg.configure_item("win",  width=w, height=h)
        dpg.configure_item("ne",   height=h - 56)
        dpg.configure_item("wdl",  width=w, height=h - 56)

    # ── Ana döngü ─────────────────────────────────────────────────────────────
    def run(self):
        while dpg.is_dearpygui_running():
            self._tick()
            dpg.render_dearpygui_frame()
        dpg.destroy_context()


# ─────────────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    PIDApp().run()