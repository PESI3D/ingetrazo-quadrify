# SPDX-License-Identifier: GPL-3.0-or-later
# Copyright (c) 2026 Peter Müller (PESI3D) — https://pesi3d.de
"""Quadrify — turn pairs of triangles into four-sided faces.

Imported meshes (OBJ, STL, DAE, glTF, terrain exports …) often arrive fully
triangulated: every rectangle is two triangles with a diagonal across it.
Quadrify finds the best partner for each triangle and removes the diagonal
between them, in the spirit of «Quadrify All / Quadrify Selection» in other
3D programs. (IngeTrazo is not affiliated with Autodesk; 3ds Max is named only
to describe the function.)

- Select faces and run Extensions ▸ Quadrify ▸ Quadrify… (or right-click ▸
  Quadrify…). With nothing selected the whole mesh being edited is used —
  open a group first to quadrify inside it.
- A FLAT pair (both triangles in one plane, within «Planar tolerance») becomes
  one real quad face; paint and tag go with it.
- A CURVED pair (sphere, terrain) cannot be one face in IngeTrazo — faces are
  planar. Its diagonal is softened (or hidden), so the pair reads as a quad
  while the surface keeps its shape. «Keep triangles» leaves curved pairs
  alone.
- «Max face angle» = how much two triangles may fold against each other,
  «Max shape angle» = how far each corner of the quad may stray from 90°.
  The best-shaped quads are made first.
- «Select Edges» selects the diagonals that would go, without changing the
  model.

Extensions ▸ Quadrify ▸ Grid Remesh… rebuilds a height-field surface
(terrain) as a regular grid instead: quads everywhere inside, border cells cut
to the outline («Clip to outline») or left out («Whole cells only»). Heights
are sampled from the old surface; bent cells are two triangles with a soft
diagonal. Spacing, Grid angle (Auto = along the site), Preview.

One undo step each. The dialogs are non-modal: orbit, pan and zoom while the preview
shows every diagonal that goes — green: becomes a quad face, orange dashed:
softened diagonal.
"""
from __future__ import annotations

import math

KEY = "quadrify_tool"
VERSION = "1.3"
TITLE = "Quadrify"

_TEXTS = {
    "de": {
        "Quadrify": "In Vierecke umwandeln",
        "Quadrify…": "In Vierecke umwandeln…",
        "Turn pairs of triangles into four-sided faces.":
            "Wandelt Dreieckspaare in viereckige Flächen um.",
        "Scope": "Bereich",
        "Selection: {t} triangles of {f} faces":
            "Auswahl: {t} Dreiecke von {f} Flächen",
        "Whole mesh: {t} triangles of {f} faces":
            "Ganzes Netz: {t} Dreiecke von {f} Flächen",
        "Follow selection": "Auswahl folgen",
        "↻ Read selection": "↻ Auswahl lesen",
        "Max face angle": "Max. Flächenwinkel",
        "Max shape angle": "Max. Formwinkel",
        "Planar tolerance": "Planar-Toleranz",
        "Surface": "Fläche",
        "Auto (terrain or any shape)": "Auto (Gelände oder beliebige Form)",
        "Height field (terrain, seen from above)": "Höhenfeld (Gelände, von oben)",
        "Any shape (surface patches)": "Beliebige Form (Flächenstücke)",
        "Any shape — quads only (retopology)": "Beliebige Form — nur Vierecke (Retopologie)",
        "Quads only: {n} patches": "Nur Vierecke: {n} Flächenstücke",
        "Spacing too small: about {n} quads — the limit is {m}. Choose a larger spacing.":
            "Rasterweite zu klein: etwa {n} Vierecke — die Grenze ist {m}. Bitte eine größere Rasterweite wählen.",
        "About {n} quads — this takes a while (up to minutes). Choose a larger spacing, or compute anyway.":
            "Etwa {n} Vierecke — das dauert eine Weile (bis zu Minuten). Größere Rasterweite wählen oder trotzdem berechnen.",
        "Compute anyway (about {n} quads)": "Trotzdem berechnen (etwa {n} Vierecke)",
        "{n} patches as a cut grid (holes or more than four corners)":
            "{n} Stücke als beschnittenes Raster (Löcher oder mehr als vier Ecken)",
        "Height field: the grid is laid seen from above (terrain). Any shape: quads only, like a retopology — the surface is cut into patches at its hard edges and every patch gets a structured quad grid that ends exactly on its outline (four corners: a grid; round: an O-grid; a tube: rings). Auto picks.":
            "Höhenfeld: das Raster wird von oben gesehen gelegt (Gelände). Beliebige Form: nur Vierecke wie bei einer Retopologie — die Fläche wird an harten Kanten in Stücke geteilt, jedes Stück bekommt ein geordnetes Viereck-Raster, das genau an seinem Umriss endet (vier Ecken: Raster; rund: O-Raster; Röhre: Ringe). Auto wählt selbst.",
        "Any shape: {n} surface patches, each gridded in its own directions":
            "Beliebige Form: {n} Flächenstücke, jedes in seinen eigenen Richtungen gerastert",
        "Height field: the grid is laid seen from above (terrain). Any shape: the surface is cut into patches at hard edges, each patch is unfolded flat, gridded in its own directions and laid back — ducts, lofts, walls, boxes. Auto picks.":
            "Höhenfeld: das Raster wird von oben gesehen gelegt (Gelände). Beliebige Form: die Fläche wird an harten Kanten in Stücke geteilt, jedes Stück flach abgewickelt, in seinen eigenen Richtungen gerastert und zurückgelegt — Kanäle, Übergänge, Wände, Kisten. Auto wählt selbst.",
        "Curved quads": "Gekrümmte Vierecke",
        "Soften diagonal": "Diagonale weich",
        "Hide diagonal": "Diagonale ausblenden",
        "Keep triangles": "Dreiecke behalten",
        "Compare materials": "Materialien vergleichen",
        "Back to the default settings.": "Zurück zu den Standardwerten.",
        "Preview": "Vorschau",
        "Result": "Ergebnis",
        "{q} quad faces · {s} curved quads · {t} triangles left":
            "{q} Viereckflächen · {s} gekrümmte Vierecke · {t} Dreiecke bleiben",
        "Grid Remesh": "Raster-Neuvernetzung",
        "Grid Remesh…": "Raster-Neuvernetzung…",
        "Rebuild a terrain surface as a regular grid of quads.":
            "Baut eine Geländefläche als regelmäßiges Viereck-Raster neu auf.",
        "Spacing": "Rasterweite",
        "Size of one grid quad.": "Größe eines Raster-Vierecks.",
        "Grid angle": "Rasterwinkel",
        "Auto": "Auto",
        "Turn the grid along the site (smallest box around it).":
            "Raster entlang des Geländes drehen (kleinstes umschließendes Rechteck).",
        "Border": "Rand",
        "Clip to outline": "Am Umriss beschneiden",
        "Whole cells only": "Nur ganze Zellen",
        "Cells flatter than this become one real face.":
            "Flachere Zellen werden zu einer echten Fläche.",
        "Remesh": "Neu vernetzen",
        "{q} quads · {b} border pieces": "{q} Vierecke · {b} Randstücke",
        "Grid Remesh: {q} quads, {b} border pieces":
            "Raster-Neuvernetzung: {q} Vierecke, {b} Randstücke",
        "No faces in the scope.": "Keine Flächen im Bereich.",
        "Spacing too small: more than {n} cells.":
            "Rasterweite zu klein: mehr als {n} Zellen.",
        "The faces are vertical — nothing to see from above.":
            "Die Flächen sind senkrecht — von oben ist nichts zu sehen.",
        "Warning: the surface overlaps itself seen from above (steep or vertical parts). Grid Remesh needs a height field such as terrain.":
            "Achtung: Die Fläche überlappt sich von oben gesehen (steile oder senkrechte Teile). Die Raster-Neuvernetzung braucht ein Höhenfeld wie ein Gelände.",
        "Select Edges": "Kanten auswählen",
        "Select Triangles Left": "Restdreiecke auswählen",
        "{n} triangle(s) left selected": "{n} Restdreieck(e) ausgewählt",
        "Tip: raise «Max shape angle» (up to 90°) for irregular meshes such as terrain.":
            "Tipp: «Max. Formwinkel» erhöhen (bis 90°) bei unregelmäßigen Netzen wie Gelände.",
        "Cancel": "Abbrechen",
        "{n} diagonal(s) selected": "{n} Diagonale(n) ausgewählt",
        "Quadrified: {q} quad faces, {s} curved quads":
            "Umgewandelt: {q} Viereckflächen, {s} gekrümmte Vierecke",
        "Nothing to quadrify: no suitable pair of triangles.":
            "Nichts umzuwandeln: kein passendes Dreieckspaar.",
        "No triangles in the scope.": "Keine Dreiecke im Bereich.",
        "Two triangles may fold this much against each other.":
            "So weit dürfen zwei Dreiecke gegeneinander geknickt sein.",
        "How far each corner of the quad may stray from 90°.":
            "So weit darf jede Ecke des Vierecks von 90° abweichen.",
        "Pairs flatter than this become one real face.":
            "Flachere Paare werden zu einer echten Fläche.",
        "Only pair triangles with the same paint.":
            "Nur Dreiecke mit gleichem Material paaren.",
    },
    "es": {
        "Quadrify": "Cuadrangular",
        "Quadrify…": "Cuadrangular…",
        "Turn pairs of triangles into four-sided faces.":
            "Convierte pares de triángulos en caras de cuatro lados.",
        "Scope": "Alcance",
        "Selection: {t} triangles of {f} faces":
            "Selección: {t} triángulos de {f} caras",
        "Whole mesh: {t} triangles of {f} faces":
            "Malla completa: {t} triángulos de {f} caras",
        "Follow selection": "Seguir la selección",
        "↻ Read selection": "↻ Leer selección",
        "Max face angle": "Ángulo máx. de caras",
        "Max shape angle": "Ángulo máx. de forma",
        "Planar tolerance": "Tolerancia plana",
        "Curved quads": "Cuadriláteros curvos",
        "Soften diagonal": "Suavizar diagonal",
        "Hide diagonal": "Ocultar diagonal",
        "Keep triangles": "Mantener triángulos",
        "Compare materials": "Comparar materiales",
        "Back to the default settings.": "Volver a los valores por defecto.",
        "Preview": "Vista previa",
        "Result": "Resultado",
        "{q} quad faces · {s} curved quads · {t} triangles left":
            "{q} caras cuadriláteras · {s} cuadriláteros curvos · quedan {t} triángulos",
        "Grid Remesh": "Remallado en cuadrícula",
        "Grid Remesh…": "Remallado en cuadrícula…",
        "Rebuild a terrain surface as a regular grid of quads.":
            "Reconstruye una superficie de terreno como cuadrícula regular de cuadriláteros.",
        "Spacing": "Separación",
        "Size of one grid quad.": "Tamaño de un cuadrilátero de la cuadrícula.",
        "Grid angle": "Ángulo de la cuadrícula",
        "Auto": "Auto",
        "Turn the grid along the site (smallest box around it).":
            "Girar la cuadrícula según el terreno (rectángulo mínimo que lo envuelve).",
        "Border": "Borde",
        "Clip to outline": "Recortar al contorno",
        "Whole cells only": "Solo celdas enteras",
        "Cells flatter than this become one real face.":
            "Las celdas más planas que esto se vuelven una cara real.",
        "Remesh": "Remallar",
        "{q} quads · {b} border pieces": "{q} cuadriláteros · {b} piezas de borde",
        "Grid Remesh: {q} quads, {b} border pieces":
            "Remallado: {q} cuadriláteros, {b} piezas de borde",
        "No faces in the scope.": "No hay caras en el alcance.",
        "Spacing too small: more than {n} cells.":
            "Separación demasiado pequeña: más de {n} celdas.",
        "The faces are vertical — nothing to see from above.":
            "Las caras son verticales: no se ven desde arriba.",
        "Warning: the surface overlaps itself seen from above (steep or vertical parts). Grid Remesh needs a height field such as terrain.":
            "Atención: la superficie se superpone vista desde arriba (partes empinadas o verticales). El remallado necesita un campo de alturas como un terreno.",
        "Select Edges": "Seleccionar aristas",
        "Select Triangles Left": "Seleccionar triángulos restantes",
        "{n} triangle(s) left selected": "{n} triángulo(s) restante(s) seleccionado(s)",
        "Tip: raise «Max shape angle» (up to 90°) for irregular meshes such as terrain.":
            "Consejo: suba «Ángulo máx. de forma» (hasta 90°) en mallas irregulares como terrenos.",
        "Cancel": "Cancelar",
        "{n} diagonal(s) selected": "{n} diagonal(es) seleccionada(s)",
        "Quadrified: {q} quad faces, {s} curved quads":
            "Cuadrangulado: {q} caras cuadriláteras, {s} cuadriláteros curvos",
        "Nothing to quadrify: no suitable pair of triangles.":
            "Nada que cuadrangular: ningún par de triángulos adecuado.",
        "No triangles in the scope.": "No hay triángulos en el alcance.",
        "Two triangles may fold this much against each other.":
            "Cuánto pueden plegarse dos triángulos entre sí.",
        "How far each corner of the quad may stray from 90°.":
            "Cuánto puede apartarse de 90° cada esquina del cuadrilátero.",
        "Pairs flatter than this become one real face.":
            "Los pares más planos que esto se vuelven una cara real.",
        "Only pair triangles with the same paint.":
            "Solo emparejar triángulos con la misma pintura.",
    },
}

DEFAULTS = {
    "face_angle": 40.0,     # degrees — fold between the two triangles
    "shape_angle": 40.0,    # degrees — corner deviation from 90°
    "planar_tol": 0.5,      # degrees — up to this a pair becomes ONE face
    "curved": "soft",       # "soft" | "hidden" | "keep"
    "materials": True,
    "maximize": True,     # re-pair along alternating paths → fewest triangles
    "preview": True,
    "follow": True,
}

#: IngeTrazo's own coplanar test is a normal dot of 0.999 (≈ 2.56°); a real
#: quad face must stay inside it, or the core would treat it as bent.
_PLANAR_MAX = 2.5

_PAINT_KEYS = ("color", "mat", "texture", "opacity", "back")


def _tr(text: str, **kw) -> str:
    """``text`` in the interface language, with ``{n}``-style fields."""
    try:
        from core.i18n import current_language
        lang = current_language()
    except Exception:  # noqa: BLE001
        lang = "en"
    out = _TEXTS.get(lang, {}).get(text, text)
    return out.format(**kw) if kw else out


def load_params() -> dict:
    p = dict(DEFAULTS)
    try:
        from PySide6.QtCore import QSettings
        st = QSettings()
        for k, v in DEFAULTS.items():
            if isinstance(v, bool):
                p[k] = st.value(f"plugins/{KEY}/{k}", v, type=bool)
            elif isinstance(v, float):
                p[k] = float(st.value(f"plugins/{KEY}/{k}", v))
            else:
                p[k] = str(st.value(f"plugins/{KEY}/{k}", v))
    except Exception:  # noqa: BLE001
        pass
    if p["curved"] not in ("soft", "hidden", "keep"):
        p["curved"] = "soft"
    p["planar_tol"] = min(max(p["planar_tol"], 0.0), _PLANAR_MAX)
    return p


def save_params(p: dict) -> None:
    try:
        from PySide6.QtCore import QSettings
        st = QSettings()
        for k in DEFAULTS:
            st.setValue(f"plugins/{KEY}/{k}", p[k])
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# 1. Geometry — pairing. Works on IngeTrazo's Mesh (shared Vertex objects,
#    Face.loop, Edge.faces radial lists).
# ---------------------------------------------------------------------------

def _v(p):
    return (p.x(), p.y(), p.z())


def _sub(a, b):
    return (a[0] - b[0], a[1] - b[1], a[2] - b[2])


def _dot(a, b):
    return a[0] * b[0] + a[1] * b[1] + a[2] * b[2]


def _cross(a, b):
    return (a[1] * b[2] - a[2] * b[1],
            a[2] * b[0] - a[0] * b[2],
            a[0] * b[1] - a[1] * b[0])


def _norm(a):
    return math.sqrt(_dot(a, a))


def _tri_normal(loop):
    p0, p1, p2 = (_v(v.position) for v in loop)
    n = _cross(_sub(p1, p0), _sub(p2, p0))
    ln = _norm(n)
    if ln < 1e-12:
        return None
    return (n[0] / ln, n[1] / ln, n[2] / ln)


def _paint(face):
    a = face.attrs or {}
    return tuple(repr(a.get(k)) for k in _PAINT_KEYS)


def _splice(loop_a, loop_b, u, w):
    """Quad loop from two triangles sharing edge {u, w}; the shared edge runs
    one way in A and the other way in B. ``None`` if it does not."""
    na, nb = len(loop_a), len(loop_b)
    ia = next((i for i in range(na)
               if {loop_a[i], loop_a[(i + 1) % na]} == {u, w}), None)
    ib = next((i for i in range(nb)
               if {loop_b[i], loop_b[(i + 1) % nb]} == {u, w}), None)
    if ia is None or ib is None:
        return None
    s, t = loop_a[ia], loop_a[(ia + 1) % na]
    if not (loop_b[ib] is t and loop_b[(ib + 1) % nb] is s):
        return None
    sa = (ia + 1) % na
    a_path = loop_a[sa:] + loop_a[:sa]          # t … s
    sb = (ib + 1) % nb
    b_path = loop_b[sb:] + loop_b[:sb]          # s … t
    quad = a_path[:-1] + b_path[:-1]
    if len({id(v) for v in quad}) != 4:
        return None
    return quad


def evaluate_pair(f0, f1, edge, p):
    """Score the quad that removing ``edge`` would make, or ``None`` when the
    pair is not allowed. Returns ``(score, quad_loop, dihedral, flipped)``."""
    n0 = _tri_normal(f0.loop)
    n1 = _tri_normal(f1.loop)
    if n0 is None or n1 is None:
        return None
    flipped = False
    quad = _splice(f0.loop, f1.loop, edge.v0, edge.v1)
    if quad is None:                             # opposite winding
        quad = _splice(f0.loop, list(reversed(f1.loop)), edge.v0, edge.v1)
        if quad is None:
            return None
        flipped = True
        n1 = (-n1[0], -n1[1], -n1[2])
    dihedral = math.degrees(math.acos(max(-1.0, min(1.0, _dot(n0, n1)))))
    if dihedral > p["face_angle"] + 1e-9:
        return None
    nav = (n0[0] + n1[0], n0[1] + n1[1], n0[2] + n1[2])
    pts = [_v(v.position) for v in quad]
    worst = 0.0
    for i in range(4):
        prev, cur, nxt = pts[i - 1], pts[i], pts[(i + 1) % 4]
        d1, d2 = _sub(cur, prev), _sub(nxt, cur)
        l1, l2 = _norm(d1), _norm(d2)
        if l1 < 1e-9 or l2 < 1e-9:
            return None
        # Convex: every corner turns the same way as the surface normal.
        if _dot(_cross(d1, d2), nav) <= 1e-12 * l1 * l2:
            return None
        a, b = _sub(prev, cur), d2
        ang = math.degrees(math.acos(max(-1.0, min(1.0, _dot(a, b) / (l1 * l2)))))
        worst = max(worst, abs(ang - 90.0))
    if worst > p["shape_angle"] + 1e-9:
        return None
    return worst + dihedral, quad, dihedral, flipped


def scope_faces(scene):
    """``(faces, from_selection)``: the selected faces of the mesh being
    edited, or all its faces when none are selected."""
    from core.mesh import Face
    mesh = scene.mesh
    live = set(mesh.faces)
    sel = [f for f in scene.selection if isinstance(f, Face) and f in live]
    if sel:
        return sel, True
    return list(mesh.faces), False


def plan(mesh, faces, p) -> dict:
    """Which diagonals go. ``{"pairs": [(edge, f0, f1, quad, kind, flipped)],
    "tris": n}`` — ``kind`` "merge" (one real face) or "soft"/"hidden"."""
    tris = [f for f in faces if len(f.loop) == 3 and not f.hole_loops]
    tset = set(tris)
    planar_tol = min(p["planar_tol"], _PLANAR_MAX)
    cands = []
    seen = set()
    for f in tris:
        lp = f.loop
        for i in range(3):
            e = mesh.find_edge(lp[i], lp[(i + 1) % 3])
            if e is None or id(e) in seen:
                continue
            seen.add(id(e))
            if len(e.faces) != 2:
                continue
            f0, f1 = e.faces
            if f0 is f1 or f0 not in tset or f1 not in tset:
                continue
            if p["materials"] and _paint(f0) != _paint(f1):
                continue
            ev = evaluate_pair(f0, f1, e, p)
            if ev is None:
                continue
            score, quad, dihedral, flipped = ev
            flat = dihedral <= planar_tol + 1e-9
            if not flat and p["curved"] == "keep":
                continue
            kind = "merge" if flat else p["curved"]
            # Flat pairs first at equal shape: they make real faces.
            cands.append((score, 0 if flat else 1, len(cands),
                          (e, f0, f1, quad, kind, flipped)))
    cands.sort(key=lambda c: (c[0], c[1], c[2]))
    # 1. Greedy, best quad first.
    mate = {}
    for *_k, pr in cands:
        f0, f1 = pr[1], pr[2]
        if f0 in mate or f1 in mate:
            continue
        mate[f0] = f1
        mate[f1] = f0
    # 2. Rescue the triangles greedy left over: re-pair along alternating
    #    paths (a leftover takes a neighbour, whose partner moves on …) so
    #    every allowed pair counts, not just the first-come ones.
    if p.get("maximize", True):
        _augment(cands, mate)
    data = {}
    for *_k, pr in cands:
        data[(id(pr[1]), id(pr[2]))] = pr
    pairs = []
    done = set()
    for f, g in mate.items():
        if f in done:
            continue
        done.add(f)
        done.add(g)
        pr = data.get((id(f), id(g))) or data.get((id(g), id(f)))
        if pr is not None:
            pairs.append(pr)
    left = [f for f in tris if f not in mate]
    return {"pairs": pairs, "tris": len(tris), "left": left}


def _augment(cands, mate, limit: int = 4000) -> int:
    """Grow the matching ``mate`` (triangle → partner) with augmenting
    paths over the allowed pairs ``cands``. Breadth-first from each
    unmatched triangle, best-scored neighbours first, at most ``limit``
    triangles per search. Returns how many pairs were added."""
    from collections import deque
    adj = {}
    for *_k, pr in cands:                       # already sorted by score
        f0, f1 = pr[1], pr[2]
        adj.setdefault(f0, []).append(f1)
        adj.setdefault(f1, []).append(f0)
    added = 0
    progress = True
    while progress:
        progress = False
        for root in list(adj):
            if root in mate:
                continue
            parent = {root: None}
            queue = deque([root])
            found = None
            while queue and found is None and len(parent) < limit:
                u = queue.popleft()
                for v in adj[u]:
                    if v in parent:
                        continue
                    if v not in mate:
                        parent[v] = u
                        found = v
                        break
                    w = mate[v]
                    if w in parent:
                        continue
                    parent[v] = u
                    parent[w] = v
                    queue.append(w)
            if found is None:
                continue
            v = found                            # flip the path
            while v is not None:
                u = parent[v]
                nxt = parent[u]
                mate[v] = u
                mate[u] = v
                v = nxt
            added += 1
            progress = True
    return added


def apply_plan(mesh, pairs) -> dict:
    """Carry out ``pairs`` (from :func:`plan`) on ``mesh`` in place — run it
    under an undo snapshot. Returns counts and the new quad faces.

    Done in bulk: ``Mesh.remove_face``/``remove_edge`` each scan the whole
    face/edge list, which made a 45 000-triangle terrain take minutes; here
    the radial lists are edited per pair and the lists rebuilt once."""
    from core.mesh import Face
    merged, softened, new_faces = 0, 0, []
    live_faces = set(mesh.faces)
    dead_faces, dead_edges = set(), set()
    for e, f0, f1, quad, kind, flipped in pairs:
        if (f0 not in live_faces or f1 not in live_faces
                or f0 in dead_faces or f1 in dead_faces or e in dead_edges):
            continue
        if kind == "merge":
            src = f0 if (f0.attrs or flipped or not f1.attrs) else f1
            for f in (f0, f1):
                lp = f.loop
                for i in range(len(lp)):
                    edge = mesh.find_edge(lp[i], lp[(i + 1) % len(lp)])
                    if edge is not None and f in edge.faces:
                        edge.faces.remove(f)
                dead_faces.add(f)
            if not e.faces:
                e.v0.edges.discard(e)
                e.v1.edges.discard(e)
                dead_edges.add(e)
            nf = Face(list(quad))
            nf.attrs = dict(src.attrs or {})
            nf.interior = bool(getattr(f0, "interior", False)
                               and getattr(f1, "interior", False))
            for i in range(4):
                edge = mesh._link_edge(quad[i], quad[(i + 1) % 4])
                edge.faces.append(nf)
            new_faces.append(nf)
            merged += 1
        else:
            if kind == "hidden":
                e.hidden = True
            else:
                e.soft = True
            softened += 1
    if dead_faces:
        mesh.faces[:] = [f for f in mesh.faces if f not in dead_faces]
    mesh.faces.extend(new_faces)
    if dead_edges:
        mesh.edges[:] = [e for e in mesh.edges if e not in dead_edges]
    if merged or softened:
        if hasattr(mesh, "_chunk_dirty"):
            mesh._chunk_dirty = True
        if hasattr(mesh, "_mut_serial"):
            mesh._mut_serial += 1
    return {"merged": merged, "softened": softened, "faces": new_faces}


# ---------------------------------------------------------------------------
# 2. Commands — one undo step.
# ---------------------------------------------------------------------------

def run_quadrify(viewport, faces, p, from_selection) -> dict | None:
    from core.history import SnapshotImport
    scene = viewport.scene
    live = set(scene.mesh.faces)
    faces = [f for f in faces if f in live]
    pl = plan(scene.mesh, faces, p)
    if not pl["tris"]:
        viewport.flash_status(_tr("No triangles in the scope."), 4000)
        return None
    if not pl["pairs"]:
        viewport.flash_status(
            _tr("Nothing to quadrify: no suitable pair of triangles."), 4000)
        return None
    result = {}
    gone = {f for pr in pl["pairs"] if pr[4] == "merge" for f in (pr[1], pr[2])}
    keep = [f for f in faces if f not in gone]

    def mutate(sc):
        result.update(apply_plan(sc.mesh, pl["pairs"]))

    viewport.history.execute(SnapshotImport(mutate))
    viewport.notify_scene_changed()
    if from_selection:
        try:
            now = set(scene.mesh.faces)
            scene.select([f for f in keep + result.get("faces", []) if f in now])
        except Exception:  # noqa: BLE001
            pass
    viewport.flash_status(_tr("Quadrified: {q} quad faces, {s} curved quads",
                              q=result.get("merged", 0),
                              s=result.get("softened", 0)), 5000)
    viewport.update()
    return result


# ---------------------------------------------------------------------------
# 3. Dialog (non-modal) + preview overlay.
# ---------------------------------------------------------------------------

_STATE = {"dialog": None, "preview": None,
          "grid_dialog": None, "grid_preview": None}


def _draw_preview(viewport, painter) -> None:
    data = _STATE.get("preview")
    if not data or _STATE.get("dialog") is None:
        return
    import numpy as np
    from PySide6.QtCore import QLineF, Qt
    from PySide6.QtGui import QColor, QPen

    for segs, colour, style, width in (
            (data["merge"], QColor(0, 190, 90, 230), Qt.SolidLine, 2),
            (data["soft"], QColor(240, 140, 0, 230), Qt.DashLine, 2)):
        if not segs:
            continue
        arr = np.asarray(segs, dtype=float).reshape(-1, 3)
        px, py, front = viewport.world_to_pixels(arr)
        pen = QPen(colour, width, style)
        pen.setCosmetic(True)
        painter.setPen(pen)
        lines = [QLineF(px[k], py[k], px[k + 1], py[k + 1])
                 for k in range(0, len(arr), 2) if front[k] and front[k + 1]]
        if lines:
            painter.drawLines(lines)


def _live_mixin():
    """The PESI3D Live Preview, shared by the Quadrify and Grid Remesh
    dialogs: a checkable «Preview» (green «● Live Preview ON»), «Reset»,
    «OK», «Cancel» and a banner. Switched on, the result stands in the model
    as ONE undo step (``SnapshotImport``) and is rebuilt on every change —
    undone first, so the plan always sees the source as it was; OK keeps
    it, Cancel takes it back. The dialog's own changes to the selection and
    the mesh are remembered, so «Follow selection» never reads them as the
    user's."""
    from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton

    class LiveMixin:
        _PV_ON = ("QPushButton { background: #2e9e4f; color: white; "
                  "font-weight: bold; border: 1px solid #1f7a3a; "
                  "border-radius: 3px; padding: 3px 8px; }")
        _BANNER = {"live": "background: #1f5f33; color: #e8ffe9;",
                   "busy": "background: #7a5a12; color: #fff6e0;",
                   "paused": "background: #5c4a1a; color: #ffe9b8;",
                   "error": "background: #7a1f1f; color: #ffecec;"}

        def _live_build(self, lay):
            self._pv_cmd = None
            self._pv_key = None
            self._pv_src_sel = []
            self._kept = False
            self.pv_lbl = QLabel(self)
            self.pv_lbl.setWordWrap(True)
            self.pv_lbl.setVisible(False)
            lay.addWidget(self.pv_lbl)
            row = QHBoxLayout()
            self.preview = QPushButton("Preview", self)
            self.preview.setCheckable(True)
            self.reset_btn = QPushButton("Reset", self)
            self.reset_btn.setToolTip(_tr("Back to the default settings."))
            self.b_ok = QPushButton("OK", self)
            self.b_ok.setDefault(True)
            self.cancel_btn = QPushButton("Cancel", self)
            row.addWidget(self.preview)
            row.addWidget(self.reset_btn)
            row.addStretch(1)
            row.addWidget(self.b_ok)
            row.addWidget(self.cancel_btn)
            lay.addLayout(row)
            self.preview.toggled.connect(self._live_toggled)
            self.reset_btn.clicked.connect(self._reset)
            self.b_ok.clicked.connect(self._apply)
            self.cancel_btn.clicked.connect(self.close)
            self._live_style(False)

        def _banner(self, kind, text):
            self.pv_lbl.setStyleSheet(self._BANNER[kind]
                                      + " padding: 6px 8px; border-radius: 3px;")
            self.pv_lbl.setText(text)
            self.pv_lbl.setVisible(True)

        def _live_style(self, on):
            if on:
                self.preview.setText("● Live Preview ON")
                self.preview.setStyleSheet(self._PV_ON)
                self.preview.setToolTip("The preview follows every change by "
                                        "itself — click to switch it off.")
            else:
                self.preview.setText("Preview")
                self.preview.setStyleSheet("")
                self.preview.setToolTip("Show the result in the model; it then "
                                        "follows every change by itself.")
                self.pv_lbl.setVisible(False)

        def _live_toggled(self, on):
            self._live_style(on)
            self._timer.stop()
            self._refresh()

        def _live_quiet(self):
            """Our own change of selection / mesh: not the user's."""
            self._sig = self._selection_sig()
            self._serial = self._mesh_serial()

        def _live_undo(self, restore=True):
            """Take the preview back (if it is still the last step). The
            source's selection comes back unless ``restore`` is False."""
            cmd, self._pv_cmd = self._pv_cmd, None
            self._pv_key = None
            if cmd is None:
                return
            vp = self.viewport
            stack = getattr(vp.history, "undo_stack", [])
            if stack and stack[-1] is cmd:
                vp.history.undo()
                vp.notify_scene_changed()
                if restore:
                    sc = vp.scene
                    alive = set(sc.mesh.faces) | set(sc.mesh.edges)
                    sc.selection.clear()
                    sc.selection.update(x for x in self._pv_src_sel if x in alive)
            self._live_quiet()
            vp.update()

        def _live_apply(self, mutate, key, select_fn):
            """Run ``mutate(scene)`` as the preview step; ``select_fn(result)``
            → what to select (the result faces)."""
            from core.history import SnapshotImport
            vp = self.viewport
            self._pv_src_sel = list(vp.scene.selection)
            result = {}

            def run(sc):
                result.update(mutate(sc) or {})

            cmd = SnapshotImport(run)
            vp.history.execute(cmd)
            err = getattr(vp.history, "last_error", None)
            if err:
                self._banner("error", f"Preview failed: {str(err).split(': ', 1)[-1]}")
                self._live_quiet()
                return None
            vp.notify_scene_changed()
            self._pv_cmd, self._pv_key = cmd, key
            try:
                now = set(vp.scene.mesh.faces)
                vp.scene.select([f for f in select_fn(result) if f in now])
            except Exception:  # noqa: BLE001
                pass
            self._live_quiet()
            vp.update()
            return result

        def _live_keep(self, key) -> bool:
            """OK with an up-to-date preview: it IS the result (one undo
            step already)."""
            cmd = self._pv_cmd
            stack = getattr(self.viewport.history, "undo_stack", [])
            if cmd is None or self._pv_key != key or not stack or stack[-1] is not cmd:
                return False
            self._pv_cmd = None
            self._kept = True
            return True

    return LiveMixin


def _make_dialog_class():
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                                   QDoubleSpinBox, QFormLayout, QHBoxLayout,
                                   QLabel, QPushButton, QVBoxLayout)

    Live = _live_mixin()

    class QuadrifyDialog(Live, QDialog):
        def __init__(self, viewport):
            super().__init__(viewport.window())
            self.viewport = viewport
            self.p = load_params()
            self.setWindowTitle(f"{_tr(TITLE)} {VERSION}")
            self.setModal(False)
            self.setAttribute(Qt.WA_DeleteOnClose, True)
            self.faces, self.from_sel = scope_faces(viewport.scene)
            self._plan = None
            self._sig = self._selection_sig()
            self._serial = self._mesh_serial()
            self._build()
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(300)
            self._timer.timeout.connect(self._refresh)
            self._poll = QTimer(self)
            self._poll.setInterval(400)
            self._poll.timeout.connect(self._poll_state)
            self._poll.start()
            if self.p["preview"]:
                self.preview.setChecked(True)     # → the first preview
            else:
                self._refresh()

        # ---- UI ------------------------------------------------------------
        def _spin(self, lo, hi, dec, val, tip):
            U = _pesi3d_units()
            if U:                          # degrees, shown in document units
                s = U["Angle"](self, lo, hi, decimals=dec)
                s.setValue(val)
                s.setToolTip(tip)
                s.valueChanged.connect(self._changed)
                return s
            s = QDoubleSpinBox(self)
            s.setRange(lo, hi)
            s.setDecimals(dec)
            s.setSingleStep(1.0 if dec == 0 else 0.1)
            s.setSuffix(" °")
            s.setValue(val)
            s.setToolTip(tip)
            s.valueChanged.connect(self._changed)
            return s

        def _build(self):
            lay = QVBoxLayout(self)
            form = QFormLayout()
            self.scope = QLabel(self)
            form.addRow(_tr("Scope"), self.scope)
            srow = QHBoxLayout()
            self.follow = QCheckBox(_tr("Follow selection"), self)
            self.follow.setChecked(self.p["follow"])
            self.follow.toggled.connect(self._follow_toggled)
            self.b_read = QPushButton(_tr("↻ Read selection"), self)
            self.b_read.clicked.connect(lambda: self._read_selection(only_if_faces=True))
            srow.addWidget(self.follow)
            srow.addWidget(self.b_read)
            srow.addStretch(1)
            form.addRow("", srow)
            self.s_face = self._spin(0, 90, 1, self.p["face_angle"],
                                     _tr("Two triangles may fold this much against each other."))
            form.addRow(_tr("Max face angle"), self.s_face)
            self.s_shape = self._spin(0, 90, 1, self.p["shape_angle"],
                                      _tr("How far each corner of the quad may stray from 90°."))
            form.addRow(_tr("Max shape angle"), self.s_shape)
            self.s_planar = self._spin(0, _PLANAR_MAX, 2, self.p["planar_tol"],
                                       _tr("Pairs flatter than this become one real face."))
            form.addRow(_tr("Planar tolerance"), self.s_planar)
            self.c_curved = QComboBox(self)
            for key, label in (("soft", "Soften diagonal"),
                               ("hidden", "Hide diagonal"),
                               ("keep", "Keep triangles")):
                self.c_curved.addItem(_tr(label), key)
            self.c_curved.setCurrentIndex(
                max(0, self.c_curved.findData(self.p["curved"])))
            self.c_curved.currentIndexChanged.connect(self._changed)
            form.addRow(_tr("Curved quads"), self.c_curved)
            self.c_mat = QCheckBox(_tr("Compare materials"), self)
            self.c_mat.setToolTip(_tr("Only pair triangles with the same paint."))
            self.c_mat.setChecked(self.p["materials"])
            self.c_mat.toggled.connect(self._changed)
            form.addRow("", self.c_mat)
            self.result = QLabel(self)
            self.result.setWordWrap(True)
            form.addRow(_tr("Result"), self.result)
            lay.addLayout(form)
            brow = QHBoxLayout()
            self.b_sel = QPushButton(_tr("Select Edges"), self)
            self.b_sel.clicked.connect(self._select_edges)
            brow.addWidget(self.b_sel)
            self.b_left = QPushButton(_tr("Select Triangles Left"), self)
            self.b_left.clicked.connect(self._select_left)
            brow.addWidget(self.b_left)
            brow.addStretch(1)
            lay.addLayout(brow)
            self._live_build(lay)

        def _params(self):
            p = dict(self.p)
            p["face_angle"] = self.s_face.value()
            p["shape_angle"] = self.s_shape.value()
            p["planar_tol"] = self.s_planar.value()
            p["curved"] = self.c_curved.currentData()
            p["materials"] = self.c_mat.isChecked()
            p["preview"] = self.preview.isChecked()
            p["follow"] = self.follow.isChecked()
            return p

        def _state_key(self, p):
            return (tuple(id(f) for f in self.faces), round(p["face_angle"], 6),
                    round(p["shape_angle"], 6), round(p["planar_tol"], 6),
                    p["curved"], p["materials"], p.get("maximize"))

        def _changed(self, *_a):
            if self.preview.isChecked():
                self._banner("busy", "⟳ Updating the preview…")
            self._timer.start()

        def _reset(self):
            d = DEFAULTS
            for w in (self.s_face, self.s_shape, self.s_planar, self.c_curved, self.c_mat):
                w.blockSignals(True)
            self.s_face.setValue(d["face_angle"])
            self.s_shape.setValue(d["shape_angle"])
            self.s_planar.setValue(d["planar_tol"])
            self.c_curved.setCurrentIndex(max(0, self.c_curved.findData(d["curved"])))
            self.c_mat.setChecked(d["materials"])
            for w in (self.s_face, self.s_shape, self.s_planar, self.c_curved, self.c_mat):
                w.blockSignals(False)
            self._changed()

        # ---- selection / document following --------------------------------
        def _selection_sig(self):
            try:
                return frozenset(id(e) for e in self.viewport.scene.selection)
            except Exception:  # noqa: BLE001
                return frozenset()

        def _mesh_serial(self):
            m = self.viewport.scene.mesh
            return (id(m), getattr(m, "_mut_serial", 0), len(m.faces))

        def _poll_state(self):
            serial = self._mesh_serial()
            if serial != self._serial:            # edit, undo, group opened
                self._serial = serial
                self._read_selection(only_if_faces=True)
                return
            if not self.follow.isChecked():
                return
            sig = self._selection_sig()
            if sig != self._sig:
                self._sig = sig
                self._read_selection(only_if_faces=True)

        def _follow_toggled(self, on):
            if on:
                self._sig = self._selection_sig()
                self._read_selection()

        def _read_selection(self, only_if_faces=False):
            """Faces in the selection → they are the scope; an empty selection
            → the whole mesh. A selection of other things (the diagonals
            «Select Edges» picked, a group) leaves the scope as it is."""
            from core.mesh import Face
            sc = self.viewport.scene
            sel = list(sc.selection)
            if only_if_faces and sel and not any(isinstance(x, Face) for x in sel):
                return
            if self._pv_cmd is not None:
                # the source as it was, with the user's new selection on it
                self._live_undo(restore=False)
                alive = set(sc.mesh.faces) | set(sc.mesh.edges)
                sc.selection.clear()
                sc.selection.update(x for x in sel if x in alive)
                self._live_quiet()
            self.faces, self.from_sel = scope_faces(sc)
            self._refresh()

        # ---- plan + preview ----------------------------------------------------
        def _refresh(self):
            self._live_undo()
            p = self._params()
            mesh = self.viewport.scene.mesh
            live = set(mesh.faces)
            self.faces = [f for f in self.faces if f in live]
            if not self.from_sel and not self.faces:
                self.faces = list(mesh.faces)
            pl = plan(mesh, self.faces, p)
            self._plan = pl
            n_tri = pl["tris"]
            key = ("Selection: {t} triangles of {f} faces" if self.from_sel
                   else "Whole mesh: {t} triangles of {f} faces")
            self.scope.setText(_tr(key, t=n_tri, f=len(self.faces)))
            q = sum(1 for pr in pl["pairs"] if pr[4] == "merge")
            s = len(pl["pairs"]) - q
            left = n_tri - 2 * len(pl["pairs"])
            self.result.setText(_tr(
                "{q} quad faces · {s} curved quads · {t} triangles left",
                q=q, s=s, t=left))
            self.b_ok.setEnabled(bool(pl["pairs"]))
            self.b_sel.setEnabled(bool(pl["pairs"]))
            self.b_left.setEnabled(bool(pl["left"]))
            text = self.result.text()
            if left and p["shape_angle"] < 89.9 and left * 10 > n_tri:
                text += "\n" + _tr("Tip: raise «Max shape angle» (up to 90°) "
                                    "for irregular meshes such as terrain.")
            self.result.setText(text)
            _STATE["preview"] = None
            if p["preview"] and pl["pairs"]:
                pairs = pl["pairs"]
                gone = {f for pr in pairs if pr[4] == "merge" for f in (pr[1], pr[2])}
                keep = [f for f in self.faces if f not in gone] if self.from_sel else []
                res = self._live_apply(
                    lambda sc: apply_plan(sc.mesh, pairs), self._state_key(p),
                    lambda r: keep + (r.get("faces", []) if self.from_sel else []))
                if res is not None:
                    self._banner("live", f"● <b>LIVE PREVIEW</b> — {res.get('merged', 0)} "
                                 f"quad faces, {res.get('softened', 0)} curved quads · "
                                 f"changes apply instantly")
            elif p["preview"]:
                self._banner("live", "● <b>LIVE PREVIEW</b> — nothing to quadrify "
                             "in the scope")
            else:
                # preview off: the plan drawn over the model
                merge, soft = [], []
                for e, *_r, kind, _fl in pl["pairs"]:
                    seg = (_v(e.v0.position), _v(e.v1.position))
                    (merge if kind == "merge" else soft).append(seg)
                _STATE["preview"] = {"merge": merge, "soft": soft}
            self.viewport.update()

        # ---- actions -------------------------------------------------------------
        def _select_edges(self):
            if self.preview.isChecked():
                self.preview.setChecked(False)     # the diagonals are merged away
            if not self._plan or not self._plan["pairs"]:
                return
            edges = [pr[0] for pr in self._plan["pairs"]]
            self.viewport.scene.select(edges)
            self._sig = self._selection_sig()
            self.viewport.flash_status(
                _tr("{n} diagonal(s) selected", n=len(edges)), 4000)
            self.viewport.update()

        def _select_left(self):
            if not self._plan or not self._plan["left"]:
                return
            left = self._plan["left"]
            self.viewport.scene.select(left)
            self._sig = self._selection_sig()
            self.viewport.flash_status(
                _tr("{n} triangle(s) left selected", n=len(left)), 4000)
            self.viewport.update()

        def _apply(self):
            p = self._params()
            self.p = p
            save_params(p)
            if self._live_keep(self._state_key(p)):
                pl = self._plan or {"pairs": []}
                q = sum(1 for pr in pl["pairs"] if pr[4] == "merge")
                self.viewport.flash_status(_tr(
                    "Quadrified: {q} quad faces, {s} curved quads",
                    q=q, s=len(pl["pairs"]) - q), 5000)
                _STATE["preview"] = None
                self.close()
                return
            self._live_undo()
            faces, from_sel = list(self.faces), self.from_sel
            _STATE["preview"] = None
            self._kept = True                  # nothing left to take back
            self.close()
            run_quadrify(self.viewport, faces, p, from_sel)

        def closeEvent(self, ev):  # noqa: N802 - Qt naming
            try:
                self._poll.stop()
                self._timer.stop()
                self.p = self._params()
                save_params(self.p)
                if not self._kept:
                    self._live_undo()          # Cancel: the preview goes
            except Exception:  # noqa: BLE001
                pass
            _STATE["preview"] = None
            if _STATE.get("dialog") is self:
                _STATE["dialog"] = None
            try:
                self.viewport.update()
            except RuntimeError:  # the window is already gone (app closing)
                pass
            super().closeEvent(ev)

    return QuadrifyDialog


_DIALOG_CLASS = None


def open_dialog(viewport):
    global _DIALOG_CLASS
    old = _STATE.get("dialog")
    if old is not None:
        try:
            old.close()
        except Exception:  # noqa: BLE001
            pass
    if _DIALOG_CLASS is None:
        _DIALOG_CLASS = _make_dialog_class()
    dlg = _DIALOG_CLASS(viewport)
    _STATE["dialog"] = dlg
    dlg.show()
    dlg.raise_()
    return dlg


# ---------------------------------------------------------------------------
# 4. Grid Remesh — rebuild a height-field surface (terrain) as a regular
#    grid: quads inside, cells cut to the outline at the border. Unlike the
#    pairing above this does not keep the old vertices; it samples the
#    surface's heights at the grid points.
# ---------------------------------------------------------------------------

GRID_DEFAULTS = {
    "spacing_m": 0.0,      # 0 = automatic from the mesh's edge length
    "angle": 0.0,          # degrees, grid rotation about Z
    "clip": True,          # cut border cells to the outline (else whole cells)
    "planar_tol": 0.5,
    "preview": True,
    "follow": True,
    "mode": "auto",        # auto | height (terrain) | surface (any shape)
}

#: Above this many cells the grid is refused (spacing far too small).
_GRID_MAX_CELLS = 400_000
#: From about this many quads the dialog asks first (it takes a while).
_GRID_WARN_QUADS = 15_000


def estimate_quads(faces, spacing):
    """About how many quads a spacing gives: area / spacing² (fast)."""
    if spacing <= 0:
        return 0
    try:
        area = sum(f.area() for f in faces)
    except Exception:  # noqa: BLE001
        return 0
    return int(round(area / (spacing * spacing)))


def load_grid_params() -> dict:
    p = dict(GRID_DEFAULTS)
    try:
        from PySide6.QtCore import QSettings
        st = QSettings()
        for k, v in GRID_DEFAULTS.items():
            if isinstance(v, bool):
                p[k] = st.value(f"plugins/{KEY}/grid_{k}", v, type=bool)
            elif isinstance(v, str):
                p[k] = str(st.value(f"plugins/{KEY}/grid_{k}", v))
            else:
                p[k] = float(st.value(f"plugins/{KEY}/grid_{k}", v))
    except Exception:  # noqa: BLE001
        pass
    p["planar_tol"] = min(max(p["planar_tol"], 0.0), _PLANAR_MAX)
    if p.get("mode") not in ("auto", "height", "surface"):
        p["mode"] = "auto"
    return p


def save_grid_params(p: dict) -> None:
    try:
        from PySide6.QtCore import QSettings
        st = QSettings()
        for k in GRID_DEFAULTS:
            st.setValue(f"plugins/{KEY}/grid_{k}", p[k])
    except Exception:  # noqa: BLE001
        pass


def _rot(theta):
    c, s = math.cos(theta), math.sin(theta)

    def to_uv(x, y):
        return x * c + y * s, -x * s + y * c

    def to_xy(u, v):
        return u * c - v * s, u * s + v * c
    return to_uv, to_xy


class _Sampler:
    """Heights of a set of triangles seen from above, by bucket lookup.

    ``tris`` = ``[((u, v, z), (u, v, z), (u, v, z)), …]`` in grid frame."""

    def __init__(self, tris):
        self.tris = tris
        us = [p[0] for t in tris for p in t]
        vs = [p[1] for t in tris for p in t]
        self.u0, self.v0 = min(us), min(vs)
        span = max(max(us) - self.u0, max(vs) - self.v0, 1e-9)
        n = max(1, len(tris))
        self.cell = max(span / max(1.0, math.sqrt(n)), 1e-9)
        self.buckets = {}
        self.pre = []
        for idx, (a, b, c) in enumerate(tris):
            det = (b[1] - c[1]) * (a[0] - c[0]) + (c[0] - b[0]) * (a[1] - c[1])
            self.pre.append(det)
            if abs(det) < 1e-18:
                continue
            i0, j0 = self._ij(min(a[0], b[0], c[0]), min(a[1], b[1], c[1]))
            i1, j1 = self._ij(max(a[0], b[0], c[0]), max(a[1], b[1], c[1]))
            for i in range(i0, i1 + 1):
                for j in range(j0, j1 + 1):
                    self.buckets.setdefault((i, j), []).append(idx)
        self.eps_len = span * 1e-7

    def _ij(self, u, v):
        return (int(math.floor((u - self.u0) / self.cell)),
                int(math.floor((v - self.v0) / self.cell)))

    def _bary(self, idx, u, v):
        a, b, c = self.tris[idx]
        det = self.pre[idx]
        l1 = ((b[1] - c[1]) * (u - c[0]) + (c[0] - b[0]) * (v - c[1])) / det
        l2 = ((c[1] - a[1]) * (u - c[0]) + (a[0] - c[0]) * (v - c[1])) / det
        return l1, l2, 1.0 - l1 - l2

    def locate(self, u, v, eps=1e-9):
        """``(z, tri_index)`` of the triangle under (u, v), or ``None``."""
        best = None
        for idx in self.buckets.get(self._ij(u, v), ()):
            l1, l2, l3 = self._bary(idx, u, v)
            m = min(l1, l2, l3)
            if m >= -eps and (best is None or m > best[0]):
                a, b, c = self.tris[idx]
                best = (m, l1 * a[2] + l2 * b[2] + l3 * c[2], idx)
        return None if best is None else (best[1], best[2])

    def nearest(self, u, v):
        """Height at the closest point of the surface (outside it)."""
        i, j = self._ij(u, v)
        best = None
        for ring in range(0, 64):
            for di in range(-ring, ring + 1):
                for dj in range(-ring, ring + 1):
                    if max(abs(di), abs(dj)) != ring:
                        continue
                    for idx in self.buckets.get((i + di, j + dj), ()):
                        d2, z = self._closest(idx, u, v)
                        if best is None or d2 < best[0]:
                            best = (d2, z, idx)
            if best is not None and math.sqrt(best[0]) < (ring - 0.5) * self.cell:
                break
            if best is not None and ring > 2:
                break
        if best is None:
            return 0.0, 0
        return best[1], best[2]

    def _closest(self, idx, u, v):
        a, b, c = self.tris[idx]
        best = None
        for p, q in ((a, b), (b, c), (c, a)):
            dx, dy = q[0] - p[0], q[1] - p[1]
            ll = dx * dx + dy * dy
            t = 0.0 if ll < 1e-30 else max(0.0, min(1.0, ((u - p[0]) * dx + (v - p[1]) * dy) / ll))
            x, y = p[0] + t * dx, p[1] + t * dy
            d2 = (x - u) ** 2 + (y - v) ** 2
            if best is None or d2 < best[0]:
                best = (d2, p[2] + t * (q[2] - p[2]))
        return best

    def height(self, u, v):
        hit = self.locate(u, v, 1e-7)
        return hit if hit is not None else self.nearest(u, v)


def _source_tris(faces):
    """Triangles of ``faces`` (any polygon) as world points, with the face
    each came from, and whether most of them face down."""
    tris, owner, down, up = [], [], 0.0, 0.0
    for f in faces:
        try:
            n = f.normal()
            parts = f.triangulate(n)
        except Exception:  # noqa: BLE001
            continue
        a = f.area()
        if n.z() < 0:
            down += a
        else:
            up += a
        for t in parts:
            tris.append(tuple(_v(p) for p in t))
            owner.append(f)
    return tris, owner, down > up


def auto_spacing(faces) -> float:
    """A round spacing near the mean edge length of ``faces`` (metres)."""
    tot, n = 0.0, 0
    for f in faces:
        lp = f.loop
        for i in range(len(lp)):
            tot += (lp[(i + 1) % len(lp)].position - lp[i].position).length()
            n += 1
    if not n:
        return 1.0
    mean = tot / n
    exp = math.floor(math.log10(max(mean, 1e-9)))
    for m in (1, 2, 2.5, 5, 10):
        if m * 10 ** exp >= mean * 0.8:
            return m * 10 ** exp
    return 10 ** (exp + 1)


def auto_angle(faces) -> float:
    """Grid angle (degrees, −45…45) of the smallest rectangle around the
    plan view of ``faces`` — the grid then runs along the site."""
    pts = {(round(v.position.x(), 6), round(v.position.y(), 6))
           for f in faces for v in f.loop}
    pts = sorted(pts)
    if len(pts) < 3:
        return 0.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    best = (None, 0.0)
    for i in range(len(hull)):
        a, b = hull[i], hull[(i + 1) % len(hull)]
        th = math.atan2(b[1] - a[1], b[0] - a[0])
        to_uv, _ = _rot(th)
        uv = [to_uv(*p) for p in hull]
        area = ((max(p[0] for p in uv) - min(p[0] for p in uv))
                * (max(p[1] for p in uv) - min(p[1] for p in uv)))
        if best[0] is None or area < best[0]:
            best = (area, th)
    deg = math.degrees(best[1])
    deg = (deg + 45.0) % 90.0 - 45.0
    return round(deg, 2)


def _seg_box(p, q, box, eps):
    """Does segment p-q touch the box (u0, v0, u1, v1) (closed, +eps)?"""
    u0, v0, u1, v1 = box[0] - eps, box[1] - eps, box[2] + eps, box[3] + eps
    t0, t1 = 0.0, 1.0
    dx, dy = q[0] - p[0], q[1] - p[1]
    for pp, qq in ((-dx, p[0] - u0), (dx, u1 - p[0]),
                   (-dy, p[1] - v0), (dy, v1 - p[1])):
        if abs(pp) < 1e-30:
            if qq < 0:
                return False
        else:
            t = qq / pp
            if pp < 0:
                t0 = max(t0, t)
            else:
                t1 = min(t1, t)
            if t0 > t1:
                return False
    return True


def grid_plan(faces, p) -> dict:
    """Grid Remesh plan. ``p["mode"]``: ``height`` (seen from above, for
    terrain), ``surface`` (any shape, patch by patch) or ``auto`` (height
    field where the faces are one, else surface)."""
    mode = p.get("mode", "auto")
    if mode == "surface":
        return grid_plan_quads(faces, p)
    gp = _grid_plan_height(faces, p)
    if mode == "auto" and (gp["overlap"] or gp["error"] == "vertical"):
        return grid_plan_quads(faces, p)
    return gp


def _grid_plan_height(faces, p) -> dict:
    """The new grid faces for ``faces``: ``{"faces": [(loop, holes, src_face,
    split)], "full", "border", "overlap", "spacing", "error"}`` with points in
    world coordinates. ``split`` is ``None`` (one planar face) or the list of
    triangles a bent cell is cut into."""
    import manifold3d as mf

    out = {"faces": [], "full": 0, "border": 0, "overlap": False,
           "spacing": 0.0, "error": None}
    faces = list(faces)
    if not faces:
        out["error"] = "empty"
        return out
    s = p["spacing_m"] if p["spacing_m"] > 0 else auto_spacing(faces)
    out["spacing"] = s
    theta = math.radians(p["angle"])
    to_uv, to_xy = _rot(theta)
    tris_w, owner, down = _source_tris(faces)
    if not tris_w:
        out["error"] = "empty"
        return out
    tris = []
    contours = []
    proj = 0.0
    for t in tris_w:
        uvz = [(*to_uv(x, y), z) for x, y, z in t]
        tris.append(tuple(uvz))
        a, b, c = uvz
        cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if abs(cr) < 1e-14:
            continue
        proj += abs(cr) / 2
        contours.append([(a[0], a[1]), (b[0], b[1]), (c[0], c[1])] if cr > 0
                        else [(a[0], a[1]), (c[0], c[1]), (b[0], b[1])])
    foot = mf.CrossSection(contours, mf.FillRule.NonZero)
    if foot.is_empty():
        out["error"] = "vertical"
        return out
    if proj > foot.area() * 1.02:
        out["overlap"] = True             # not a height field everywhere
    sampler = _Sampler(tris)
    (umin, vmin), (umax, vmax) = _bounds(foot)
    i0, i1 = int(math.floor(umin / s)), int(math.ceil(umax / s))
    j0, j1 = int(math.floor(vmin / s)), int(math.ceil(vmax / s))
    if (i1 - i0) * (j1 - j0) > _GRID_MAX_CELLS:
        out["error"] = "too_many"
        return out

    # Cells the outline passes through.
    touched = set()
    eps = s * 1e-6
    for poly in foot.to_polygons():
        pts = [tuple(map(float, q)) for q in poly]
        for k in range(len(pts)):
            a, b = pts[k], pts[(k + 1) % len(pts)]
            ia = int(math.floor((min(a[0], b[0]) - eps) / s))
            ib = int(math.floor((max(a[0], b[0]) + eps) / s))
            ja = int(math.floor((min(a[1], b[1]) - eps) / s))
            jb = int(math.floor((max(a[1], b[1]) + eps) / s))
            for i in range(ia, ib + 1):
                for j in range(ja, jb + 1):
                    if (i, j) in touched:
                        continue
                    if _seg_box(a, b, (i * s, j * s, (i + 1) * s, (j + 1) * s), eps):
                        touched.add((i, j))

    zcache = {}

    def point(u, v):
        key = (round(u, 9), round(v, 9))
        z = zcache.get(key)
        if z is None:
            z = zcache[key] = sampler.height(u, v)[0]
        x, y = to_xy(u, v)
        return (x, y, z)

    def src_at(u, v):
        hit = sampler.locate(u, v, 1e-7)
        idx = hit[1] if hit is not None else sampler.nearest(u, v)[1]
        return owner[idx]

    tan_tol = math.tan(math.radians(p["planar_tol"]))
    square = mf.CrossSection.square([s, s])

    pending = []

    def emit(loop_uv, holes_uv):
        pending.append((loop_uv, holes_uv))

    def finish(loop_uv, holes_uv):
        if down:
            loop_uv = loop_uv[::-1]
            holes_uv = [h[::-1] for h in holes_uv]
        loop = [point(u, v) for u, v in loop_uv]
        holes = [[point(u, v) for u, v in h] for h in holes_uv]
        cu = sum(q[0] for q in loop_uv) / len(loop_uv)
        cv = sum(q[1] for q in loop_uv) / len(loop_uv)
        split = None
        if not _is_planar(loop, holes, tan_tol):
            split = _split_bent(loop, holes)
        out["faces"].append((loop, holes, src_at(cu, cv), split))

    for i in range(i0, i1):
        for j in range(j0, j1):
            u, v = i * s, j * s
            cell = [(u, v), (u + s, v), (u + s, v + s), (u, v + s)]
            if (i, j) not in touched:
                if sampler.locate(u + s / 2, v + s / 2, 0.0) is None:
                    continue
                emit(cell, [])
                out["full"] += 1
                continue
            if not p["clip"]:
                if all(sampler.locate(cu, cv, 1e-7) is not None for cu, cv in cell) \
                        and sampler.locate(u + s / 2, v + s / 2, 0.0) is not None:
                    emit(cell, [])
                    out["full"] += 1
                continue
            piece = square.translate([u, v]) ^ foot
            if piece.is_empty() or piece.area() < s * s * 1e-6:
                continue
            outers, holes = [], []
            for poly in piece.to_polygons():
                pts = [(float(q[0]), float(q[1])) for q in poly]
                if len(pts) < 3:
                    continue
                (outers if _area2(pts) > 0 else holes).append(pts)
            if len(outers) == 1 and not holes and _is_cell(outers[0], cell, eps):
                emit(cell, [])
                out["full"] += 1
                continue
            for o in outers:
                mine = [h for h in holes if _inside(h[0], o)]
                emit(o, mine)
                out["border"] += 1

    # Points the outline adds along a straight piece edge (the old mesh's
    # border vertices) make a quad a hexagon: drop them where no other piece
    # uses them — a point two pieces share must stay, or one of them would
    # end in a T-junction.
    def k_of(q):
        return (round(q[0] / s, 7), round(q[1] / s, 7))
    use = {}
    for loop_uv, holes_uv in pending:
        for lp in (loop_uv, *holes_uv):
            for q in lp:
                use[k_of(q)] = use.get(k_of(q), 0) + 1

    def clean(lp):
        pts = list(lp)
        changed = True
        while changed and len(pts) > 3:
            changed = False
            for k in range(len(pts)):
                a, b, c = pts[k - 1], pts[k], pts[(k + 1) % len(pts)]
                if use.get(k_of(b), 0) > 1:
                    continue
                cr = (b[0] - a[0]) * (c[1] - b[1]) - (b[1] - a[1]) * (c[0] - b[0])
                la = math.hypot(b[0] - a[0], b[1] - a[1])
                lc = math.hypot(c[0] - b[0], c[1] - b[1])
                if abs(cr) <= 1e-9 * max(la * lc, 1e-30) and \
                        (b[0] - a[0]) * (c[0] - b[0]) + (b[1] - a[1]) * (c[1] - b[1]) > 0:
                    del pts[k]
                    changed = True
                    break
        return pts

    for loop_uv, holes_uv in pending:
        finish(clean(loop_uv), [clean(h) for h in holes_uv])
    return out


# ---------------------------------------------------------------------------
# Grid Remesh on ANY surface (1.3)
# ---------------------------------------------------------------------------
# A height field (terrain) is gridded seen from above. Any other shape —
# a duct, a loft from a rectangle to a circle, walls, a box — is cut into
# surface patches («charts»): faces joined across soft edges (folds under
# SMOOTH_DEG), a hard edge or a turn of the surface beyond CHART_DEG starts
# a new patch. Each patch is UNFOLDED flat, triangle by triangle across its
# shared edges (exact for developable surfaces: planes, cylinders, cones,
# lofts between two outlines), gridded flat in its own directions (the
# smallest box around it, plus the Grid angle) and the grid laid back onto
# the surface. Where two patches meet, the points of the one are added to
# the edges of the other, so the result stays closed (no T-junctions).

SMOOTH_DEG = 35.0          # folds softer than this stay inside one patch
CHART_DEG = 100.0          # a patch never turns further than this


def _key3(p, q=1e-6):
    return (round(p[0] / q), round(p[1] / q), round(p[2] / q))


def _charts(tris, max_dev=CHART_DEG, smooth=SMOOTH_DEG):
    """Triangles (world points) → list of patches (lists of indices)."""
    n = len(tris)
    normals, areas = [], []
    for a, b, c in tris:
        u = _sub(b, a)
        w = _sub(c, a)
        cr = _cross(u, w)
        ln = math.sqrt(_dot(cr, cr))
        areas.append(ln / 2)
        normals.append((cr[0] / ln, cr[1] / ln, cr[2] / ln) if ln > 1e-18
                       else (0.0, 0.0, 1.0))
    edge_tris = {}
    for i, t in enumerate(tris):
        ks = [_key3(p) for p in t]
        for k in range(3):
            e = tuple(sorted((ks[k], ks[(k + 1) % 3])))
            edge_tris.setdefault(e, []).append(i)
    nb = [[] for _ in range(n)]
    for e, ts in edge_tris.items():
        if len(ts) == 2:
            i, j = ts
            nb[i].append((j, e))
            nb[j].append((i, e))
    cos_s = math.cos(math.radians(smooth))
    cos_d = -2.0 if max_dev >= 180.0 else math.cos(math.radians(max_dev))
    owner = [-1] * n
    charts = []
    order = sorted(range(n), key=lambda i: -areas[i])
    for seed in order:
        if owner[seed] >= 0:
            continue
        cid = len(charts)
        owner[seed] = cid
        members = [seed]
        n0 = normals[seed]
        stack = [seed]
        while stack:
            i = stack.pop()
            for j, _e in nb[i]:
                if owner[j] >= 0:
                    continue
                if _dot(normals[i], normals[j]) < cos_s:
                    continue                    # a hard edge
                if _dot(n0, normals[j]) < cos_d:
                    continue                    # the patch would turn too far
                owner[j] = cid
                members.append(j)
                stack.append(j)
        charts.append(members)
    return charts, nb, normals


def _unfold(tris, members, nb):
    """Lay the patch flat: ``{tri: ((u, v), (u, v), (u, v))}`` in the
    triangle's own vertex order, counter-clockwise (the face's front)."""
    mine = set(members)
    flat = {}
    seed = members[0]
    a, b, c = tris[seed]
    ab = math.dist(a, b)
    if ab < 1e-12:
        return flat
    ac = math.dist(a, c)
    bc = math.dist(b, c)
    x = (ab * ab + ac * ac - bc * bc) / (2 * ab)
    y = math.sqrt(max(ac * ac - x * x, 0.0))
    flat[seed] = ((0.0, 0.0), (ab, 0.0), (x, y))
    queue = [seed]
    qi = 0
    while qi < len(queue):
        i = queue[qi]
        qi += 1
        ti = tris[i]
        ki = [_key3(p) for p in ti]
        for j, e in nb[i]:
            if j not in mine or j in flat:
                continue
            tj = tris[j]
            kj = [_key3(p) for p in tj]
            # the shared edge in i's flat placement
            pi = {ki[k]: flat[i][k] for k in range(3)}
            sh = [k for k in range(3) if kj[k] in pi]
            if len(sh) != 2:
                continue
            r = 3 - sh[0] - sh[1]               # j's third vertex
            P = pi[kj[sh[0]]]
            Q = pi[kj[sh[1]]]
            dp = math.dist(tj[sh[0]], tj[r])
            dq = math.dist(tj[sh[1]], tj[r])
            L = math.dist(P, Q)
            if L < 1e-12:
                continue
            ex, ey = (Q[0] - P[0]) / L, (Q[1] - P[1]) / L
            xa = (dp * dp - dq * dq + L * L) / (2 * L)
            ya = math.sqrt(max(dp * dp - xa * xa, 0.0))
            best = None
            for sgn in (1.0, -1.0):
                R = (P[0] + ex * xa - ey * ya * sgn, P[1] + ey * xa + ex * ya * sgn)
                pts = [None, None, None]
                pts[sh[0]], pts[sh[1]], pts[r] = P, Q, R
                ar = ((pts[1][0] - pts[0][0]) * (pts[2][1] - pts[0][1])
                      - (pts[1][1] - pts[0][1]) * (pts[2][0] - pts[0][0]))
                if best is None or ar > best[0]:
                    best = (ar, tuple(pts))
            flat[j] = best[1]
            queue.append(j)
    return flat


def _min_box_angle(pts):
    """Angle (rad) of the smallest rectangle around 2D ``pts``."""
    pts = sorted(set((round(p[0], 6), round(p[1], 6)) for p in pts))
    if len(pts) < 3:
        return 0.0

    def cross(o, a, b):
        return (a[0] - o[0]) * (b[1] - o[1]) - (a[1] - o[1]) * (b[0] - o[0])
    lower, upper = [], []
    for p in pts:
        while len(lower) >= 2 and cross(lower[-2], lower[-1], p) <= 0:
            lower.pop()
        lower.append(p)
    for p in reversed(pts):
        while len(upper) >= 2 and cross(upper[-2], upper[-1], p) <= 0:
            upper.pop()
        upper.append(p)
    hull = lower[:-1] + upper[:-1]
    best = (None, 0.0)
    for i in range(len(hull)):
        a, b = hull[i], hull[(i + 1) % len(hull)]
        th = math.atan2(b[1] - a[1], b[0] - a[0])
        to_uv, _ = _rot(th)
        uv = [to_uv(*p) for p in hull]
        area = ((max(p[0] for p in uv) - min(p[0] for p in uv))
                * (max(p[1] for p in uv) - min(p[1] for p in uv)))
        if best[0] is None or area < best[0] - 1e-12:
            best = (area, th)
    return best[1]


def _grid_patch(tri_ids, flat, tris, owner, s, p, out):
    """Grid one unfolded patch; appends its faces to ``out``. Returns False
    when the unfolded patch overlaps itself (the caller splits it)."""
    import numpy as np
    import manifold3d as mf

    pts2 = [q for i in tri_ids for q in flat[i]]
    th = _min_box_angle(pts2) + math.radians(p["angle"])
    to_uv, _to_xy = _rot(th)
    stris, contours, proj = [], [], 0.0
    for i in tri_ids:
        f = flat[i]
        uv = [to_uv(*q) for q in f]
        w = tris[i]
        stris.append(tuple((uv[k][0], uv[k][1], np.asarray(w[k], float))
                           for k in range(3)))
        a, b, c = uv
        cr = (b[0] - a[0]) * (c[1] - a[1]) - (b[1] - a[1]) * (c[0] - a[0])
        if cr <= 1e-14:
            continue
        proj += cr / 2
        contours.append([a, b, c])
    if not contours:
        return True
    foot = mf.CrossSection(contours, mf.FillRule.NonZero)
    if foot.is_empty():
        return True
    if proj > foot.area() * 1.02 + 1e-9:
        return False                      # unfolded onto itself: split
    sampler = _Sampler(stris)
    (umin, vmin), (umax, vmax) = _bounds(foot)
    i0, i1 = int(math.floor(umin / s)), int(math.ceil(umax / s))
    j0, j1 = int(math.floor(vmin / s)), int(math.ceil(vmax / s))
    if (i1 - i0) * (j1 - j0) > _GRID_MAX_CELLS:
        out["error"] = "too_many"
        return True
    eps = s * 1e-6
    touched = set()
    for poly in foot.to_polygons():
        pp = [tuple(map(float, q)) for q in poly]
        for k in range(len(pp)):
            a, b = pp[k], pp[(k + 1) % len(pp)]
            ia = int(math.floor((min(a[0], b[0]) - eps) / s))
            ib = int(math.floor((max(a[0], b[0]) + eps) / s))
            ja = int(math.floor((min(a[1], b[1]) - eps) / s))
            jb = int(math.floor((max(a[1], b[1]) + eps) / s))
            for i in range(ia, ib + 1):
                for j in range(ja, jb + 1):
                    if (i, j) not in touched and _seg_box(
                            a, b, (i * s, j * s, (i + 1) * s, (j + 1) * s), eps):
                        touched.add((i, j))
    cache = {}

    def point(u, v):
        key = (round(u, 9), round(v, 9))
        q = cache.get(key)
        if q is None:
            hit = sampler.height(u, v)[0]
            if not hasattr(hit, "__len__"):   # nothing near: first corner
                hit = stris[0][0][2]
            q = cache[key] = (float(hit[0]), float(hit[1]), float(hit[2]))
        return q

    def src_at(u, v):
        hit = sampler.locate(u, v, 1e-7)
        idx = hit[1] if hit is not None else sampler.nearest(u, v)[1]
        return owner[tri_ids[idx]]

    tan_tol = math.tan(math.radians(p["planar_tol"]))
    square = mf.CrossSection.square([s, s])

    # the patch's own corners (folds of the surface) on the outline: a
    # piece edge running past one must bend there, or it cuts the corner
    vtol = s * 1e-5
    vcell = s
    vgrid = {}
    for t in stris:
        for q in t:
            vgrid.setdefault((int(q[0] // vcell), int(q[1] // vcell)),
                             set()).add((q[0], q[1]))

    def with_corners(lp):
        out = []
        n = len(lp)
        for k in range(n):
            a, b = lp[k], lp[(k + 1) % n]
            out.append(a)
            dx, dy = b[0] - a[0], b[1] - a[1]
            ll = dx * dx + dy * dy
            if ll < 1e-24:
                continue
            L = math.sqrt(ll)
            found = []
            for ix in range(int(min(a[0], b[0]) // vcell) - 1,
                            int(max(a[0], b[0]) // vcell) + 2):
                for iy in range(int(min(a[1], b[1]) // vcell) - 1,
                                int(max(a[1], b[1]) // vcell) + 2):
                    for q in vgrid.get((ix, iy), ()):
                        t = ((q[0] - a[0]) * dx + (q[1] - a[1]) * dy) / ll
                        if t * L <= vtol or (1 - t) * L <= vtol:
                            continue
                        x, y = a[0] + dx * t, a[1] + dy * t
                        if math.hypot(x - q[0], y - q[1]) <= vtol:
                            found.append((t, q))
            found.sort()
            out.extend(q for _t, q in found)
        return out

    def emit(loop_uv, holes_uv):
        loop_uv = with_corners(loop_uv)
        holes_uv = [with_corners(h) for h in holes_uv]
        loop = [point(u, v) for u, v in loop_uv]
        holes = [[point(u, v) for u, v in h] for h in holes_uv]
        cu = sum(q[0] for q in loop_uv) / len(loop_uv)
        cv = sum(q[1] for q in loop_uv) / len(loop_uv)
        split = None
        if not _is_planar(loop, holes, tan_tol):
            split = _split_bent(loop, holes)
        out["faces"].append((loop, holes, src_at(cu, cv), split))

    for i in range(i0, i1):
        for j in range(j0, j1):
            u, v = i * s, j * s
            cell = [(u, v), (u + s, v), (u + s, v + s), (u, v + s)]
            if (i, j) not in touched:
                if sampler.locate(u + s / 2, v + s / 2, 0.0) is None:
                    continue
                emit(cell, [])
                out["full"] += 1
                continue
            if not p["clip"]:
                if all(sampler.locate(cu, cv, 1e-7) is not None for cu, cv in cell) \
                        and sampler.locate(u + s / 2, v + s / 2, 0.0) is not None:
                    emit(cell, [])
                    out["full"] += 1
                continue
            piece = square.translate([u, v]) ^ foot
            if piece.is_empty() or piece.area() < s * s * 1e-6:
                continue
            outers, holes = [], []
            for poly in piece.to_polygons():
                pp = [(float(q[0]), float(q[1])) for q in poly]
                if len(pp) >= 3:
                    (outers if _area2(pp) > 0 else holes).append(pp)
            if len(outers) == 1 and not holes and _is_cell(outers[0], cell, eps):
                emit(cell, [])
                out["full"] += 1
                continue
            for o in outers:
                emit(o, [h for h in holes if _inside(h[0], o)])
                out["border"] += 1
    return True


def _close_seams(faces, s, tan_tol=0.0087):
    """Where patches meet: points closer than a hair are merged into one,
    and the points of one patch that lie on an edge of another patch's
    piece are added to that edge — no T-junctions, no slivers, the result
    stays closed."""
    tol = max(s * 1e-3, 1e-6)
    cell = max(s * 0.5, tol * 4)

    def ck(q):
        return (int(q[0] // cell), int(q[1] // cell), int(q[2] // cell))

    # 1. merge near-coincident points (the same corner seen by two patches)
    rep = {}
    grid = {}
    for loop, holes, _src, _split in faces:
        for lp in (loop, *holes):
            for q in lp:
                if q in rep:
                    continue
                c = ck(q)
                hit = None
                for dx in (-1, 0, 1):
                    for dy in (-1, 0, 1):
                        for dz in (-1, 0, 1):
                            for r in grid.get((c[0] + dx, c[1] + dy, c[2] + dz), ()):
                                if math.dist(q, r) <= tol:
                                    hit = r
                                    break
                            if hit:
                                break
                        if hit:
                            break
                    if hit:
                        break
                if hit is None:
                    grid.setdefault(c, []).append(q)
                    rep[q] = q
                else:
                    rep[q] = hit

    def snap(lp):
        out = []
        for q in lp:
            r = rep[q]
            if not out or out[-1] != r:
                out.append(r)
        while len(out) > 1 and out[0] == out[-1]:
            out.pop()
        return out

    # 2. points lying on another piece's edge go into that edge
    def on_edge(a, b):
        d = _sub(b, a)
        ll = _dot(d, d)
        if ll < 1e-24:
            return []
        L = math.sqrt(ll)
        lo = [min(a[k], b[k]) - tol for k in range(3)]
        hi = [max(a[k], b[k]) + tol for k in range(3)]
        found = []
        for ix in range(int(lo[0] // cell), int(hi[0] // cell) + 1):
            for iy in range(int(lo[1] // cell), int(hi[1] // cell) + 1):
                for iz in range(int(lo[2] // cell), int(hi[2] // cell) + 1):
                    for q in grid.get((ix, iy, iz), ()):
                        if q == a or q == b:
                            continue
                        t = _dot(_sub(q, a), d) / ll
                        if t * L <= tol or (1 - t) * L <= tol:
                            continue
                        x = (a[0] + d[0] * t, a[1] + d[1] * t, a[2] + d[2] * t)
                        if math.dist(x, q) <= tol:
                            found.append((t, q))
        found.sort()
        return [q for _t, q in found]

    def fix(lp):
        out = []
        for k in range(len(lp)):
            a, b = lp[k], lp[(k + 1) % len(lp)]
            out.append(a)
            out.extend(on_edge(a, b))
        # no spikes (… a b a …) and no repeated points
        changed = True
        while changed and len(out) >= 3:
            changed = False
            n = len(out)
            for k in range(n):
                if out[k - 1] == out[(k + 1) % n] or out[k] == out[k - 1]:
                    del out[k]
                    if out and out[k % len(out) - 1] == out[k % len(out)]:
                        del out[k % len(out)]
                    changed = True
                    break
        return out

    res, added = [], 0
    for loop, holes, src, split in faces:
        sl = snap(loop)
        if len(sl) < 3:
            continue                       # collapsed to a sliver: gone
        sh = [h2 for h2 in (snap(h) for h in holes) if len(h2) >= 3]
        nl = fix(sl)
        nh = [h2 for h2 in (fix(h) for h in sh) if len(h2) >= 3]
        if len(nl) < 3:
            continue
        added += len(nl) - len(loop)
        if split is not None or nl != loop or nh != holes:
            # re-check flatness on the final outline
            split = None if _is_planar(nl, nh, tan_tol) \
                else _split_bent(nl, nh)
        res.append((nl, nh, src, split))
    return res, added


def grid_plan_surface(faces, p) -> dict:
    """Grid Remesh for any shape: patches unfolded and gridded one by one.
    Same result format as :func:`grid_plan` (plus ``patches``)."""
    out = {"faces": [], "full": 0, "border": 0, "overlap": False,
           "spacing": 0.0, "error": None, "patches": 0, "surface": True}
    faces = list(faces)
    if not faces:
        out["error"] = "empty"
        return out
    s = p["spacing_m"] if p["spacing_m"] > 0 else auto_spacing(faces)
    out["spacing"] = s
    tris, owner, _down = _source_tris(faces)
    if not tris:
        out["error"] = "empty"
        return out
    charts, nb, _normals = _charts(tris)
    todo = [(c, CHART_DEG) for c in charts]
    while todo:
        members, dev = todo.pop()
        flat = _unfold(tris, members, nb)
        placed = [i for i in members if i in flat]
        rest = [i for i in members if i not in flat]
        if rest:                          # not reached across edges
            todo.append((rest, dev))
        if not placed:
            continue
        mark = len(out["faces"]), out["full"], out["border"]
        if _grid_patch(placed, flat, tris, owner, s, p, out):
            out["patches"] += 1
            if out["error"]:
                return out
            continue
        # overlapped itself when laid flat: undo, split it tighter
        del out["faces"][mark[0]:]
        out["full"], out["border"] = mark[1], mark[2]
        sub = [tris[i] for i in placed]
        cs, _nb2, _n2 = _charts(sub, max_dev=max(15.0, dev * 0.5))
        if len(cs) <= 1 and dev <= 15.0:
            # cannot split further: grid the triangles one by one
            for i in placed:
                fl = _unfold(tris, [i], nb)
                if fl and _grid_patch([i], fl, tris, owner, s, p, out):
                    out["patches"] += 1
            continue
        for c in cs:
            todo.append(([placed[k] for k in c], max(15.0, dev * 0.5)))
    out["faces"], out["seam_points"] = _close_seams(
        out["faces"], s, math.tan(math.radians(p["planar_tol"])))
    return out


# ---------------------------------------------------------------------------
# Grid Remesh «Any shape»: QUADS ONLY, like a retopology (1.3)
# ---------------------------------------------------------------------------
# The surface is cut into patches at its hard edges. Every patch is meshed
# as a structured quad grid that ends exactly on its outline:
#   * a patch with four corners (a wall, a rectangle, a side of a box):
#     a Coons patch — opposite sides get the same number of quads;
#   * a round patch without corners (a circle, an ellipse): an «O-grid» —
#     an inner square and four quad rings round it;
#   * a tube between two outlines (a duct, a loft from a rectangle to a
#     circle): rings of quads from one outline to the other;
#   * three corners: a fourth one is added on the longest side.
# The boundary of every patch is cut into chains between corners; each
# chain gets ONE number of divisions and ONE set of points, shared by both
# patches that meet there — so the patches join without gaps and without
# T-junctions, and every face is a quad. Points inside a patch are laid
# onto the old surface (closest point). Patches that are none of the above
# (holes, many outlines) fall back to the cut grid.

CORNER_DEG = 35.0          # a turn of the outline sharper than this = corner


def _np_closest(points, tris):
    """Closest point on the triangles for every point. points (n, 3),
    tris (m, 3, 3) → (n, 3) closest points, (n,) triangle index."""
    import numpy as np
    P = np.asarray(points, float)
    T = np.asarray(tris, float)
    out = np.empty_like(P)
    idx = np.zeros(len(P), dtype=np.int64)
    A, B, C = T[:, 0], T[:, 1], T[:, 2]
    AB, AC = B - A, C - A
    for s0 in range(0, len(P), 256):
        p = P[s0:s0 + 256][:, None, :]               # (k, 1, 3)
        AP = p - A
        d1 = (AB * AP).sum(-1)
        d2 = (AC * AP).sum(-1)
        BP = p - B
        d3 = (AB * BP).sum(-1)
        d4 = (AC * BP).sum(-1)
        CP = p - C
        d5 = (AB * CP).sum(-1)
        d6 = (AC * CP).sum(-1)
        va = d3 * d6 - d5 * d4
        vb = d5 * d2 - d1 * d6
        vc = d1 * d4 - d3 * d2
        den = va + vb + vc
        den = np.where(np.abs(den) < 1e-30, 1e-30, den)
        v = vb / den
        w = vc / den
        res = A + AB * v[..., None] + AC * w[..., None]
        # vertex / edge regions
        m = (d1 <= 0) & (d2 <= 0)
        res = np.where(m[..., None], A, res)
        m2 = (d3 >= 0) & (d4 <= d3)
        res = np.where(m2[..., None], B, res)
        m3 = (d6 >= 0) & (d5 <= d6)
        res = np.where(m3[..., None], C, res)
        t = np.clip(d1 / np.where(np.abs(d1 - d3) < 1e-30, 1e-30, d1 - d3), 0, 1)
        e = (vc <= 0) & (d1 >= 0) & (d3 <= 0)
        res = np.where(e[..., None], A + AB * t[..., None], res)
        t = np.clip(d2 / np.where(np.abs(d2 - d6) < 1e-30, 1e-30, d2 - d6), 0, 1)
        e = (vb <= 0) & (d2 >= 0) & (d6 <= 0)
        res = np.where(e[..., None], A + AC * t[..., None], res)
        num = d4 - d3
        t = np.clip(num / np.where(np.abs(num + d5 - d6) < 1e-30, 1e-30, num + d5 - d6), 0, 1)
        e = (va <= 0) & (num >= 0) & ((d5 - d6) >= 0)
        res = np.where(e[..., None], B + (C - B) * t[..., None], res)
        dist = ((res - p) ** 2).sum(-1)
        k = dist.argmin(1)
        out[s0:s0 + 256] = res[np.arange(len(k)), k]
        idx[s0:s0 + 256] = k
    return out, idx


def _resample(pts, n, closed=False):
    """``n`` segments of equal length along the polyline ``pts`` → n+1
    points (n points for a closed one)."""
    P = list(pts) + ([pts[0]] if closed else [])
    seg = [math.dist(P[k], P[k + 1]) for k in range(len(P) - 1)]
    total = sum(seg) or 1e-12
    out = [P[0]]
    k, acc = 0, 0.0
    for i in range(1, n):
        target = total * i / n
        while k < len(seg) - 1 and acc + seg[k] < target:
            acc += seg[k]
            k += 1
        t = 0.0 if seg[k] < 1e-15 else (target - acc) / seg[k]
        t = min(max(t, 0.0), 1.0)
        a, b = P[k], P[k + 1]
        out.append(tuple(a[c] + (b[c] - a[c]) * t for c in range(3)))
    if not closed:
        out.append(P[-1])
    return out


def _coons(B, R, T, L):
    """Discrete Coons patch. B, T: n+1 points (u), L, R: m+1 points (v);
    B[0]=L[0], B[n]=R[0], T[0]=L[m], T[n]=R[m]. → grid [i][j]."""
    n, m = len(B) - 1, len(L) - 1
    P00, P10, P01, P11 = B[0], B[n], T[0], T[n]
    G = []
    for i in range(n + 1):
        u = i / n
        col = []
        for j in range(m + 1):
            v = j / m
            if j == 0:
                col.append(B[i])
                continue
            if j == m:
                col.append(T[i])
                continue
            if i == 0:
                col.append(L[j])
                continue
            if i == n:
                col.append(R[j])
                continue
            q = []
            for c in range(3):
                q.append((1 - v) * B[i][c] + v * T[i][c] + (1 - u) * L[j][c] + u * R[j][c]
                         - ((1 - u) * (1 - v) * P00[c] + u * (1 - v) * P10[c]
                            + (1 - u) * v * P01[c] + u * v * P11[c]))
            col.append(tuple(q))
        G.append(col)
    return G


def _grid_quads(G, closed_u=False):
    """Quads of a point grid G[i][j] (i along u, j along v)."""
    n = len(G) - (0 if closed_u else 1)
    m = len(G[0]) - 1
    out = []
    for i in range(n):
        i1 = (i + 1) % len(G)
        for j in range(m):
            out.append([G[i][j], G[i1][j], G[i1][j + 1], G[i][j + 1]])
    return out


def grid_plan_quads(faces, p) -> dict:
    """Quads-only Grid Remesh for any shape (see the notes above). Same
    result format as :func:`grid_plan`."""
    import numpy as np
    out = {"faces": [], "full": 0, "border": 0, "overlap": False,
           "spacing": 0.0, "error": None, "patches": 0, "surface": True,
           "quads_only": True, "fallback": 0}
    faces = list(faces)
    if not faces:
        out["error"] = "empty"
        return out
    s = p["spacing_m"] if p["spacing_m"] > 0 else auto_spacing(faces)
    out["spacing"] = s
    tris, owner, _down = _source_tris(faces)
    if not tris:
        out["error"] = "empty"
        return out
    # shared vertices
    vid, verts, T = {}, [], []
    for t in tris:
        row = []
        for q in t:
            k = _key3(q)
            if k not in vid:
                vid[k] = len(verts)
                verts.append(tuple(q))
            row.append(vid[k])
        T.append(row)
    charts, _nb, normals = _charts(tris, max_dev=181.0)
    tri_patch = {}
    for ci, ch in enumerate(charts):
        for t in ch:
            tri_patch[t] = ci
    # directed edges → triangle
    dedge = {}
    for ti, (a, b, c) in enumerate(T):
        for e in ((a, b), (b, c), (c, a)):
            dedge.setdefault(e, []).append(ti)

    patches = []
    bad = set()
    for ci, ch in enumerate(charts):
        mine = set(ch)
        nxt = {}
        ok = True
        for ti in ch:
            a, b, c = T[ti]
            for e in ((a, b), (b, c), (c, a)):
                twin = [x for x in dedge.get((e[1], e[0]), []) if x in mine]
                if twin:
                    continue
                if e[0] in nxt:
                    ok = False             # pinched outline
                nxt[e[0]] = e[1]
        loops = []
        seen = set()
        for st in list(nxt):
            if st in seen:
                continue
            lp = [st]
            seen.add(st)
            cur = nxt[st]
            guard = 0
            while cur != st and guard < 1_000_000:
                if cur in seen or cur not in nxt:
                    ok = False
                    break
                lp.append(cur)
                seen.add(cur)
                cur = nxt[cur]
                guard += 1
            loops.append(lp)
        if not ok or len(loops) not in (1, 2):
            bad.add(ci)
        patches.append({"tris": ch, "loops": loops, "nxt": nxt})

    def nb_patch(a, b, ci):
        """Patch on the other side of boundary edge a→b of patch ci."""
        for ti in dedge.get((b, a), []):
            if tri_patch.get(ti) != ci:
                return tri_patch.get(ti)
        return None

    # corners: sharp turns and patch junctions
    corner = set()
    cos_c = math.cos(math.radians(CORNER_DEG))
    for ci, pt in enumerate(patches):
        for lp in pt["loops"]:
            n = len(lp)
            for k in range(n):
                a, v, b = lp[k - 1], lp[k], lp[(k + 1) % n]
                d1 = _sub(verts[v], verts[a])
                d2 = _sub(verts[b], verts[v])
                l1, l2 = _norm(d1), _norm(d2)
                if l1 < 1e-12 or l2 < 1e-12:
                    continue
                d1 = (d1[0] / l1, d1[1] / l1, d1[2] / l1)
                d2 = (d2[0] / l2, d2[1] / l2, d2[2] / l2)
                if _dot(d1, d2) < cos_c:
                    corner.add(v)
                elif nb_patch(a, v, ci) != nb_patch(v, b, ci):
                    corner.add(v)

    def arclen(lp, i0, i1):
        """Length along loop lp from index i0 to i1 (forward)."""
        n = len(lp)
        L, k = 0.0, i0
        while k != i1:
            L += math.dist(verts[lp[k]], verts[lp[(k + 1) % n]])
            k = (k + 1) % n
        return L

    def add_virtual(lp, want):
        """Add corners on the loop (at its vertices) until it has
        ``want``: the longest run between corners is halved each time."""
        n = len(lp)
        have = sorted(k for k, v in enumerate(lp) if v in corner)
        if not have:
            corner.add(lp[0])
            have = [0]
        while len(have) < want:
            best = None
            for idx, k0 in enumerate(have):
                k1 = have[(idx + 1) % len(have)]
                L = arclen(lp, k0, k1) if len(have) > 1 else arclen(lp, k0, (k0 - 1) % n) \
                    + math.dist(verts[lp[(k0 - 1) % n]], verts[lp[k0]])
                if best is None or L > best[0]:
                    best = (L, k0, k1)
            L, k0, k1 = best
            acc, k, pick = 0.0, k0, None
            while True:
                kn = (k + 1) % n
                if kn == k1 and len(have) > 1:
                    break
                if kn == k0:
                    break
                acc += math.dist(verts[lp[k]], verts[lp[kn]])
                if pick is None or abs(acc - L / 2) < pick[0]:
                    pick = (abs(acc - L / 2), kn)
                k = kn
            if pick is None or pick[1] in have:
                return False
            corner.add(lp[pick[1]])
            have = sorted(have + [pick[1]])
        return True

    # disks need four corners, circles get four virtual ones (O-grid)
    for ci, pt in enumerate(patches):
        if ci in bad:
            continue
        if len(pt["loops"]) == 1:
            lp = pt["loops"][0]
            nc = sum(1 for v in lp if v in corner)
            pt["ogrid"] = nc == 0
            if nc < 4 and not add_virtual(lp, 4):
                bad.add(ci)

    # chains between corners (closed when a loop has none)
    chains = {}                         # key → dict(pts, len, n)

    def chain_key(seq):
        return min(tuple(seq), tuple(reversed(seq)))

    for ci, pt in enumerate(patches):
        if ci in bad:
            continue
        pt["sides"] = []                # per loop: list of (key, forward)
        for lp in pt["loops"]:
            n = len(lp)
            cs = [k for k, v in enumerate(lp) if v in corner]
            runs = []
            if not cs:
                seq = list(lp) + [lp[0]]
                key = ("closed",) + tuple(sorted(lp))
                runs.append((key, seq))
            else:
                for idx, k0 in enumerate(cs):
                    k1 = cs[(idx + 1) % len(cs)]
                    seq = [lp[k0]]
                    k = k0
                    while True:
                        k = (k + 1) % n
                        seq.append(lp[k])
                        if k == k1:
                            break
                    runs.append((chain_key(seq), seq))
            sides = []
            for key, seq in runs:
                if key not in chains:
                    P = [verts[v] for v in seq]
                    L = sum(math.dist(P[k], P[k + 1]) for k in range(len(P) - 1))
                    chains[key] = {"seq": seq, "len": L,
                                   "n": max(1, int(round(L / s))),
                                   "closed": key[0] == "closed"}
                fwd = tuple(seq) == tuple(chains[key]["seq"]) or key[0] == "closed"
                sides.append((key, fwd, seq))
            pt["sides"].append(sides)

    # constraints: opposite sides equal; tube outlines equal; O-grid square
    cons = []
    for ci, pt in enumerate(patches):
        if ci in bad:
            continue
        if len(pt["loops"]) == 1:
            sd = pt["sides"][0]
            if len(sd) != 4:
                bad.add(ci)
                continue
            cons.append(([sd[0][0]], [sd[2][0]]))
            cons.append(([sd[1][0]], [sd[3][0]]))
            if pt.get("ogrid"):
                cons.append(([sd[0][0]], [sd[1][0]]))
        else:
            cons.append(([k for k, _f, _s in pt["sides"][0]],
                         [k for k, _f, _s in pt["sides"][1]]))
    for _it in range(20000):
        changed = False
        for A_, B_ in cons:
            sa = sum(chains[k]["n"] for k in A_)
            sb = sum(chains[k]["n"] for k in B_)
            if sa == sb:
                continue
            grow = A_ if sa < sb else B_
            k = max(grow, key=lambda q: chains[q]["len"] / chains[q]["n"])
            chains[k]["n"] += 1
            changed = True
        if not changed:
            break
    # the points of every chain, once
    for key, ch in chains.items():
        P = [verts[v] for v in ch["seq"]]
        if ch["closed"]:
            ch["pts"] = _resample(P[:-1], ch["n"], closed=True)
        else:
            ch["pts"] = _resample(P, ch["n"])

    def side_pts(side):
        """Points of one patch side (chains in walking order)."""
        res = []
        for key, fwd, seq in side:
            ch = chains[key]
            pts = list(ch["pts"])
            if ch["closed"]:
                # start where the loop starts, walk its way
                st = verts[seq[0]]
                k0 = min(range(len(pts)), key=lambda k: math.dist(pts[k], st))
                pts = pts[k0:] + pts[:k0]
                if len(seq) > 2 and len(pts) > 2:
                    a = math.dist(pts[1], verts[seq[1]])
                    b = math.dist(pts[-1], verts[seq[1]])
                    if b < a:
                        pts = [pts[0]] + pts[1:][::-1]
                pts = pts + [pts[0]]
            elif not fwd:
                pts = pts[::-1]
            if res:
                pts = pts[1:]
            res.extend(pts)
        return res

    tris_np = np.asarray(tris, float)

    def emit_grid(ci, quads, inner):
        """Lay the inner points onto the surface; orient; add the quads."""
        mine = patches[ci]["tris"]
        sub = tris_np[mine]
        if inner:
            pts = sorted(inner)
            proj, _i = _np_closest(pts, sub)
            mp = {q: tuple(map(float, r)) for q, r in zip(pts, proj)}
        else:
            mp = {}
        qs = [[mp.get(q, q) for q in quad] for quad in quads]
        if not qs:
            return
        cen = np.asarray([[sum(q[c] for q in quad) / 4 for c in range(3)] for quad in qs])
        _cp, ti = _np_closest(cen, sub)
        flip = 0.0
        tan_tol = math.tan(math.radians(p["planar_tol"]))
        for quad, t in zip(qs, ti):
            nx = ny = nz = 0.0
            for k in range(4):
                x0, y0, z0 = quad[k]
                x1, y1, z1 = quad[(k + 1) % 4]
                nx += (y0 - y1) * (z0 + z1)
                ny += (z0 - z1) * (x0 + x1)
                nz += (x0 - x1) * (y0 + y1)
            nr = normals[mine[int(t)]]
            flip += nx * nr[0] + ny * nr[1] + nz * nr[2]
        src_of = [owner[mine[int(t)]] for t in ti]
        for quad, src in zip(qs, src_of):
            if flip < 0:
                quad = quad[::-1]
            if len({tuple(round(c, 9) for c in q) for q in quad}) < 4:
                tri = []
                for q in quad:
                    if not tri or math.dist(tri[-1], q) > 1e-9:
                        tri.append(q)
                if len(tri) >= 2 and math.dist(tri[0], tri[-1]) < 1e-9:
                    tri.pop()
                if len(tri) < 3:
                    continue
                out["faces"].append((tri, [], src, None))
                out["border"] += 1
                continue
            split = None if _is_planar(quad, [], tan_tol) else _split_bent(quad, [])
            out["faces"].append((quad, [], src, split))
            out["full"] += 1

    for ci, pt in enumerate(patches):
        if ci in bad:
            continue
        if len(pt["loops"]) == 1:
            sd = pt["sides"][0]
            S = [side_pts([x]) for x in sd]
            if pt.get("ogrid"):
                c = [S[k][0] for k in range(4)]
                cen = tuple(sum(q[i] for q in c) / 4 for i in range(3))
                q = len(S[0]) - 1
                rad = sum(math.dist(cc, cen) for cc in c) / 4
                f = 0.5
                I = [tuple(cen[i] + (cc[i] - cen[i]) * f for i in range(3)) for cc in c]
                r = max(1, int(round(rad * (1 - f) / s)))
                inner_edges = [_resample([I[k], I[(k + 1) % 4]], q) for k in range(4)]
                radial = [_resample([c[k], I[k]], r) for k in range(4)]
                quads, inner = [], set()
                for k in range(4):
                    G = _coons(S[k], radial[(k + 1) % 4], inner_edges[k], radial[k])
                    quads += _grid_quads(G)
                    for i in range(1, len(G) - 1):
                        for j in range(1, len(G[0])):
                            inner.add(G[i][j])
                    for j in range(1, len(G[0])):
                        inner.add(G[0][j])
                Gc = _coons(inner_edges[0], inner_edges[1],
                            inner_edges[2][::-1], inner_edges[3][::-1])
                quads += _grid_quads(Gc)
                for col in Gc:
                    inner.update(col)
                emit_grid(ci, quads, inner)
            else:
                Bs, Rs = S[0], S[1]
                Ts, Ls = S[2][::-1], S[3][::-1]
                if len(Bs) != len(Ts) or len(Ls) != len(Rs):
                    bad.add(ci)
                    continue
                G = _coons(Bs, Rs, Ts, Ls)
                inner = {G[i][j] for i in range(1, len(G) - 1)
                         for j in range(1, len(G[0]) - 1)}
                emit_grid(ci, _grid_quads(G), inner)
        else:
            P1 = side_pts(pt["sides"][0])[:-1]
            P2 = side_pts(pt["sides"][1])[:-1]
            if len(P1) != len(P2) or len(P1) < 3:
                bad.add(ci)
                continue
            P2 = P2[::-1]                   # walk both outlines one way
            N = len(P1)
            off = min(range(N), key=lambda o: sum(
                math.dist(P1[i], P2[(i + o) % N]) for i in range(0, N, max(1, N // 16))))
            P2 = P2[off:] + P2[:off]
            M = max(1, int(round(sum(math.dist(a, b) for a, b in zip(P1, P2)) / N / s)))
            G = []
            inner = set()
            for i in range(N):
                col = []
                for j in range(M + 1):
                    t = j / M
                    q = tuple(P1[i][c] + (P2[i][c] - P1[i][c]) * t for c in range(3))
                    col.append(q)
                    if 0 < j < M:
                        inner.add(q)
                G.append(col)
            emit_grid(ci, _grid_quads(G, closed_u=True), inner)
        out["patches"] += 1

    if bad:
        # the rest: the cut grid of the patch (not only quads)
        out["fallback"] = len(bad)
        sub = {"faces": [], "full": 0, "border": 0, "error": None}
        for ci in bad:
            ch = patches[ci]["tris"]
            flat = _unfold(tris, ch, _nb)
            placed = [i for i in ch if i in flat]
            if placed:
                _grid_patch(placed, flat, tris, owner, s, p, sub)
        out["faces"] += sub["faces"]
        out["full"] += sub["full"]
        out["border"] += sub["border"]
        out["faces"], out["seam_points"] = _close_seams(
            out["faces"], s, math.tan(math.radians(p["planar_tol"])))
    return out


def _bounds(cs):
    b = cs.bounds()
    try:
        return (float(b[0]), float(b[1])), (float(b[2]), float(b[3]))
    except (TypeError, IndexError):  # pragma: no cover - other binding shape
        (a, c), (d, e) = b
        return (float(a), float(c)), (float(d), float(e))


def _area2(pts):
    return sum(pts[k][0] * pts[(k + 1) % len(pts)][1]
               - pts[(k + 1) % len(pts)][0] * pts[k][1] for k in range(len(pts)))


def _inside(pt, poly):
    x, y = pt
    inside = False
    for k in range(len(poly)):
        (x1, y1), (x2, y2) = poly[k], poly[(k + 1) % len(poly)]
        if (y1 > y) != (y2 > y) and x < (x2 - x1) * (y - y1) / (y2 - y1) + x1:
            inside = not inside
    return inside


def _is_cell(pts, cell, eps):
    if len(pts) != 4:
        return False
    return all(any(abs(a[0] - b[0]) <= eps * 10 and abs(a[1] - b[1]) <= eps * 10
                   for b in pts) for a in cell)


def _is_planar(loop, holes, tan_tol):
    pts = loop + [q for h in holes for q in h]
    if len(pts) <= 3:
        return True
    nx = ny = nz = 0.0
    for k in range(len(loop)):
        x0, y0, z0 = loop[k]
        x1, y1, z1 = loop[(k + 1) % len(loop)]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    ln = math.sqrt(nx * nx + ny * ny + nz * nz)
    if ln < 1e-15:
        return False
    nx, ny, nz = nx / ln, ny / ln, nz / ln
    cx = sum(q[0] for q in pts) / len(pts)
    cy = sum(q[1] for q in pts) / len(pts)
    cz = sum(q[2] for q in pts) / len(pts)
    size = max(math.dist(a, b) for a in loop for b in loop) or 1.0
    dev = max(abs((q[0] - cx) * nx + (q[1] - cy) * ny + (q[2] - cz) * nz) for q in pts)
    return dev <= size * tan_tol * 0.5


def _split_bent(loop, holes):
    """Triangles for a cell that is not flat: a quad by its shorter
    diagonal, anything else by IngeTrazo's own triangulator."""
    if len(loop) == 4 and not holes:
        a, b, c, d = loop
        if math.dist(a, c) <= math.dist(b, d):
            return [[a, b, c], [a, c, d]]
        return [[a, b, d], [b, c, d]]
    from PySide6.QtGui import QVector3D
    from core.triangulate import triangulate
    pv = [QVector3D(*q) for q in loop]
    hv = [[QVector3D(*q) for q in h] for h in holes]
    nx = ny = nz = 0.0
    for k in range(len(loop)):
        x0, y0, z0 = loop[k]
        x1, y1, z1 = loop[(k + 1) % len(loop)]
        nx += (y0 - y1) * (z0 + z1)
        ny += (z0 - z1) * (x0 + x1)
        nz += (x0 - x1) * (y0 + y1)
    tris = triangulate(pv, hv, QVector3D(nx, ny, nz).normalized())
    return [[_v(p) for p in t] for t in tris]


def apply_grid(mesh, faces, gp) -> dict:
    """Replace ``faces`` by the grid ``gp`` (from :func:`grid_plan`) — run it
    under an undo snapshot. Bent cells become triangles joined by a soft
    diagonal, so they still read as one quad."""
    from PySide6.QtGui import QVector3D
    gone = set(faces)
    touched_edges = set()
    for f in gone:
        for lp in (f.loop, *f.hole_loops):
            for k in range(len(lp)):
                e = mesh.find_edge(lp[k], lp[(k + 1) % len(lp)])
                if e is not None:
                    if f in e.faces:
                        e.faces.remove(f)
                    touched_edges.add(e)
    mesh.faces[:] = [f for f in mesh.faces if f not in gone]
    dead = {e for e in touched_edges if not e.faces}
    for e in dead:
        e.v0.edges.discard(e)
        e.v1.edges.discard(e)
    if dead:
        mesh.edges[:] = [e for e in mesh.edges if e not in dead]
    mesh._chunk_dirty = True
    mesh._mut_serial += 1
    mesh.prune_orphan_vertices()

    new_faces, soft = [], 0
    for loop, holes, src, split in gp["faces"]:
        attrs = dict(getattr(src, "attrs", None) or {})
        if split is None:
            try:
                nf = mesh.add_face([QVector3D(*q) for q in loop],
                                   [[QVector3D(*q) for q in h] for h in holes] or None)
            except Exception:  # noqa: BLE001 - degenerate piece
                continue
            nf.attrs = attrs
            new_faces.append(nf)
            continue
        made = []
        for t in split:
            try:
                nf = mesh.add_face([QVector3D(*q) for q in t])
            except Exception:  # noqa: BLE001
                continue
            nf.attrs = dict(attrs)
            made.append(nf)
        new_faces.extend(made)
        # Edges shared by two of this cell's own triangles are its inside.
        mine = set(made)
        for nf in made:
            lp = nf.loop
            for k in range(3):
                e = mesh.find_edge(lp[k], lp[(k + 1) % 3])
                if e is not None and not e.soft and len(e.faces) == 2 \
                        and all(g in mine for g in e.faces):
                    e.soft = True
                    soft += 1
    mesh._chunk_dirty = True
    mesh._mut_serial += 1
    return {"faces": new_faces, "soft": soft}


def run_grid(viewport, faces, gp) -> dict | None:
    from core.history import SnapshotImport
    scene = viewport.scene
    live = set(scene.mesh.faces)
    faces = [f for f in faces if f in live]
    if not faces or not gp or not gp["faces"]:
        return None
    result = {}

    def mutate(sc):
        result.update(apply_grid(sc.mesh, faces, gp))

    viewport.history.execute(SnapshotImport(mutate))
    viewport.notify_scene_changed()
    try:
        now = set(scene.mesh.faces)
        scene.select([f for f in result.get("faces", []) if f in now])
    except Exception:  # noqa: BLE001
        pass
    viewport.flash_status(_tr("Grid Remesh: {q} quads, {b} border pieces",
                              q=gp["full"], b=gp["border"]), 5000)
    viewport.update()
    return result


def _draw_grid_preview(viewport, painter) -> None:
    data = _STATE.get("grid_preview")
    if not data or _STATE.get("grid_dialog") is None:
        return
    import numpy as np
    from PySide6.QtCore import QLineF
    from PySide6.QtGui import QColor, QPen

    segs = data.get("segs")
    if segs is None or not len(segs):
        return
    px, py, front = viewport.world_to_pixels(segs)
    pen = QPen(QColor(0, 150, 255, 220), 1)
    pen.setCosmetic(True)
    painter.setPen(pen)
    lines = [QLineF(px[k], py[k], px[k + 1], py[k + 1])
             for k in range(0, len(segs), 2) if front[k] and front[k + 1]]
    if lines:
        painter.drawLines(lines)
    _ = np


def _grid_segments(gp, cap=60000):
    import numpy as np
    seen = set()
    out = []
    for loop, holes, _src, _split in gp["faces"]:
        for lp in (loop, *holes):
            for k in range(len(lp)):
                a, b = lp[k], lp[(k + 1) % len(lp)]
                key = (a, b) if a <= b else (b, a)
                if key in seen:
                    continue
                seen.add(key)
                out.append(a)
                out.append(b)
                if len(out) >= cap * 2:
                    return np.asarray(out, dtype=float)
    return np.asarray(out, dtype=float).reshape(-1, 3)


def _unit_scale_and_label():
    """Metres per displayed unit and its label, from the document."""
    try:
        from core import units
        code = units.model_unit()
        return units._BARE_SCALE.get(code, 1.0), code
    except Exception:  # noqa: BLE001
        return 1.0, "m"


def _make_grid_dialog_class():
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                                   QDoubleSpinBox, QFormLayout, QHBoxLayout,
                                   QLabel, QPushButton, QVBoxLayout)

    Live = _live_mixin()

    class GridDialog(Live, QDialog):
        def __init__(self, viewport):
            super().__init__(viewport.window())
            self.viewport = viewport
            self.p = load_grid_params()
            self.scale, self.unit = _unit_scale_and_label()
            self.setWindowTitle(f"{_tr('Grid Remesh')} — {_tr(TITLE)} {VERSION}")
            self.setModal(False)
            self.setAttribute(Qt.WA_DeleteOnClose, True)
            self.faces, self.from_sel = scope_faces(viewport.scene)
            self._gp = None
            self._gp_key = None
            self._sig = self._selection_sig()
            self._serial = self._mesh_serial()
            self._build()
            self._timer = QTimer(self)
            self._timer.setSingleShot(True)
            self._timer.setInterval(350)
            self._timer.timeout.connect(self._refresh)
            self._poll = QTimer(self)
            self._poll.setInterval(400)
            self._poll.timeout.connect(self._poll_state)
            self._poll.start()
            self._big_ok = None
            # the dialog shows first; the first plan comes right after
            if self.p["preview"]:
                QTimer.singleShot(0, lambda: self.preview.setChecked(True))
            else:
                QTimer.singleShot(0, self._refresh)

        def _build(self):
            lay = QVBoxLayout(self)
            form = QFormLayout()
            self.scope = QLabel(self)
            form.addRow(_tr("Scope"), self.scope)
            srow = QHBoxLayout()
            self.follow = QCheckBox(_tr("Follow selection"), self)
            self.follow.setChecked(self.p["follow"])
            self.follow.toggled.connect(self._follow_toggled)
            b_read = QPushButton(_tr("↻ Read selection"), self)
            b_read.clicked.connect(lambda: self._read_selection(True))
            srow.addWidget(self.follow)
            srow.addWidget(b_read)
            srow.addStretch(1)
            form.addRow("", srow)

            U = _pesi3d_units()
            if U:                          # metres, shown in document units
                self.scale = 1.0
                self.s_space = U["Length"](self, minimum=0.0, maximum=1e6)
            else:
                self.s_space = QDoubleSpinBox(self)
                self.s_space.setDecimals(3 if self.scale >= 1.0 else 1)
                self.s_space.setRange(0.0, 1e6)
                self.s_space.setSuffix(f" {self.unit}")
            sp = self.p["spacing_m"] or auto_spacing(self.faces)
            self.s_space.setValue(sp / self.scale)
            self.s_space.setToolTip(_tr("Size of one grid quad."))
            self.s_space.valueChanged.connect(self._changed)
            form.addRow(_tr("Spacing"), self.s_space)

            arow = QHBoxLayout()
            if U:
                self.s_angle = U["Angle"](self, -90.0, 90.0, decimals=2)
            else:
                self.s_angle = QDoubleSpinBox(self)
                self.s_angle.setRange(-90.0, 90.0)
                self.s_angle.setDecimals(2)
                self.s_angle.setSuffix(" °")
            self.s_angle.setValue(self.p["angle"])
            self.s_angle.valueChanged.connect(self._changed)
            b_auto = QPushButton(_tr("Auto"), self)
            b_auto.setToolTip(_tr("Turn the grid along the site (smallest box around it)."))
            b_auto.clicked.connect(
                lambda: self.s_angle.setValue(auto_angle(self.faces)))
            arow.addWidget(self.s_angle, 1)
            arow.addWidget(b_auto)
            form.addRow(_tr("Grid angle"), arow)

            self.c_mode = QComboBox(self)
            self.c_mode.addItem(_tr("Auto (terrain or any shape)"), "auto")
            self.c_mode.addItem(_tr("Height field (terrain, seen from above)"), "height")
            self.c_mode.addItem(_tr("Any shape — quads only (retopology)"), "surface")
            self.c_mode.setCurrentIndex(max(0, self.c_mode.findData(self.p.get("mode", "auto"))))
            self.c_mode.setToolTip(_tr(
                "Height field: the grid is laid seen from above (terrain). "
                "Any shape: quads only, like a retopology — the surface is "
                "cut into patches at its hard edges and every patch gets a "
                "structured quad grid that ends exactly on its outline "
                "(four corners: a grid; round: an O-grid; a tube: rings). "
                "Auto picks."))
            self.c_mode.currentIndexChanged.connect(self._changed)
            form.addRow(_tr("Surface"), self.c_mode)

            self.c_border = QComboBox(self)
            self.c_border.addItem(_tr("Clip to outline"), True)
            self.c_border.addItem(_tr("Whole cells only"), False)
            self.c_border.setCurrentIndex(0 if self.p["clip"] else 1)
            self.c_border.currentIndexChanged.connect(self._changed)
            form.addRow(_tr("Border"), self.c_border)

            if U:
                self.s_planar = U["Angle"](self, 0.0, _PLANAR_MAX, decimals=2)
            else:
                self.s_planar = QDoubleSpinBox(self)
                self.s_planar.setRange(0.0, _PLANAR_MAX)
                self.s_planar.setDecimals(2)
                self.s_planar.setSuffix(" °")
            self.s_planar.setValue(self.p["planar_tol"])
            self.s_planar.setToolTip(_tr("Cells flatter than this become one real face."))
            self.s_planar.valueChanged.connect(self._changed)
            form.addRow(_tr("Planar tolerance"), self.s_planar)

            self.result = QLabel(self)
            self.result.setWordWrap(True)
            form.addRow(_tr("Result"), self.result)
            self.b_big = QPushButton(self)
            self.b_big.setVisible(False)
            self.b_big.clicked.connect(self._compute_big)
            form.addRow("", self.b_big)
            lay.addLayout(form)
            self._live_build(lay)

        def _compute_big(self):
            self._big_ok = self._key(self._params())
            self.b_big.setVisible(False)
            self._refresh()

        def _params(self):
            p = dict(self.p)
            p["spacing_m"] = self.s_space.value() * self.scale
            p["angle"] = self.s_angle.value()
            p["clip"] = bool(self.c_border.currentData())
            p["mode"] = self.c_mode.currentData()
            p["planar_tol"] = self.s_planar.value()
            p["preview"] = self.preview.isChecked()
            p["follow"] = self.follow.isChecked()
            return p

        def _changed(self, *_a):
            if self.preview.isChecked():
                self._banner("busy", "⟳ Updating the preview…")
            self._timer.start()

        def _reset(self):
            d = GRID_DEFAULTS
            for w in (self.s_space, self.s_angle, self.c_border, self.s_planar,
                      self.c_mode):
                w.blockSignals(True)
            self.c_mode.setCurrentIndex(0)
            self.s_space.setValue((d["spacing_m"] or auto_spacing(self.faces)) / self.scale)
            self.s_angle.setValue(d["angle"])
            self.c_border.setCurrentIndex(0 if d["clip"] else 1)
            self.s_planar.setValue(d["planar_tol"])
            for w in (self.s_space, self.s_angle, self.c_border, self.s_planar,
                      self.c_mode):
                w.blockSignals(False)
            self._changed()

        def _selection_sig(self):
            try:
                return frozenset(id(e) for e in self.viewport.scene.selection)
            except Exception:  # noqa: BLE001
                return frozenset()

        def _mesh_serial(self):
            m = self.viewport.scene.mesh
            return (id(m), getattr(m, "_mut_serial", 0), len(m.faces))

        def _poll_state(self):
            serial = self._mesh_serial()
            if serial != self._serial:
                self._serial = serial
                self._read_selection(True)
                return
            if not self.follow.isChecked():
                return
            sig = self._selection_sig()
            if sig != self._sig:
                self._sig = sig
                self._read_selection(True)

        def _follow_toggled(self, on):
            if on:
                self._sig = self._selection_sig()
                self._read_selection(True)

        def _read_selection(self, only_if_faces):
            from core.mesh import Face
            sc = self.viewport.scene
            sel = list(sc.selection)
            if only_if_faces and sel and not any(isinstance(x, Face) for x in sel):
                return
            if self._pv_cmd is not None:
                self._live_undo(restore=False)
                alive = set(sc.mesh.faces) | set(sc.mesh.edges)
                sc.selection.clear()
                sc.selection.update(x for x in sel if x in alive)
                self._live_quiet()
            self.faces, self.from_sel = scope_faces(sc)
            self._gp_key = None
            self._refresh()

        def _key(self, p):
            # the source faces come back as the same objects after the
            # preview is undone: no mesh serial here (the preview changes it)
            return (tuple(id(f) for f in self.faces),
                    round(p["spacing_m"], 9), round(p["angle"], 6), p["clip"],
                    round(p["planar_tol"], 6), p.get("mode"))

        def _refresh(self):
            self._live_undo()
            p = self._params()
            mesh = self.viewport.scene.mesh
            live = set(mesh.faces)
            self.faces = [f for f in self.faces if f in live]
            if not self.from_sel and not self.faces:
                self.faces = list(mesh.faces)
            key = ("Selection: {t} triangles of {f} faces" if self.from_sel
                   else "Whole mesh: {t} triangles of {f} faces")
            n_tri = sum(1 for f in self.faces if len(f.loop) == 3)
            self.scope.setText(_tr(key, t=n_tri, f=len(self.faces)))
            k = self._key(p)
            sp = p["spacing_m"] if p["spacing_m"] > 0 else auto_spacing(self.faces)
            est = estimate_quads(self.faces, sp)
            self.b_big.setVisible(False)
            if est > _GRID_MAX_CELLS:
                self._gp, self._gp_key = None, None
                text = _tr("Spacing too small: about {n} quads — the limit is {m}. "
                           "Choose a larger spacing.",
                           n=f"{est:,}".replace(",", "."), m=f"{_GRID_MAX_CELLS:,}".replace(",", "."))
                self.result.setText(text)
                self.b_ok.setEnabled(False)
                self._banner("paused", f"⏸ <b>Preview paused</b> — {text}")
                return
            if est > _GRID_WARN_QUADS and self._big_ok != k and k != self._gp_key:
                self._gp, self._gp_key = None, None
                text = _tr("About {n} quads — this takes a while (up to minutes). "
                           "Choose a larger spacing, or compute anyway.",
                           n=f"{est:,}".replace(",", "."))
                self.result.setText(text)
                self.b_big.setText(_tr("Compute anyway (about {n} quads)",
                                       n=f"{est:,}".replace(",", ".")))
                self.b_big.setVisible(True)
                self.b_ok.setEnabled(False)
                self._banner("paused", f"⏸ <b>Preview paused</b> — {text}")
                return
            if k != self._gp_key:
                from PySide6.QtWidgets import QApplication
                from PySide6.QtCore import Qt as _Qt
                QApplication.setOverrideCursor(_Qt.WaitCursor)
                try:
                    self._gp = grid_plan(self.faces, p) if self.faces else None
                finally:
                    QApplication.restoreOverrideCursor()
                self._gp_key = k
            gp = self._gp
            ok = bool(gp and gp["faces"] and not gp["error"])
            if gp is None or gp["error"] == "empty":
                text = _tr("No faces in the scope.")
            elif gp["error"] == "too_many":
                text = _tr("Spacing too small: more than {n} cells.", n=_GRID_MAX_CELLS)
            elif gp["error"] == "vertical":
                text = _tr("The faces are vertical — nothing to see from above.")
            else:
                text = _tr("{q} quads · {b} border pieces", q=gp["full"], b=gp["border"])
                if gp.get("surface"):
                    if gp.get("quads_only"):
                        text += "\n" + _tr("Quads only: {n} patches", n=gp.get("patches", 0))
                        if gp.get("fallback"):
                            text += " · " + _tr("{n} patches as a cut grid (holes or more than four corners)",
                                               n=gp["fallback"])
                    else:
                        text += "\n" + _tr("Any shape: {n} surface patches, each "
                                           "gridded in its own directions",
                                           n=gp.get("patches", 0))
                if gp["overlap"] and not gp.get("surface"):
                    text += "\n" + _tr("Warning: the surface overlaps itself seen from "
                                       "above (steep or vertical parts). Grid Remesh "
                                       "needs a height field such as terrain.")
            self.result.setText(text)
            self.b_ok.setEnabled(ok)
            _STATE["grid_preview"] = None
            if p["preview"] and ok:
                faces = list(self.faces)
                res = self._live_apply(
                    lambda sc: apply_grid(sc.mesh, faces, gp), self._key(p),
                    lambda r: r.get("faces", []) if self.from_sel else [])
                if res is not None:
                    self._banner("live", f"● <b>LIVE PREVIEW</b> — {gp['full']} quads, "
                                 f"{gp['border']} border pieces · changes apply instantly")
            elif p["preview"]:
                self._banner("paused", f"⏸ <b>Preview paused</b> — {text}")
            elif ok:
                _STATE["grid_preview"] = {"segs": _grid_segments(gp)}
            self.viewport.update()

        def _apply(self):
            p = self._params()
            self.p = p
            save_grid_params(p)
            if self._live_keep(self._key(p)):
                gp = self._gp
                self.viewport.flash_status(_tr("Grid Remesh: {q} quads, {b} border pieces",
                                               q=gp["full"], b=gp["border"]), 5000)
                _STATE["grid_preview"] = None
                self.close()
                return
            self._live_undo()
            if self._key(p) != self._gp_key:
                self._gp = grid_plan(self.faces, p) if self.faces else None
                self._gp_key = self._key(p)
            gp, faces = self._gp, list(self.faces)
            _STATE["grid_preview"] = None
            self._kept = True
            self.close()
            run_grid(self.viewport, faces, gp)

        def closeEvent(self, ev):  # noqa: N802 - Qt naming
            try:
                self._poll.stop()
                self._timer.stop()
                self.p = self._params()
                save_grid_params(self.p)
                if not self._kept:
                    self._live_undo()          # Cancel: the preview goes
            except Exception:  # noqa: BLE001
                pass
            _STATE["grid_preview"] = None
            if _STATE.get("grid_dialog") is self:
                _STATE["grid_dialog"] = None
            try:
                self.viewport.update()
            except RuntimeError:  # the window is already gone (app closing)
                pass
            super().closeEvent(ev)

    return GridDialog


_GRID_DIALOG_CLASS = None


def open_grid_dialog(viewport):
    global _GRID_DIALOG_CLASS
    old = _STATE.get("grid_dialog")
    if old is not None:
        try:
            old.close()
        except Exception:  # noqa: BLE001
            pass
    if _GRID_DIALOG_CLASS is None:
        _GRID_DIALOG_CLASS = _make_grid_dialog_class()
    dlg = _GRID_DIALOG_CLASS(viewport)
    _STATE["grid_dialog"] = dlg
    dlg.show()
    dlg.raise_()
    return dlg


# ---------------------------------------------------------------------------
# 5. Registration.
# ---------------------------------------------------------------------------

# ---------------------------------------------------------------------------
# Toolbar (PESI3D): icons drawn in IngeTrazo's own icon style
# ---------------------------------------------------------------------------



# ---------------------------------------------------------------------------
# PESI3D unit fields — keep this block identical in every PESI3D plugin.
# Every length, angle and number field shows and reads the units of the
# open document (IngeTrazo ▸ Preferences ▸ Units: length unit and form,
# precision, angle unit, decimal separator). value() stays in metres /
# degrees, so the code behind a dialog never converts anything.
# ---------------------------------------------------------------------------
_PESI3D_UNITS = {}


def _pesi3d_units():
    """``{"Length", "Angle", "Area", "Number", "len", "area", "angle",
    "num"}`` —
    field classes and formatters in the document's units, or ``None`` on
    IngeTrazo builds before 0.5.8 (then the plain fields are used)."""
    if "ok" in _PESI3D_UNITS:
        return _PESI3D_UNITS["ok"]
    try:
        import math as _m
        from core import units
        from views.length_field import LengthSpinBox
        from PySide6.QtGui import QValidator
        from PySide6.QtWidgets import QDoubleSpinBox
    except Exception:  # noqa: BLE001 - an older IngeTrazo
        _PESI3D_UNITS["ok"] = None
        return None

    def _read_number(text, suffix):
        t = text.strip()
        if suffix and t.endswith(suffix.strip()):
            t = t[: -len(suffix.strip())]
        t = t.replace(" ", "").replace(",", ".")
        try:
            return float(t)
        except ValueError:
            return None

    class _Field(QDoubleSpinBox):
        def _read(self, text):                     # → value or None
            raise NotImplementedError

        def valueFromText(self, text):
            v = self._read(text)
            return self.value() if v is None else v

        def validate(self, text, pos):
            v = self._read(text)
            ok = v is not None and \
                self.minimum() - 1e-9 <= v <= self.maximum() + 1e-9
            return (QValidator.Acceptable if ok else QValidator.Intermediate,
                    text, pos)

        def fixup(self, text):
            return text

    class AngleSpinBox(_Field):
        """value() in degrees; text in the document's angle unit (°, rad,
        gon) and angle precision (at least ``decimals``)."""

        def __init__(self, parent=None, minimum=-360.0, maximum=360.0,
                     decimals=1):
            super().__init__(parent)
            self._unit = units.unit_setting("angle") or "deg"
            self._shown = max(int(decimals),
                              int(units.unit_setting("angle_precision") or 1))
            super().setDecimals(9)
            self.setRange(minimum, maximum)
            self.setSingleStep({"deg": 1.0, "grad": 0.9}.get(
                self._unit, _m.degrees(0.01)))
            self.setKeyboardTracking(False)

        def textFromValue(self, value):
            return units.localized(units.format_angle(
                _m.radians(value), self._unit, self._shown))

        def _read(self, text):
            r = units.parse(text, "angle", self._unit)
            return _m.degrees(r.value) if r.ok else None

    class AreaSpinBox(_Field):
        """value() in m²; text in the document's area unit and precision."""

        def __init__(self, parent=None, minimum=0.0, maximum=1e6):
            super().__init__(parent)
            u = units.unit_setting("area") or "auto"
            self._unit = (units.area_unit_for(units.model_unit())
                          if u == "auto" else u)
            self._shown = max(2, int(units.unit_setting("area_precision")
                                     or 2))
            super().setDecimals(9)
            self.setRange(minimum, maximum)
            self.setSingleStep(units.convert(
                10 ** -self._shown, self._unit, "m2"))
            self.setKeyboardTracking(False)

        def textFromValue(self, value):
            return units.localized(units.format_area(
                value, self._unit, self._shown))

        def _read(self, text):
            r = units.parse(text, "area", self._unit)
            return r.value if r.ok else None

    class NumberSpinBox(_Field):
        """A plain number (%, passes, factor …) with the document's decimal
        separator; «1,5» and «1.5» are both read."""

        def __init__(self, parent=None, minimum=0.0, maximum=1e6,
                     decimals=2, suffix=""):
            super().__init__(parent)
            self._dec, self._suf = int(decimals), suffix
            super().setDecimals(max(int(decimals), 6))
            self.setRange(minimum, maximum)
            self.setSingleStep(1.0 if decimals == 0 else 10 ** -min(decimals, 1))
            self.setKeyboardTracking(False)

        def textFromValue(self, value):
            return units.localized(f"{value:.{self._dec}f}{self._suf}")

        def _read(self, text):
            pre = self.prefix()
            if pre and text.startswith(pre):
                text = text[len(pre):]
            return _read_number(text, self._suf)

    class Length(LengthSpinBox):
        def __init__(self, parent=None, minimum=0.0, maximum=1000.0,
                     decimals=None):
            super().__init__(parent, minimum=minimum, maximum=maximum,
                             decimals=decimals)
            self.setKeyboardTracking(False)

    def fmt_len(metres, fine=False):
        if fine:
            return units.fmt_len_fine(float(metres))
        return units.fmt_len(float(metres))

    def fmt_area(m2):
        return units.fmt_area(float(m2))

    def fmt_angle(deg):
        return units.fmt_angle_deg(float(deg))

    def fmt_num(v, dec=2):
        return units.localized(f"{float(v):,.{dec}f}".replace(",", " ")
                               if abs(v) >= 1e4 else f"{float(v):.{dec}f}")

    res = {"Length": Length, "Angle": AngleSpinBox, "Number": NumberSpinBox,
           "Area": AreaSpinBox,
           "len": fmt_len, "area": fmt_area, "angle": fmt_angle,
           "num": fmt_num, "units": units}
    _PESI3D_UNITS["ok"] = res
    return res


def _pesi3d_icons():
    """Icon key → draw(painter, ink, accent) on a 48 px canvas."""
    import math  # noqa: F401
    from PySide6.QtCore import QPointF, QRectF, Qt  # noqa: F401
    from PySide6.QtGui import (QBrush, QColor, QPainterPath, QPen,  # noqa: F401
                               QPolygonF)

    def _a(c, alpha):
        return QColor(c.red(), c.green(), c.blue(), alpha)

    def _dot(p, acc, x, y, r=3.2, color=None):
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(color or acc)
        p.drawEllipse(QPointF(x, y), r, r)
        p.restore()

    def _poly(pts):
        return QPolygonF([QPointF(x, y) for x, y in pts])

    def _thin(p, ink, alpha=120, width=1.8, dashed=False):
        pen = QPen(_a(ink, alpha), width, Qt.DashLine if dashed else Qt.SolidLine)
        pen.setCapStyle(Qt.RoundCap)
        pen.setJoinStyle(Qt.RoundJoin)
        p.setPen(pen)

    def quadrify_icon(p, ink, acc):
        q = _poly([(9, 13), (37, 9), (40, 37), (11, 39)])
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(_a(acc, 120))
        p.drawPolygon(q)
        p.restore()
        p.save()
        _thin(p, ink, 140, 1.8, dashed=True)
        p.drawLine(QPointF(37, 9), QPointF(11, 39))   # the diagonal that goes
        p.restore()
        p.setBrush(Qt.NoBrush)
        p.drawPolygon(q)
        for x, y in ((9, 13), (37, 9), (40, 37), (11, 39)):
            _dot(p, acc, x, y, 3.0)

    def grid_remesh_icon(p, ink, acc):
        # A sheet in perspective with a regular quad grid on it.
        def pt(u, v):  # u, v in 0..1
            x0 = 6 + 8 * v
            x1 = 42 - 8 * v
            x = x0 + (x1 - x0) * u
            y = 38 - 24 * v + 3.0 * math.sin(u * 3.14159) * (1 - v)
            return QPointF(x, y)
        outline = QPolygonF([pt(0, 0), pt(1, 0), pt(1, 1), pt(0, 1)])
        p.save()
        p.setPen(Qt.NoPen)
        p.setBrush(_a(acc, 110))
        path = QPainterPath()
        n = 12
        path.moveTo(pt(0, 0))
        for i in range(1, n + 1):
            path.lineTo(pt(i / n, 0))
        path.lineTo(pt(1, 1))
        path.lineTo(pt(0, 1))
        path.closeSubpath()
        p.drawPath(path)
        p.restore()
        p.save()
        _thin(p, ink, 170, 1.8)
        for k in (1, 2):
            t = k / 3
            p.drawLine(pt(t, 0), pt(t, 1))
            line = QPainterPath()
            line.moveTo(pt(0, t))
            for i in range(1, n + 1):
                line.lineTo(pt(i / n, t))
            p.setBrush(Qt.NoBrush)
            p.drawPath(line)
        p.restore()
        p.setBrush(Qt.NoBrush)
        p.drawPath(path)

    return {"quadrify": quadrify_icon, "grid": grid_remesh_icon}


def _pesi3d_toolbar(app, title, entries):
    """A toolbar of this plugin's own — one icon per command (PESI3D).

    ``entries`` = (icon key, text, tip, callable). The icons are drawn
    like IngeTrazo's own (views/icons.py: 48 px, ink = the palette's text
    colour, 3 px pen, the orange accent) and redrawn when the theme flips.
    The toolbar moves, floats and hides like the built-in ones (right-click
    on any toolbar); its place is kept by its objectName."""
    try:
        from PySide6.QtCore import QEvent, QObject, QSize, Qt
        from PySide6.QtGui import QAction, QColor, QIcon, QPainter, QPen, QPixmap
        from PySide6.QtWidgets import QApplication, QToolBar
    except Exception:  # noqa: BLE001 — no Qt, no toolbar
        return None
    win = getattr(app, "window", None)
    if win is None:
        return None
    draws = _pesi3d_icons()

    def make_icon(key):
        draw = draws.get(key)
        if draw is None:
            return QIcon()
        qa = QApplication.instance()
        ink = (QColor(qa.palette().windowText().color()) if qa is not None
               else QColor(40, 44, 52))
        pm = QPixmap(48, 48)
        pm.fill(Qt.transparent)
        p = QPainter(pm)
        p.setRenderHint(QPainter.Antialiasing, True)
        pen = QPen(ink, 3.0)
        pen.setJoinStyle(Qt.RoundJoin)
        pen.setCapStyle(Qt.RoundCap)
        p.setPen(pen)
        try:
            draw(p, ink, QColor(243, 115, 41))
        finally:
            p.end()
        return QIcon(pm)

    name = f"pesi3d_{getattr(app, 'key', title)}"
    tb = None
    make = getattr(win, "_new_toolbar", None)     # the host's own builder
    if callable(make):
        try:
            tb = make(title, name)
        except Exception:  # noqa: BLE001
            tb = None
    if tb is None:
        tb = QToolBar(title, win)
        tb.setObjectName(name)
        tb.setMovable(True)
        tb.setFloatable(True)
        try:
            from views.icons import toolbar_icon_px
            px = int(toolbar_icon_px())
        except Exception:  # noqa: BLE001
            px = 24
        tb.setIconSize(QSize(px, px))
        tb.setToolButtonStyle(Qt.ToolButtonIconOnly)
        win.addToolBar(Qt.TopToolBarArea, tb)

    actions = []
    for key, text, tip, fn in entries:
        act = QAction(make_icon(key), text, tb)
        act.setToolTip(f"{text}\n{tip}" if tip else text)
        if tip:
            act.setStatusTip(tip)
        act.triggered.connect(lambda _c=False, f=fn: f())
        tb.addAction(act)
        actions.append((act, key))

    class _ThemeWatch(QObject):
        def eventFilter(self, obj, event):  # noqa: N802 — Qt override
            if event.type() in (QEvent.PaletteChange,
                                QEvent.ApplicationPaletteChange,
                                QEvent.StyleChange):
                for a, k in actions:
                    a.setIcon(make_icon(k))
            return False

    watch = _ThemeWatch(tb)
    tb.installEventFilter(watch)
    tb._pesi3d_watch = watch
    _pesi3d_place_later(win)
    return tb


def _pesi3d_place_later(win):
    """A toolbar the saved window layout does not know yet lands at the end
    of the top row, squeezed behind the built-in ones. Once the window is
    laid out, put new PESI3D toolbars on a row of their own under the
    built-in ones — only the first time each one appears; after that the
    user's own arrangement (saved with the window) wins. Every PESI3D
    plugin carries this code; the first one to get here does it for all."""
    if getattr(win, "_pesi3d_place_pending", False):
        return
    win._pesi3d_place_pending = True
    from PySide6.QtCore import QSettings, Qt, QTimer
    from PySide6.QtWidgets import QToolBar

    def place():
        win._pesi3d_place_pending = False
        try:
            st = QSettings()
            key = "plugins/pesi3d/placed_toolbars"
            placed = st.value(key) or []
            if isinstance(placed, str):
                placed = [placed]
            placed = list(placed)
            bars = [t for t in win.findChildren(QToolBar)
                    if t.objectName().startswith("pesi3d_")]
            new = [t for t in bars if t.objectName() not in placed]
            if not new:
                return
            fresh = not placed            # no PESI3D row yet → open one
            for i, t in enumerate(sorted(new, key=lambda t: t.objectName())):
                shown = not t.isHidden()
                win.removeToolBar(t)
                if fresh and i == 0:
                    win.addToolBarBreak(Qt.TopToolBarArea)
                win.addToolBar(Qt.TopToolBarArea, t)
                t.setVisible(shown)
            st.setValue(key, placed + [t.objectName() for t in new])
        except Exception:  # noqa: BLE001 — layout only, never break the app
            pass

    QTimer.singleShot(0, place)


def setup(app) -> None:
    """Extensions ▸ Quadrify ▸ Quadrify…, and the same entry in the
    viewport's right-click menu when faces are selected."""
    from PySide6.QtCore import QTimer

    tip = _tr("Turn pairs of triangles into four-sided faces.")
    sub = app.add_menu(_tr(TITLE))
    if sub is not None:
        a = sub.addAction(_tr("Quadrify…"))
        a.setStatusTip(tip)
        a.triggered.connect(lambda _c=False: open_dialog(app.viewport))
        g = sub.addAction(_tr("Grid Remesh…"))
        g.setStatusTip(_tr("Rebuild a terrain surface as a regular grid of quads."))
        g.triggered.connect(lambda _c=False: open_grid_dialog(app.viewport))
    else:  # pragma: no cover - no Extensions menu
        app.add_menu_action(_tr("Quadrify…"), lambda: open_dialog(app.viewport),
                            tip=tip)

    def context(menu, selection) -> None:
        from core.mesh import Face
        sel = getattr(app.viewport.scene, "selection", None) or selection or []
        if not any(isinstance(x, Face) for x in sel):
            return
        menu.addSeparator()
        if any(isinstance(x, Face) and len(x.loop) == 3 for x in sel):
            act = menu.addAction(_tr("Quadrify…"))
            act.triggered.connect(
                lambda _c=False: QTimer.singleShot(0, lambda: open_dialog(app.viewport)))
        act2 = menu.addAction(_tr("Grid Remesh…"))
        act2.triggered.connect(
            lambda _c=False: QTimer.singleShot(0, lambda: open_grid_dialog(app.viewport)))

    app.add_context_menu(context)
    app.add_overlay(_draw_preview)
    app.add_overlay(_draw_grid_preview)

    _pesi3d_toolbar(app, _tr(TITLE), [
        ("quadrify", _tr("Quadrify…"),
         _tr("Turn pairs of triangles into four-sided faces."),
         lambda: open_dialog(app.viewport)),
        ("grid", _tr("Grid Remesh…"),
         _tr("Rebuild a terrain surface as a regular grid of quads."),
         lambda: open_grid_dialog(app.viewport)),
    ])
