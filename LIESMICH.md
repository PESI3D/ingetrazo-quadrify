# Quadrify — Dreiecke zu Vierecken für IngeTrazo

Wandelt triangulierte Netze (OBJ, STL, DAE, glTF, Gelände) in **viereckige Flächen** um und baut Gelände als sauberes **Viereck-Raster** neu auf.

[English → README.md](README.md)

![Quadrify](screenshot.webp)

## Installation
1. In IngeTrazo: **Extensions ▸ Open plugins folder** (Windows: `%APPDATA%\ingetrazo\plugins\`, Linux: `~/.local/share/ingetrazo/plugins/`).
2. `quadrify_tool.py` in diesen Ordner kopieren.
3. IngeTrazo neu starten → **Extensions ▸ Quadrify ▸** *Quadrify… · Grid Remesh…* (auch im Rechtsklick-Menü, wenn Flächen gewählt sind).

Benötigt IngeTrazo ≥ 0.5 (Extension-API 2).

## Quadrify…
Entfernt die Diagonale zwischen zwei Dreiecken überall dort, wo sie ein gutes Viereck ergeben. Arbeitet mit den gewählten Flächen oder — ohne Auswahl — mit dem ganzen gerade bearbeiteten Netz (Gruppe vorher öffnen).

- **Flache Paare** werden eine echte Viereckfläche; Material und Tag bleiben erhalten.
- **Gekrümmte Paare** (Kugel, Gelände) können in IngeTrazo keine einzelne Fläche sein — Flächen sind eben —, deshalb wird die Diagonale **weich** (oder ausgeblendet) und das Paar wirkt wie ein Viereck. *Keep triangles* lässt sie unverändert.
- **Max face angle** — wie stark zwei Dreiecke gegeneinander geknickt sein dürfen. **Max shape angle** — wie weit jede Ecke von 90° abweichen darf (bei unregelmäßigen Netzen wie Gelände bis 90° erhöhen). **Planar tolerance** — bis zu diesem Knick entsteht eine echte Fläche. **Compare materials** — nur Dreiecke mit gleichem Material paaren.
- Die Paarung findet die größtmögliche Zahl an Vierecken; **Select Triangles Left** zeigt den Rest, **Select Edges** die Diagonalen, die entfallen.
- Vorschau: grün = wird Viereckfläche, orange = weiche Diagonale.

## Grid Remesh…
Baut ein Höhenfeld (Gelände) als regelmäßiges Raster neu auf: innen nur Vierecke, Randzellen am Umriss beschnitten (*Clip to outline*) oder weggelassen (*Whole cells only*). Die Höhen werden von der alten Fläche abgetastet. **Spacing**, **Grid angle** (*Auto* dreht das Raster entlang des Geländes), **Planar tolerance**, Vorschau.

Beide Befehle sind ein Undo-Schritt; die Dialoge blockieren den Viewport nicht (Orbit, Pan, Zoom).

## Änderungen
- **1.1** — eigene Werkzeugleiste **Quadrify** mit einem Icon je Befehl (Quadrify… · Grid Remesh…). Sie erscheint in einer eigenen Zeile unter den eingebauten Leisten und lässt sich wie diese verschieben, abdocken oder ausblenden (Rechtsklick auf eine Leiste). Icons im Stil von IngeTrazo, passend zum hellen/dunklen Theme.
- **1.0** — erste Veröffentlichung.

## Lizenz
GPL-3.0-or-later · © 2026 Pesi (pesi3d.de) · [Impressum](https://pesi3d.de)

3ds Max ist eine Marke von Autodesk, Inc.; der Name dient nur zur Beschreibung der Funktion («Quadrify All / Quadrify Selection»). Dieses Plugin steht in keiner Verbindung zu Autodesk.
