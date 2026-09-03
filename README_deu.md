<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-COGNITIVE-NODE banner" width="100%">
</p>

# 🧠 HYDRA-UMC-COGNITIVE-NODE

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | <a href="README_fra.md">🇫🇷 Français</a> | <a href="README_ita.md">🇮🇹 Italiano</a> | 🇩🇪 <b>Deutsch</b> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🤖 Semantisches Denken & GenAI Edge Node (Hailo-10 + Raspberry Pi CM5)

<p align="left">
  <img src="https://img.shields.io/badge/Lizenz-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Hardware-CM5%20%2B%20Hailo--10-orange.svg" alt="CM5 + Hailo-10">
  <img src="https://img.shields.io/badge/Leistung-40%20TOPS-green.svg" alt="40 TOPS">
  <img src="https://img.shields.io/badge/GenAI-Lokales%20LLM%20%2F%20VLA-blueviolet.svg" alt="GenAI">
</p>

---

## 1. 🛠️ TECHNISCHER ÜBERBLICK

**HYDRA-UMC-COGNITIVE-NODE** dient als "Frontallappen" des HYDRA-UMC-Ökosystems. Angetrieben von der Hailo-10 NPU (40 TOPS), ermöglicht er komplexes semantisches Denken, natürliches Sprachverständnis und Vision-Language-Action (VLA) Aufgabenplanung direkt am Edge.

Er transformiert hochgradige menschliche Anweisungen in logische Robotersequenzen und verwaltet die Fehlerbehebung sowie die Missionsoptimierung ohne Cloud-Abhängigkeit.

### Hauptmerkmale:
* 🧠 **Lokale LLM-Ausführung:** Hardwarebeschleunigte Inferenz für quantisierte Modelle (Llama/Mistral). *(geplant - benötigt die echte Hailo-10-Modell-Laufzeitumgebung)*
* 👁️ **VLA-Integration:** Vision-Language-Action-Modelle für eine intuitive Aufgabenausführung. *(geplant)*
* 🎙️ **Sprachbefehlsverarbeitung:** Echtzeit-STT/TTS für die Mensch-Roboter-Interaktion. *(geplant)*
* 🛡️ **Datenschutz zuerst:** 100% Offline-Verarbeitung aller kognitiven Aufgaben. *(schon jetzt so konzipiert, sobald das Obige existiert - hier ruft heute nichts ein Netzwerk auf)*
* 🧩 **Integrations-Hub (v0):** Besitzt das gemeinsam genutzte HydraOS-Image
  und die quantisierten Modellgewichte, die von seinen 4 Kindern genutzt
  werden, und verbindet sie als Schwesterdienste in einer einzigen
  `docker-compose.yml`. Die echte `family-status`-Prüfung liest das echte
  Manifest jedes Kindes, um Präsenz/Version/Reifegrad zu melden.
  *(implementiert als echte Bereitschaftsprüfung - siehe BUILD UND
  AUSFÜHRUNG unten)*
* 🔒 **Versioniertes Status-Schema + ressourcenbeschränkte Manifest-Lesevorgänge:** `family-status --json` gibt ein echtes, versioniertes, maschinenlesbares Ergebnis aus; jedes Geschwister-Manifest, das größer als 64 KiB ist (ein beschädigtes oder manipuliertes Checkout), degradiert zu "nicht gefunden", statt unbegrenzt eingelesen zu werden. *(implementiert)*
* 🪫 **Degradationsprüfung für gemeinsam genutzte Modellgewichte:** `family-status` meldet ehrlich, ob das eigene `models/`-Verzeichnis dieses Knotens tatsächlich echte Gewichte enthält - nicht nur, ob die Geschwister-Repos ausgecheckt sind. *(implementiert)*
* 📦 **Kilometerzähler-Versionierung:** Jeder echte Build erhöht
  automatisch die Version in `pyproject.toml` (`bump_version.py`) - keine
  manuellen Versionsänderungen.

---

## 2. 🔄 KOGNITIVER ARBEITSABLAUF

```mermaid
flowchart TB
    INPUT["Sprach- / Texteingabe"] --> VOICE["VOICE-UI (STT)"]
    VOICE --> PLANNER["SEMANTIC-PLANNER (LLM)"]
    VIS["Vision Node Daten"] --> VLA["VLA-ENGINE"]
    VLA --> PLANNER
    PLANNER --> ORCH["HYDRA-ORCHESTRATOR"]
    DOCS["Technische Handbücher"] --> RAG["DOCS-QA (RAG)"]
    RAG --> PLANNER
```

---

## 3. 🧱 ARCHITEKTUR & DESIGNENTSCHEIDUNGEN

Dieses Repository ist der **Eltern-/Integrationspunkt** der Cognitive AI
Node-Familie. Es führt selbst kein Modell aus - es besitzt die
gemeinsamen Ressourcen und die Verdrahtung, die es seinen vier Kindern
ermöglichen, als eine kognitive Einheit auf derselben physischen Platine
zu agieren:

* **Warum dieser Knoten keine eigene Hardware/Firmware hat.** Anders als
  die Firmware auf Motherboard-Ebene von HYDRA-UMC läuft dieser Knoten
  vollständig auf einem bereits vorhandenen Raspberry Pi CM5 + Hailo-10
  M.2-Modul - es gibt hier keine eigene Leiterplatte oder einen eigenen
  Mikrocontroller zu entwerfen, daher wurden die Ordner
  `hardware/`/`firmware/` entfernt, statt sie leer zu lassen.
* **Warum `os/` und `models/` nur im Elternteil liegen.** Das
  HydraOS-Image und die quantisierten LLM/VLA-Gewichte sind gemeinsam
  genutzte Ressourcen auf Platinenebene - eine einzige Kopie im
  Elternteil zu behalten und sie schreibgeschützt in jeden
  Kind-Container zu mounten (siehe `docker-compose.yml`) vermeidet vier
  abweichende Kopien mehrere Gigabyte großer Modellgewichte.
* **Warum ein `src/`-Layout.** Trennt das installierbare Paket
  (`hydra_umc_cognitive_node`) vom Tooling im Repo-Root
  (`bump_version.py`, `docker-compose.yml`) und entspricht dem Layout
  aller anderen Python-Projekte im Ökosystem.
* **Warum der Einstiegspunkt heute nur Identität/Version/Rolle
  ausgibt.** Dies ist die Andamiaje- (Gerüst-) Phase: zu beweisen, dass
  sich das Paket auf der tatsächlichen Ziel-Python-Version sauber
  installieren, kompilieren und importieren lässt, ist Voraussetzung,
  bevor echte LLM/VLA/Sprach-Orchestrierungslogik hinzugefügt wird, und
  hält diese spätere Arbeit von Packaging-Fragen getrennt.
* **Warum `docker-compose.yml` existiert, bevor die Kinder eigene
  Dockerfiles haben.** Den Integrationsvertrag jetzt zu entscheiden und
  zu dokumentieren (welcher Dienst von welchem abhängt, welche
  Geräte-/Volume-Mounts jeder benötigt) verhindert, dass diese Form
  später ad hoc erfunden wird - auch wenn `docker compose up` erst dann
  vollständig funktioniert, wenn jedes Kind sein eigenes Dockerfile
  veröffentlicht.
* **Wie sich das in den Rest des Ökosystems einfügt.** Dieser Knoten
  sitzt eine Schicht über der Wahrnehmung (HYDRA-UMC-VISION-NODE,
  Hailo-8) und eine Schicht unter der Missionsorchestrierung
  (HYDRA-UMC-ORCHESTRATOR): Er wandelt Sprach-/Textanweisungen und
  Erkennungen in semantische Entscheidungen um, die der Orchestrator
  anschließend in physische Roboterbefehle umsetzt.
* **Warum `family-status` das eigene Manifest jedes Kindes liest, statt
  einer von Hand gepflegten Liste.** `hydra-umc.project.json` ist bereits
  die einzige Quelle der Wahrheit, der das ökosystemweite Dashboard und
  der Updater vertrauen - eine zweite
  Liste hier würde in dem Moment auseinanderdriften, in dem sich der
  echte Reifegrad eines Kindes ändert und niemand daran denkt, sie zu
  aktualisieren.
* **Warum ein fehlendes Geschwister-Checkout ein echtes, ehrliches
  "nicht gefunden" ist, kein Fehler.** Ein Integrations-Hub weiß
  wirklich nicht, ob ein Entwickler alle vier Kinder lokal ausgecheckt
  hat - `manifest.py` gibt für jeden echten Fehlerfall (fehlendes Repo,
  fehlendes Manifest, fehlerhaftes JSON) `None` zurück, sodass
  `family-status` dies klar meldet, statt abzustürzen.
* **Warum Manifest-Lesevorgänge von Geschwistern auf 64 KiB begrenzt
  sind.** Jedes echte Manifest in diesem Ökosystem ist einige hundert
  Byte bis wenige KiB groß - ein beschädigtes oder manipuliertes
  Checkout, dessen Manifest durch eine überdimensionierte Datei ersetzt
  wurde, darf eine routinemäßige Bereitschaftsprüfung niemals dazu
  bringen, eine unbegrenzte Menge an Daten in den Speicher zu laden. Es
  degradiert zu `None`, genau wie jedes andere fehlerhafte Manifest.
* **Warum `family-status` `models/` meldet, obwohl dieser Knoten selbst
  kein Modell ausführt.** "Die Geschwister-Repos sind ausgecheckt" und
  "die gemeinsam genutzten Gewichte, die sie bräuchten, sind tatsächlich
  vorhanden" sind zwei unterschiedliche echte Fakten -
  `check_shared_models()` in `models.py` prüft den zweiten ehrlich (leer,
  aber vorhanden zählt als fehlend), statt einen Betreiber allein aus der
  Präsenz der Kinder auf Bereitschaft schließen zu lassen.

---

## 📂 VERZEICHNISSTRUKTUR

```text
HYDRA-UMC-COGNITIVE-NODE/
├── src/hydra_umc_cognitive_node/
│   ├── manifest.py                 # Echter, defensiver Leser für das eigene Manifest eines Geschwisters (64 KiB Grenze)
│   ├── models.py                   # Echte Prüfung des eigenen Verzeichnisses mit gemeinsam genutzten Modellgewichten dieses Knotens
│   ├── family.py                    # Echte Familien-Bereitschaftsprüfung + versioniertes JSON-Schema
│   ├── api.py                         # Einfache JSON/HTTP-Oberfläche (stdlib http.server) über `family-status`
│   └── main.py                        # Einstiegspunkt + echtes Subcommand `family-status [--json]`
├── tests/                          # Echte Tests: Manifest-Lesen, Modelle, Familienstatus, api, End-to-End-CLI
├── docs/                           # Dokumentation und Architektur
├── os/                             # HydraOS-Image/Konfiguration für die CM5 - wird beim Deployment befüllt (nicht in git)
├── models/                         # Hailo-10-optimierte Gewichte (LLM/VLA, von den 4 Kindern gemeinsam genutzt) - wird beim Deployment befüllt (nicht in git)
├── images/                         # Medien und Diagramme
├── systemd/
│   └── hydra-umc-cognitive-node.service # systemd-Unit der lokalen CM5-family-status-API
├── tools/
│   ├── build_test.py               # Nicht-versionierender Build-Check
│   └── ci_validate.py              # Manifest/CHANGELOG/Docs-Validierung, von CI genutzt
├── build/                          # Lokale Build-Ausgabe (von git ignoriert)
├── pyproject.toml                  # Paket-Metadaten (Version per Kilometerzähler-Inkrement)
├── bump_version.py                 # Native Kilometerzähler-artige Versionserhöhung (von build.sh/.bat verwendet)
├── bump_manifest_version.py        # Synchronisiert die Version von hydra-umc.project.json mit der nativen (--sync)
├── docker-compose.yml              # Integrationskarte für die 4 Kind-Dienste
├── build.sh / build.bat            # Erstellt das venv, installiert (mit Dev-Extras), führt Tests aus, prüft den Import
└── run.sh / run.bat                # Führt den Einstiegspunkt aus (leitet Argumente weiter, z. B. `family-status`)
```

> **Hinweis:** `hardware/` und `firmware/` wurden entfernt - dieser Knoten
> läuft auf einem bereits vorhandenen CM5 + Hailo-10 M.2 Modul ohne
> eigenes Hardware-/Firmware-Design. Ein eigener Hilfsmikrocontroller
> könnte später bei Bedarf ergänzt werden.

---

## ⚙️ BUILD UND AUSFÜHRUNG

Erfordert Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # erstellt .venv, installiert das Paket (editable), prüft den Import
./run.sh     # führt den Einstiegspunkt aus

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` erhöhen die Version (Kilometerzähler-Stil, siehe
`bump_version.py`) vor jedem echten Build und führen die echte Testsuite
aus (`pytest tests/`). Erwartete Ausgabe eines `run.sh` ohne Argumente:

```text
HYDRA-UMC-COGNITIVE-NODE v0.0.8
Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine, Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.
```

Siehe `docker-compose.yml` dafür, wie die vier Kind-Dienste (VLA-Engine,
Voice-UI, Semantic-Planner, Docs-QA) an diesen Knoten angebunden werden,
sobald jeder sein eigenes Dockerfile veröffentlicht.

Das echte Subcommand `family-status` prüft die echten Kinder in einem
echten lokalen Checkout:

```bash
./run.sh family-status
./run.sh family-status --workspace /pfad/zu/einem/anderen/checkout
./run.sh family-status --json

# Windows
run.bat family-status
```

`family-status` meldet immer auch die eigenen gemeinsam genutzten
Modellgewichte dieses Knotens - ein echtes, leeres `models/` auf einer
Entwicklungsmaschine ist ehrlich `MISSING`, niemals stillschweigend
ignoriert:

```text
Cognitive AI Node family status (workspace: /path/to/workspace):
  HYDRA-UMC-VLA-ENGINE: v0.1.0, maturity=established, role=service
  ...

Shared model weights: MISSING (.../HYDRA-UMC-COGNITIVE-NODE/models) - this node's own os/models weights have not been provisioned on this machine; children that need them will run in their own honest degraded/no-hardware mode.

All 4 children present.
```

`--json` gibt stattdessen dieselben echten Daten als versioniertes,
maschinenlesbares Objekt aus:

```bash
$ ./run.sh family-status --json
{
  "schema_version": "1.0",
  "shared_models": { "present": false, "path": ".../models" },
  "children": [
    { "name": "HYDRA-UMC-VLA-ENGINE", "present": true, "version": "0.1.0", "maturity": "established", "role": "service" },
    ...
  ],
  "all_children_present": true
}
```

Standardmäßig wird das eigene übergeordnete Verzeichnis dieses Repos
verwendet - dasselbe Layout, das jeder echte Checkout dieses Ökosystems
bereits nutzt (alle Repos als Geschwister unter einem gemeinsamen
Workspace-Ordner). Beendet sich mit `1`, wenn ein echtes Kind fehlt.

### 🩺 Fehlerbehebung

* **`python: Befehl nicht gefunden` / der Build schlägt bei Schritt 1
  fehl.** Erfordert Python >= 3.10 im `PATH`. Unter Windows von
  [python.org](https://python.org) installieren und bei der Installation
  "Add to PATH" ankreuzen; unter Linux/macOS heißt es meist `python3`.
* **`build.sh` kann das venv nicht aktivieren.** `python3 -m venv .venv`
  legt das Aktivierungsskript je nach Plattform an anderer Stelle ab:
  `.venv/bin/activate` unter Linux/macOS, `.venv/Scripts/activate` unter
  Windows (auch bei einem Windows-Python-venv, das aus Git Bash heraus
  verwendet wird). `build.sh` prüft bereits beide Pfade - schlägt es
  weiterhin fehl, `.venv/` löschen und `./build.sh` erneut ausführen, um
  es von Grund auf neu zu erstellen.
* **`pip install -e .` schlägt fehl.** Meist wegen eines veralteten
  `.venv/`. Den Ordner `.venv/` löschen und `./build.sh`/`build.bat`
  erneut ausführen, um ihn neu zu erstellen.
* **`import OK` erscheint nie.** Bedeutet, dass `python -c "import
  hydra_umc_cognitive_node"` selbst fehlgeschlagen ist - mit aktivem venv
  erneut ausführen, um den echten Traceback zu sehen (eine defekte
  manuelle Änderung an `pyproject.toml` ist nach einem manuellen Merge
  meist die Ursache).
* **`docker compose up` bewirkt nichts Sinnvolles.** Das ist derzeit
  erwartet - die vier in `docker-compose.yml` referenzierten
  Kind-Dienste haben noch kein veröffentlichtes Dockerfile (jeder bietet
  bisher nur einen Python-Einstiegspunkt). Jeden Dienst während der
  Entwicklung direkt mit seinem eigenen `run.sh`/`run.bat` ausführen.

---

## 🚀 FAHRPLAN
* **Phase 1:** VLA-Engine-Bereitstellung und multimodale Eingabeverarbeitung auf Hailo-10.
* **Phase 2:** Integration des semantischen Planers mit Schwarmverhaltensmodellen und Langzeitgedächtnis.
* **Phase 3:** Lokale Ausführung der Voice-UI mit niedriger Latenz und industrielle Geräuschunterdrückung.
* **Phase 4:** Audits zur autonomen Entscheidungsfindung und vollständige Integration mit Dashboard AI für „See and Ask“-Feedback.

---

## 🔗 VERWANDTE PROJEKTE

Dieses Projekt ist Teil des HYDRA-UMC-Robotik-Ökosystems desselben Autors (JuanenRac / Electro Hobby 3D). Gut zu wissen, da eine Anfrage eigentlich eines dieser Projekte betreffen könnte statt dieses Repositorys.

**Untergeordnete Projekte** — jedes davon ist eine Stufe im eigenen kognitiven Ablauf dieses Knotens (Spracheingabe, Entscheidung, Aktion, Verankerung)
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — echtes Sprach-Frontend (VAD + Intent-Parser) mit einem begrenzten, bestätigungsgesicherten Watch-Relay.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — echte regelbasierte Aufgabenzerlegung und semantische Fehlerbehebung über MCU-Fehlercodes.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — echte Aktions-Token-Kodierung/-Dekodierung und Trajektoriengenerierung für ein Vision-Language-Action-Modell.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — echte, nur auf der Standardbibliothek basierende TF-IDF-Dokumentensuche über die eigenen Markdown-Dokumente dieses Ökosystems.

**Direkt verwandt**
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — Integrationsknoten mit einem echten gRPC/Protobuf-Health-Report-Vertrag und einer Missions-Zustandsmaschine; gibt diesem Knoten seine eigenen Missionsaufträge.
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — Integrationsknoten für die Hailo-8-Vision-Pipeline, mit einer echten stufenweisen Hardware-Bereitschaftsprüfung; die eigene semantische Schicht dieses Knotens konsumiert dessen Erkennungen.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — Web-Steuerungs-Dashboard mit Echtzeit-3D-Visualisierung mehrerer Roboter; eine der eigenen Sprachsteuerungsoberflächen dieses Knotens.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — native Touch-UI für das eingebaute 7"-DSI-Touchscreen, direkt auf dem CM5 eingebettet; die andere eigene Sprachsteuerungsoberfläche dieses Knotens.

**Ebenfalls Teil des Ökosystems**

*Kern-Hardware & Plattform*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — das physische Motherboard des Roboterarms: CM5-Host + Dual-Core-STM32H745, koordiniert bis zu 8 Werkzeugarme über CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — reproduzierbare Raspberry-Pi-OS-Produktschicht für den CM5: schreibgeschützter Agent, validierte Konfiguration/Profile, WiFi-Ersteinrichtung.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — der gemeinsame JSON-Schema-Vertrag und die Sicherheitsschranke, gegen die jede Bridge ihre Befehle validiert.

*Kern-Backend & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — das reale Headless-Backend (REST/WebSocket), mit dem jeder Steuerungsclient tatsächlich spricht.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — Desktop-Schwarmleitstand (PySide6) für mehrere Server gleichzeitig, verpackt als eigenständige ausführbare Datei.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — native Android-Steuerungs-App mit biometrischem Login und einer gekoppelten Wear-OS-Begleit-App.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — iOS/iPadOS-Steuerungs-App (Flutter) mit Echtzeit-WebSocket-Synchronisierung.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — grafischer Desktop-URDF-Ersteller/-Editor, der fertige Modelle in STUDIOs eigenen Katalog überträgt.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — Koordinationsschranke für AGV-/AMR-Flotten über einen echten VDA-5050-MQTT-Publisher.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — High-Level-Koordinator für CNC-Zellen mit echtem GRBL-Status-/Steuerbyte-Zugriff.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — Koordinationsschranke für laufende/humanoide Droiden, mit einem echten Boston-Dynamics-Spot-Befehlssender.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — Sicherheitskoordinator für Laserzellen, liest 3 echte Schlüssel-/Gehäuse-/Verriegelungs-GPIO-Sicherungen.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — sicherer High-Level-Koordinator für den Leiterplattenfluss von OpenPnP Pick-and-Place.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — sichere Koordinationsschranke für Moonraker/Klipper-3D-Drucker, mit echten gesicherten Job-Befehlen.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — Sicherheitskoordinator mit einem echten, träge importierten rclpy-ROS-2-Transport.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — Koordinationsschranke für kameraausgestattete UAVs, mit einem echten MAVLink-Befehlssender.

*URTC-Werkzeugplattform*
- **[URTC](https://github.com/JuanenRac/URTC)** — Firmware für die physische Universal-Robot-Tool-Controller-Platine, 25+ Werkzeugprofile über CAN-Bus.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — Desktop-GUI-Flash-Tool für URTC-Platinen, CAN-OTA plus Full-Chip-SWD/JTAG.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — Desktop-Live-CAN-Bus-Diagnosetool für URTC-Platinen, ein Panel pro Werkzeugprofil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — browserbasierte Alternative zu URTC-TESTER über die Web-Serial-API, ohne lokale Installation.

*Vision-KI-Knoten (Hailo-8)*
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — echte Registry für kompilierte Modelle mit Hailo-Architektur-/Prüfsummen-Safe-Load-Verifizierung.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — echter GStreamer-Pipeline- + MediaMTX-Konfigurationsgenerator mit einer echten HailoRT-Integrationsschranke.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — echtes Position-Based-Visual-Servoing-Korrekturgesetz, sicherheitsgesteuert nach vorgelagertem Zonenstatus.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — echte Zonenverletzungsprüfung und E-STOP-Anforderung, mit erzwungener Kalibrierungsaktualität.

*Orchestrierung & Schwarm*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — echte prioritätsbasierte Job-Queue mit Deduplizierung, über eine echte HTTP-API.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — echter gRPC-basierter Flotten-Health-Watchdog mit Retry/Backoff und Identitäts-Mismatch-Erkennung.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — echter RRT-basierter 3D-Pfadplaner mit echter Hindernis-/Arbeitsraum-Kollisionsvalidierung.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — echte CRDT-LWW-Element-Map-Zustandssynchronisation, eigenschaftsgetestet auf Multi-Zellen-Konvergenz.

*Digitaler Zwilling & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — Integrationsknoten für die Digital-Twin-Engine, mit einem echten Versionskompatibilitäts-Sync-Vertrag.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — echte Hardware-in-the-Loop-Sicherheitsverriegelung, die Befehle zwischen Simulation und echter Hardware routet.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — echte Vorwärtskinematik und Gelenkgrenzenvalidierung über eine echte URDF-Teilmenge.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — echter prozeduraler 2D-Szenengenerator mit YOLO/COCO-Annotationsexport.

*Daten & Analytik*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — echter sqlite3-gestützter Zeitreihenspeicher mit einer echten Ingest-/Abfrage-HTTP-API.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — echter FFT- + statistischer Basislinien-Anomaliedetektor mit Drift-Überwachung.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — echte OEE-/Verfügbarkeitsberechnung über den DATALAKE-Verlauf, mit reproduzierbarem CSV-Export.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — echte CAN/WebSocket-Ingestion-Pipeline in DATALAKE, mit Sequenz-Deduplizierung.

*Industrie-Gateway*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — Integrationsknoten, der zu Industrieprotokollen weiterleitet, mit einer echten Befehls-Allowlist-/Backpressure-Schicht.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — echter OPC-UA-Adressraum, verifiziert mit einer echten Binärprotokoll-Client-Session.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — echter MQTT-Broker mit optionaler Pro-Client-Authentifizierung und Topic-ACLs.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — echte MTConnect-`/probe`- und `/current`-XML-Endpunkte mit Degraded-Mode-Ausgabe.

*Ergänzende Tools & Ökosystembetrieb*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — Smart-Summaries- und Anomaly-Highlighting-Panels über DATALAKE/ANOMALY-DETECTOR, mit einem ehrlichen statistischen Fallback.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — Flotten-CLI mit einem echten, stabilen Exit-Code-Vertrag, ein echter Live-Client der eigenen API von HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — WearOS-Begleit-App mit echten haptischen Alarmen und einem Sprach-Relay zum gekoppelten Telefon.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — Firmware für ein Platinenmontagegestell mit echter Werkzeug-ID-Dekodierung und Smart-Idle-Vorheizlogik.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — Firmware plus ein echter Python-Vision-Begleiter für einen Thermal-/RGB-Inspektionswerkzeugkopf.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — administratives Desktop-Tool, das jedes Repository in diesem Ökosystem entdeckt, klont und aktualisiert.

---

## 📚 Dokumentation & Community

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — Technologie-Stack und Coding-Richtlinien für einen Pull Request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — die in dieser Community erwarteten Verhaltensstandards.
- **[SECURITY.md](SECURITY.md)** — wie man eine Schwachstelle meldet, und die echten Sicherheitsschwerpunkte dieses Projekts.
- **[SUPPORT.md](SUPPORT.md)** — wo man Fragen stellt und Fehler meldet.
- **[LICENSE.md](LICENSE.md)** — die eigene Lizenz dieses Projekts.

## 👤 AUTOR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LIZENZ
GPL-3.0 - Siehe LICENSE für Details.
