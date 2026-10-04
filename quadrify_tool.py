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
VERSION = "1.0"
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
        "Curved quads": "Gekrümmte Vierecke",
        "Soften diagonal": "Diagonale weich",
        "Hide diagonal": "Diagonale ausblenden",
        "Keep triangles": "Dreiecke behalten",
        "Compare materials": "Materialien vergleichen",
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


def _make_dialog_class():
    from PySide6.QtCore import Qt, QTimer
    from PySide6.QtWidgets import (QCheckBox, QComboBox, QDialog,
                                   QDoubleSpinBox, QFormLayout, QHBoxLayout,
                                   QLabel, QPushButton, QVBoxLayout)

    class QuadrifyDialog(QDialog):
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
            self._refresh()

        # ---- UI ------------------------------------------------------------
        def _spin(self, lo, hi, dec, val, tip):
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
            self.c_prev = QCheckBox(_tr("Preview"), self)
            self.c_prev.setChecked(self.p["preview"])
            self.c_prev.toggled.connect(self._changed)
            form.addRow("", self.c_prev)
            self.result = QLabel(self)
            self.result.setWordWrap(True)
            form.addRow(_tr("Result"), self.result)
            lay.addLayout(form)
            brow = QHBoxLayout()
            self.b_sel = QPushButton(_tr("Select Edges"), self)
            self.b_sel.clicked.connect(self._select_edges)
            self.b_ok = QPushButton(_tr("Quadrify"), self)
            self.b_ok.setDefault(True)
            self.b_ok.clicked.connect(self._apply)
            b_cancel = QPushButton(_tr("Cancel"), self)
            b_cancel.clicked.connect(self.close)
            brow.addWidget(self.b_sel)
            self.b_left = QPushButton(_tr("Select Triangles Left"), self)
            self.b_left.clicked.connect(self._select_left)
            brow.addWidget(self.b_left)
            brow.addStretch(1)
            brow.addWidget(self.b_ok)
            brow.addWidget(b_cancel)
            lay.addLayout(brow)

        def _params(self):
            p = dict(self.p)
            p["face_angle"] = self.s_face.value()
            p["shape_angle"] = self.s_shape.value()
            p["planar_tol"] = self.s_planar.value()
            p["curved"] = self.c_curved.currentData()
            p["materials"] = self.c_mat.isChecked()
            p["preview"] = self.c_prev.isChecked()
            p["follow"] = self.follow.isChecked()
            return p

        def _changed(self, *_a):
            self._timer.start()

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
            self.faces, self.from_sel = scope_faces(sc)
            self._refresh()

        # ---- plan + preview ----------------------------------------------------
        def _refresh(self):
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
            if p["preview"]:
                merge, soft = [], []
                for e, *_r, kind, _fl in pl["pairs"]:
                    seg = (_v(e.v0.position), _v(e.v1.position))
                    (merge if kind == "merge" else soft).append(seg)
                _STATE["preview"] = {"merge": merge, "soft": soft}
            else:
                _STATE["preview"] = None
            self.viewport.update()

        # ---- actions -------------------------------------------------------------
        def _select_edges(self):
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
            faces, from_sel = list(self.faces), self.from_sel
            _STATE["preview"] = None
            self.close()
            run_quadrify(self.viewport, faces, p, from_sel)

        def closeEvent(self, ev):  # noqa: N802 - Qt naming
            try:
                self._poll.stop()
                self._timer.stop()
                self.p = self._params()
                save_params(self.p)
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
}

#: Above this many cells the grid is refused (spacing far too small).
_GRID_MAX_CELLS = 400_000


def load_grid_params() -> dict:
    p = dict(GRID_DEFAULTS)
    try:
        from PySide6.QtCore import QSettings
        st = QSettings()
        for k, v in GRID_DEFAULTS.items():
            if isinstance(v, bool):
                p[k] = st.value(f"plugins/{KEY}/grid_{k}", v, type=bool)
            else:
                p[k] = float(st.value(f"plugins/{KEY}/grid_{k}", v))
    except Exception:  # noqa: BLE001
        pass
    p["planar_tol"] = min(max(p["planar_tol"], 0.0), _PLANAR_MAX)
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

    class GridDialog(QDialog):
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
            self._refresh()

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

            self.c_border = QComboBox(self)
            self.c_border.addItem(_tr("Clip to outline"), True)
            self.c_border.addItem(_tr("Whole cells only"), False)
            self.c_border.setCurrentIndex(0 if self.p["clip"] else 1)
            self.c_border.currentIndexChanged.connect(self._changed)
            form.addRow(_tr("Border"), self.c_border)

            self.s_planar = QDoubleSpinBox(self)
            self.s_planar.setRange(0.0, _PLANAR_MAX)
            self.s_planar.setDecimals(2)
            self.s_planar.setSuffix(" °")
            self.s_planar.setValue(self.p["planar_tol"])
            self.s_planar.setToolTip(_tr("Cells flatter than this become one real face."))
            self.s_planar.valueChanged.connect(self._changed)
            form.addRow(_tr("Planar tolerance"), self.s_planar)

            self.c_prev = QCheckBox(_tr("Preview"), self)
            self.c_prev.setChecked(self.p["preview"])
            self.c_prev.toggled.connect(self._changed)
            form.addRow("", self.c_prev)
            self.result = QLabel(self)
            self.result.setWordWrap(True)
            form.addRow(_tr("Result"), self.result)
            lay.addLayout(form)
            brow = QHBoxLayout()
            brow.addStretch(1)
            self.b_ok = QPushButton(_tr("Remesh"), self)
            self.b_ok.setDefault(True)
            self.b_ok.clicked.connect(self._apply)
            b_cancel = QPushButton(_tr("Cancel"), self)
            b_cancel.clicked.connect(self.close)
            brow.addWidget(self.b_ok)
            brow.addWidget(b_cancel)
            lay.addLayout(brow)

        def _params(self):
            p = dict(self.p)
            p["spacing_m"] = self.s_space.value() * self.scale
            p["angle"] = self.s_angle.value()
            p["clip"] = bool(self.c_border.currentData())
            p["planar_tol"] = self.s_planar.value()
            p["preview"] = self.c_prev.isChecked()
            p["follow"] = self.follow.isChecked()
            return p

        def _changed(self, *_a):
            self._timer.start()

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
            sel = list(self.viewport.scene.selection)
            if only_if_faces and sel and not any(isinstance(x, Face) for x in sel):
                return
            self.faces, self.from_sel = scope_faces(self.viewport.scene)
            self._gp_key = None
            self._refresh()

        def _key(self, p):
            return (tuple(id(f) for f in self.faces), self._mesh_serial(),
                    round(p["spacing_m"], 9), round(p["angle"], 6), p["clip"],
                    round(p["planar_tol"], 6))

        def _refresh(self):
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
            if k != self._gp_key:
                self._gp = grid_plan(self.faces, p) if self.faces else None
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
                if gp["overlap"]:
                    text += "\n" + _tr("Warning: the surface overlaps itself seen from "
                                       "above (steep or vertical parts). Grid Remesh "
                                       "needs a height field such as terrain.")
            self.result.setText(text)
            self.b_ok.setEnabled(ok)
            if p["preview"] and ok:
                _STATE["grid_preview"] = {"segs": _grid_segments(gp)}
            else:
                _STATE["grid_preview"] = None
            self.viewport.update()

        def _apply(self):
            p = self._params()
            self.p = p
            save_grid_params(p)
            if self._key(p) != self._gp_key:
                self._refresh()
            gp, faces = self._gp, list(self.faces)
            _STATE["grid_preview"] = None
            self.close()
            run_grid(self.viewport, faces, gp)

        def closeEvent(self, ev):  # noqa: N802 - Qt naming
            try:
                self._poll.stop()
                self._timer.stop()
                self.p = self._params()
                save_grid_params(self.p)
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
