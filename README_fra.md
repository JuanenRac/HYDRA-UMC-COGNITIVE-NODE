<p align="center">
  <img src="images/HYDRA_UMC_BANNER.svg" alt="HYDRA-UMC-COGNITIVE-NODE banner" width="100%">
</p>

# 🧠 HYDRA-UMC-COGNITIVE-NODE

<p align="center"><a href="README.md">🇺🇸 English</a> | <a href="README_spa.md">🇪🇸 Español</a> | 🇫🇷 <b>Français</b> | <a href="README_ita.md">🇮🇹 Italiano</a> | <a href="README_deu.md">🇩🇪 Deutsch</a> | <a href="README_zho.md">🇨🇳 简体中文</a> | <a href="README_jpn.md">🇯🇵 日本語</a></p>

### 🤖 Nœud d'IA Edge pour Raisonnement Sémantique & GenAI (Hailo-10 + Raspberry Pi CM5)

<p align="left">
  <img src="https://img.shields.io/badge/Licence-GPL%203.0-blue.svg" alt="GPL 3.0">
  <img src="https://img.shields.io/badge/Matériel-CM5%20%2B%20Hailo--10-orange.svg" alt="CM5 + Hailo-10">
  <img src="https://img.shields.io/badge/Performance-40%20TOPS-green.svg" alt="40 TOPS">
  <img src="https://img.shields.io/badge/GenAI-Local%20LLM%20%2F%20VLA-blueviolet.svg" alt="GenAI">
</p>

---

## 1. 🛠️ APERÇU TECHNIQUE

**HYDRA-UMC-COGNITIVE-NODE** sert de « lobe frontal » de l'écosystème HYDRA-UMC. Propulsé par le NPU Hailo-10 (40 TOPS), il permet un raisonnement sémantique complexe, une compréhension du langage naturel et une planification de tâches vision-language-action (VLA) directement à la périphérie (edge).

Il transforme les instructions humaines de haut niveau en séquences robotiques logiques, gérant la récupération d'erreurs et l'optimisation des missions sans dépendance au cloud.

### Caractéristiques principales :
* 🧠 **Exécution de LLM locale :** Inférence accélérée matériellement pour les modèles quantifiés (Llama/Mistral). *(prévu - nécessite le vrai runtime de modèles Hailo-10)*
* 👁️ **Intégration VLA :** Modèles Vision-Language-Action pour une exécution intuitive des tâches. *(prévu)*
* 🎙️ **Traitement des commandes vocales :** STT/TTS en temps réel pour l'interaction homme-robot. *(prévu)*
* 🛡️ **Priorité à la confidentialité :** Traitement 100 % hors ligne de toutes les tâches cognitives. *(vrai par conception une fois ce qui précède en place - rien ici n'appelle un réseau aujourd'hui)*
* 🧩 **Hub d'intégration (v0) :** Détient l'image HydraOS partagée et les poids
  de modèles quantifiés consommés par ses 4 enfants, et les relie entre
  eux comme des services frères dans un seul `docker-compose.yml`. Le
  vrai contrôle `family-status` lit le manifeste réel de chaque enfant
  pour signaler présence/version/maturité. *(implémenté comme un vrai
  contrôle de disponibilité - voir BUILD ET EXÉCUTION ci-dessous)*
* 🔒 **Schéma de statut versionné + lectures de manifeste à ressources limitées :** `family-status --json` affiche un résultat réel, versionné et lisible par machine ; tout manifeste d'un frère dépassant 64 Kio (un checkout corrompu ou malveillant) se dégrade en « non trouvé » plutôt que d'être lu sans limite. *(implémenté)*
* 🪫 **Contrôle de dégradation des poids de modèle partagés :** `family-status` signale honnêtement si le répertoire `models/` propre à ce nœud contient réellement de vrais poids, et pas seulement si les dépôts frères sont clonés. *(implémenté)*
* 📦 **Versionnage compteur kilométrique :** Chaque build réel incrémente
  automatiquement la version de `pyproject.toml` (`bump_version.py`) - pas
  de modification manuelle de version.

---

## 2. 🔄 FLUX DE TRAVAIL COGNITIF

```mermaid
flowchart TB
    INPUT["Entrée vocale / textuelle"] --> VOICE["VOICE-UI (STT)"]
    VOICE --> PLANNER["SEMANTIC-PLANNER (LLM)"]
    VIS["Données du nœud Vision"] --> VLA["VLA-ENGINE"]
    VLA --> PLANNER
    PLANNER --> ORCH["HYDRA-ORCHESTRATOR"]
    DOCS["Manuels techniques"] --> RAG["DOCS-QA (RAG)"]
    RAG --> PLANNER
```

---

## 3. 🧱 ARCHITECTURE & DÉCISIONS DE CONCEPTION

Ce dépôt est le **point parent/d'intégration** de la famille Cognitive AI
Node. Il n'exécute aucun modèle lui-même - il détient les ressources
partagées et le câblage qui permettent à ses quatre enfants d'agir comme
une seule unité cognitive sur la même carte physique :

* **Pourquoi ce nœud n'a pas de matériel/firmware propre.** Contrairement
  au firmware au niveau de la carte mère HYDRA-UMC, ce nœud fonctionne
  entièrement sur un module Raspberry Pi CM5 + Hailo-10 M.2 déjà
  existant - il n'y a aucun PCB ou microcontrôleur propre à concevoir
  ici, donc les dossiers `hardware/`/`firmware/` ont été supprimés
  plutôt que laissés vides.
* **Pourquoi `os/` et `models/` ne vivent que dans le parent.** L'image
  HydraOS et les poids LLM/VLA quantifiés sont des ressources partagées
  au niveau de la carte - garder une seule copie dans le parent et la
  monter en lecture seule dans chaque conteneur enfant (voir
  `docker-compose.yml`) évite quatre copies divergentes de poids de
  plusieurs gigaoctets.
* **Pourquoi une structure `src/`.** Sépare le paquet installable
  (`hydra_umc_cognitive_node`) de l'outillage à la racine du dépôt
  (`bump_version.py`, `docker-compose.yml`), conformément au reste des
  projets Python de l'écosystème.
* **Pourquoi le point d'entrée se contente d'afficher
  identité/version/rôle aujourd'hui.** C'est l'étape d'échafaudage :
  prouver que le paquet s'installe, se compile et s'importe correctement
  - sur la version Python cible réelle - est un prérequis avant d'ajouter
  une vraie logique d'orchestration LLM/VLA/vocale, et isole ce travail
  ultérieur des préoccupations d'empaquetage.
* **Pourquoi `docker-compose.yml` existe avant que les enfants n'aient de
  Dockerfile.** Décider et documenter le contrat d'intégration (quel
  service dépend de quel autre, quels montages de périphérique/volume
  chacun nécessite) dès maintenant évite que cette forme soit inventée
  plus tard de manière improvisée, même si `docker compose up` ne peut
  pas pleinement réussir tant que chaque enfant n'a pas publié son propre
  Dockerfile.
* **Comment cela s'intègre dans le reste de l'écosystème.** Ce nœud se
  situe une couche au-dessus de la perception (HYDRA-UMC-VISION-NODE,
  Hailo-8) et une couche en dessous de l'orchestration de mission
  (HYDRA-UMC-ORCHESTRATOR) : il transforme les instructions vocales/
  textuelles et les détections en décisions sémantiques, que
  l'orchestrateur transforme ensuite en commandes physiques pour les
  robots.
* **Pourquoi `family-status` lit le manifeste propre de chaque enfant
  plutôt qu'une liste tenue à la main.** `hydra-umc.project.json` est déjà
  la source unique de vérité en laquelle le tableau de bord et l'updater
  de tout l'écosystème ont confiance -
  une seconde liste ici dériverait dès qu'un enfant changerait réellement
  de maturité sans que personne ne pense à la mettre à jour.
* **Pourquoi un enfant sans checkout local est un « non trouvé » réel et
  honnête, pas une erreur.** Un hub d'intégration ne sait réellement pas
  si un développeur a cloné localement les quatre enfants -
  `manifest.py` renvoie `None` pour chaque échec réel (dépôt absent,
  manifeste absent, JSON malformé) afin que `family-status` le signale
  clairement plutôt que de planter.
* **Pourquoi les lectures de manifeste d'un frère sont plafonnées à
  64 Kio.** Chaque manifeste réel de cet écosystème pèse de quelques
  centaines d'octets à quelques Kio - un checkout corrompu ou malveillant
  dont le manifeste aurait été remplacé par un fichier surdimensionné ne
  doit jamais faire charger en mémoire une quantité illimitée de données
  par un simple contrôle de disponibilité de routine. Il se dégrade en
  `None`, comme tout autre manifeste malformé.
* **Pourquoi `family-status` signale `models/` alors que ce nœud
  n'exécute lui-même aucun modèle.** « Les dépôts frères sont clonés »
  et « les poids partagés dont ils auraient besoin sont réellement
  présents » sont deux faits réels distincts - `check_shared_models()`
  de `models.py` vérifie honnêtement le second (vide mais présent compte
  comme manquant) plutôt que de laisser un opérateur présumer de la
  disponibilité à partir de la seule présence des enfants.

---

## 📂 STRUCTURE DES RÉPERTOIRES

```text
HYDRA-UMC-COGNITIVE-NODE/
├── src/hydra_umc_cognitive_node/
│   ├── manifest.py                 # Lecteur réel et défensif du manifeste propre d'un frère (plafonné à 64 Kio)
│   ├── models.py                   # Contrôle réel du répertoire de poids de modèle partagés propre à ce nœud
│   ├── family.py                    # Vrai contrôle de disponibilité de famille + schéma JSON versionné
│   ├── api.py                         # Surface JSON/HTTP simple (http.server de stdlib) sur `family-status`
│   └── main.py                        # Point d'entrée + sous-commandes réelles `family-status [--json]` et `serve`
├── tests/                          # Tests réels : lecture de manifeste, modèles, statut de famille, api, CLI de bout en bout
├── docs/
│   └── CLI_REFERENCE.md            # Référence complète des commandes : chaque option, sortie réelle capturée, codes de sortie
├── os/                             # Image/configuration HydraOS pour le CM5 - peuplé au déploiement (absent de git)
├── models/                         # Poids optimisés Hailo-10 (LLM/VLA, partagés par les 4 enfants) - peuplé au déploiement (absent de git)
├── images/                         # Médias et diagrammes
├── systemd/
│   └── hydra-umc-cognitive-node.service # Unité systemd de l'API locale family-status sur la CM5
├── tools/
│   ├── build_test.py               # Vérification de build sans versionnage
│   └── ci_validate.py              # Validation manifeste/CHANGELOG/docs utilisée par CI
├── build/                          # Sortie de build locale (ignorée par git)
├── pyproject.toml                  # Métadonnées du paquet (version à incrément type compteur kilométrique)
├── bump_version.py                 # Incrément de version native type compteur kilométrique (utilisé par build.sh/.bat)
├── bump_manifest_version.py        # Synchronise la version de hydra-umc.project.json avec la version native (--sync)
├── docker-compose.yml              # Carte d'intégration des 4 services enfants
├── build.sh / build.bat            # Crée le venv, installe (avec extras dev), exécute les tests, vérifie l'import
└── run.sh / run.bat                # Exécute le point d'entrée (transmet les arguments, ex. `family-status`)
```

> **Remarque :** `hardware/` et `firmware/` ont été supprimés - ce nœud
> fonctionne sur un module CM5 + Hailo-10 M.2 déjà existant, sans
> conception matérielle/firmware propre. Un microcontrôleur auxiliaire
> dédié pourra être ajouté plus tard si cela devient nécessaire.

---

## ⚙️ BUILD ET EXÉCUTION

Nécessite Python >= 3.10.

```bash
# Linux / macOS / Git Bash
./build.sh   # crée .venv, installe le paquet (éditable), vérifie l'import
./run.sh     # exécute le point d'entrée

# Windows (cmd)
build.bat
run.bat
```

`build.sh`/`build.bat` incrémentent la version (type compteur
kilométrique, voir `bump_version.py`) avant chaque build réel, et
exécutent la vraie suite de tests (`pytest tests/`). Sortie attendue
d'un `run.sh` sans argument :

```text
HYDRA-UMC-COGNITIVE-NODE v0.0.8
Semantic reasoning & GenAI edge node (Hailo-10) - integrates VLA-Engine, Voice-UI, Semantic-Planner and Docs-QA into one cognitive node.
```

Voir `docker-compose.yml` pour savoir comment les quatre services enfants
(VLA-Engine, Voice-UI, Semantic-Planner, Docs-QA) se rattachent à ce nœud
une fois que chacun publie son propre Dockerfile.

La vraie sous-commande `family-status` vérifie les vrais enfants dans un
vrai checkout local :

```bash
./run.sh family-status
./run.sh family-status --workspace /chemin/vers/un/autre/checkout
./run.sh family-status --json

# Windows
run.bat family-status
```

`family-status` signale toujours aussi les poids de modèle partagés
propres à ce nœud - un `models/` réel et vide sur une machine de
développement est honnêtement `MISSING`, jamais ignoré en silence :

```text
Cognitive AI Node family status (workspace: /path/to/workspace):
  HYDRA-UMC-VLA-ENGINE: v0.1.0, maturity=established, role=service
  ...

Shared model weights: MISSING (.../HYDRA-UMC-COGNITIVE-NODE/models) - this node's own os/models weights have not been provisioned on this machine; children that need them will run in their own honest degraded/no-hardware mode.

All 4 children present.
```

`--json` affiche à la place les mêmes données réelles sous forme d'un
objet versionné et lisible par machine :

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

Par défaut, utilise le propre répertoire parent de ce dépôt - la même
disposition que tout checkout réel de cet écosystème utilise déjà (tous
les dépôts en frères sous un même dossier de workspace). Se termine avec
`1` si un vrai enfant manque.

### 🌐 API HTTP (`serve`)

`serve` exécute cette même vérification `family-status` sous la forme
d'un petit `http.server` de la bibliothèque standard, au lieu d'un appel
CLI ponctuel - c'est la commande réelle que l'unit systemd
`hydra-umc-cognitive-node.service` du CM5 exécute en production :

```bash
./run.sh serve --addr 127.0.0.1 --port 8096
# GET /family-status  -> le même JSON que celui affiché par `family-status --json` ci-dessus
# GET /stats          -> { "workspace": "<workspace configuré par défaut>" }
```

`GET /family-status` accepte un `?workspace=` optionnel pour le
remplacer ; tout autre chemin renvoie `404`. Voir la
[Référence CLI](docs/CLI_REFERENCE.md) pour la référence complète des
commandes : chaque option, la sortie réelle capturée de `-h`/`curl`, et
le tableau des codes de sortie.

### 🩺 Dépannage

* **`python : commande introuvable` / le build échoue à l'étape 1.**
  Nécessite Python >= 3.10 dans le `PATH`. Sous Windows, installez-le
  depuis [python.org](https://python.org) et cochez "Add to PATH" lors de
  l'installation ; sous Linux/macOS, c'est généralement `python3`.
* **`build.sh` n'arrive pas à activer le venv.** `python3 -m venv .venv`
  place le script d'activation à un emplacement différent selon la
  plateforme : `.venv/bin/activate` sous Linux/macOS,
  `.venv/Scripts/activate` sous Windows (également pour un venv Python
  Windows utilisé depuis Git Bash). `build.sh` vérifie déjà les deux
  chemins - si cela échoue toujours, supprimez `.venv/` et relancez
  `./build.sh` pour le reconstruire entièrement.
* **`pip install -e .` échoue.** Généralement dû à un `.venv/` obsolète.
  Supprimez le dossier `.venv/` et relancez `./build.sh`/`build.bat` pour
  le recréer.
* **`import OK` ne s'affiche jamais.** Signifie que `python -c "import
  hydra_umc_cognitive_node"` a lui-même échoué - relancez avec le venv
  actif pour voir la vraie trace d'erreur (une modification manuelle
  cassée de `pyproject.toml` est la cause habituelle après une fusion
  manuelle).
* **`docker compose up` ne fait rien d'utile.** C'est normal pour
  l'instant - les quatre services enfants référencés dans
  `docker-compose.yml` n'ont pas encore de Dockerfile publié (chacun ne
  fournit pour l'instant qu'un point d'entrée Python). Lancez chaque
  service directement avec son propre `run.sh`/`run.bat` pendant le
  développement.

---

## 🚀 FEUILLE DE ROUTE
* **Phase 1 :** Déploiement du moteur VLA et traitement des entrées multimodales sur Hailo-10.
* **Phase 2 :** Intégration du planificateur sémantique avec des modèles de comportement en essaim et une mémoire à long terme.
* **Phase 3 :** Exécution locale à faible latence de l'interface vocale et suppression du bruit industriel.
* **Phase 4 :** Audits de prise de décision autonomes et intégration complète avec Dashboard AI pour le retour « Voir et demander ».

---

## 🔗 PROJETS LIÉS

Ce projet fait partie de l'écosystème robotique HYDRA-UMC du même auteur (JuanenRac / Electro Hobby 3D). Bon à savoir, car une demande pourrait en réalité concerner l'un de ceux-ci plutôt que ce dépôt.

**Projets Enfants** — chacun est une étape du propre flux cognitif de ce nœud (entrée vocale, décision, action, ancrage)
- **[HYDRA-UMC-VOICE-UI](https://github.com/JuanenRac/HYDRA-UMC-VOICE-UI)** — vrai front-end vocal (VAD + analyseur d'intention) avec un relais Watch borné et soumis à confirmation.
- **[HYDRA-UMC-SEMANTIC-PLANNER](https://github.com/JuanenRac/HYDRA-UMC-SEMANTIC-PLANNER)** — vraie décomposition de tâches basée sur des règles et récupération sémantique d'erreurs sur les codes d'erreur MCU.
- **[HYDRA-UMC-VLA-ENGINE](https://github.com/JuanenRac/HYDRA-UMC-VLA-ENGINE)** — vrai encodage/décodage de jetons d'action et génération de trajectoire pour un modèle Vision-Language-Action.
- **[HYDRA-UMC-DOCS-QA](https://github.com/JuanenRac/HYDRA-UMC-DOCS-QA)** — vraie recherche documentaire TF-IDF (bibliothèque standard uniquement) sur les propres documents Markdown de cet écosystème.

**Directement Liés**
- **[HYDRA-UMC-ORCHESTRATOR](https://github.com/JuanenRac/HYDRA-UMC-ORCHESTRATOR)** — hub d'intégration avec un vrai contrat de rapport de santé gRPC/Protobuf et une machine à états de mission ; c'est lui qui donne à ce nœud ses propres ordres de mission.
- **[HYDRA-UMC-VISION-NODE](https://github.com/JuanenRac/HYDRA-UMC-VISION-NODE)** — hub d'intégration pour le pipeline de vision Hailo-8, avec une vraie vérification de disponibilité matérielle par étape ; la propre couche sémantique de ce nœud consomme ses détections.
- **[HYDRA-UMC-STUDIO](https://github.com/JuanenRac/HYDRA-UMC-STUDIO)** — tableau de bord de contrôle web avec visualisation 3D multi-robot en temps réel ; l'une des propres surfaces de contrôle vocal de ce nœud.
- **[HYDRA-UMC-DSI](https://github.com/JuanenRac/HYDRA-UMC-DSI)** — interface tactile native pour l'écran tactile DSI 7" embarqué, intégrée directement sur le CM5 ; l'autre propre surface de contrôle vocal de ce nœud.

**Fait Également Partie de l'Écosystème**

*Matériel & Plateforme de Base*
- **[HYDRA-UMC](https://github.com/JuanenRac/HYDRA-UMC)** — la carte mère physique du bras robotique : hôte CM5 + coprocesseur STM32H745 double cœur, coordonnant jusqu'à 8 bras-outils via CAN-OTA/SPI-OTA.
- **[HYDRA-UMC-OS](https://github.com/JuanenRac/HYDRA-UMC-OS)** — couche produit reproductible sur Raspberry Pi OS pour le CM5 : agent en lecture seule, config/profils validés, provisionnement WiFi de premier contact.
- **[HYDRA-UMC-SDK](https://github.com/JuanenRac/HYDRA-UMC-SDK)** — le contrat JSON-Schema partagé et la barrière de sécurité contre laquelle chaque bridge valide ses commandes.

*Backend Central & Clients*
- **[HYDRA-UMC-SERVER](https://github.com/JuanenRac/HYDRA-UMC-SERVER)** — le vrai backend headless (REST/WebSocket) auquel parle réellement chaque client de contrôle.
- **[HYDRA-UMC-SUITE](https://github.com/JuanenRac/HYDRA-UMC-SUITE)** — centre de commande d'essaim de bureau (PySide6) pour plusieurs serveurs à la fois, empaqueté en exécutable autonome.
- **[HYDRA-UMC-ANDROID-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-ANDROID-CONTROL)** — application de contrôle Android native avec connexion biométrique et un compagnon Wear OS jumelé.
- **[HYDRA-UMC-IOS-CONTROL](https://github.com/JuanenRac/HYDRA-UMC-IOS-CONTROL)** — application de contrôle iOS/iPadOS (Flutter) avec synchronisation WebSocket en temps réel.
- **[HYDRA-UMC-EDITOR-URDF](https://github.com/JuanenRac/HYDRA-UMC-EDITOR-URDF)** — créateur/éditeur graphique de bureau pour URDF qui envoie les modèles terminés vers le propre catalogue de STUDIO.
- **[HYDRA-UMC-BRIDGE-AMR](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-AMR)** — frontière de coordination pour les flottes AGV/AMR via un éditeur MQTT VDA 5050 réel.
- **[HYDRA-UMC-BRIDGE-CNC](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-CNC)** — coordinateur haut niveau pour cellules CNC avec accès réel au statut/octets de contrôle GRBL.
- **[HYDRA-UMC-BRIDGE-DROIDS](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-DROIDS)** — frontière de coordination pour droïdes à pattes/humanoïdes, avec un véritable émetteur de commandes Boston Dynamics Spot.
- **[HYDRA-UMC-BRIDGE-LASER](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-LASER)** — coordinateur de sécurité pour cellules laser lisant 3 vraies sécurités GPIO de clé/enceinte/verrouillage.
- **[HYDRA-UMC-BRIDGE-OPENPNP](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-OPENPNP)** — coordinateur haut niveau sûr pour le flux de cartes du pick-and-place OpenPnP.
- **[HYDRA-UMC-BRIDGE-PRINTER3D](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-PRINTER3D)** — frontière de coordination sûre pour imprimantes 3D Moonraker/Klipper, avec de vraies commandes de tâche contrôlées.
- **[HYDRA-UMC-BRIDGE-ROS2](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-ROS2)** — coordinateur de sécurité avec un vrai transport ROS 2 rclpy à importation paresseuse.
- **[HYDRA-UMC-BRIDGE-UAV](https://github.com/JuanenRac/HYDRA-UMC-BRIDGE-UAV)** — frontière de coordination pour UAV équipés de caméra, avec un véritable émetteur de commandes MAVLink.

*Plateforme d'Outils URTC*
- **[URTC](https://github.com/JuanenRac/URTC)** — firmware pour la carte physique Universal Robot Tool Controller, plus de 25 profils d'outil sur bus CAN.
- **[URTC-FLASHER](https://github.com/JuanenRac/URTC-FLASHER)** — outil de bureau à interface graphique pour flasher les cartes URTC, CAN-OTA plus SWD/JTAG puce complète.
- **[URTC-TESTER](https://github.com/JuanenRac/URTC-TESTER)** — outil de bureau de diagnostic CAN-bus en direct pour cartes URTC, un panneau par profil d'outil.
- **[URTC-WEB-STUDIO](https://github.com/JuanenRac/URTC-WEB-STUDIO)** — alternative basée navigateur à URTC-TESTER via la Web Serial API, sans installation locale.

*Nœud IA de Vision (Hailo-8)*
- **[HYDRA-UMC-DETECTION-HEF](https://github.com/JuanenRac/HYDRA-UMC-DETECTION-HEF)** — registre réel de modèles compilés avec vérification de chargement sécurisé par architecture Hailo/checksum.
- **[HYDRA-UMC-VISION-STREAMER](https://github.com/JuanenRac/HYDRA-UMC-VISION-STREAMER)** — générateur réel de pipeline GStreamer + config MediaMTX, avec une vraie frontière d'intégration HailoRT.
- **[HYDRA-UMC-VISUAL-SERVOING-API](https://github.com/JuanenRac/HYDRA-UMC-VISUAL-SERVOING-API)** — vraie loi de correction Position-Based Visual Servoing, verrouillée sur l'état de zone en amont.
- **[HYDRA-UMC-SAFETY-ZONES](https://github.com/JuanenRac/HYDRA-UMC-SAFETY-ZONES)** — vraie vérification de violation de zone et demande d'E-STOP, avec application de la fraîcheur de calibration.

*Orchestration & Essaim*
- **[HYDRA-UMC-JOB-DISPATCHER](https://github.com/JuanenRac/HYDRA-UMC-JOB-DISPATCHER)** — vraie file de tâches basée sur la priorité avec déduplication, via une vraie API HTTP.
- **[HYDRA-UMC-NODE-HEALING](https://github.com/JuanenRac/HYDRA-UMC-NODE-HEALING)** — vrai chien de garde de santé de flotte basé sur gRPC, avec retry/backoff et détection d'incohérence d'identité.
- **[HYDRA-UMC-PATH-PLANNER-3D](https://github.com/JuanenRac/HYDRA-UMC-PATH-PLANNER-3D)** — vrai planificateur de trajectoire 3D basé sur RRT, avec vraie validation des collisions obstacle/espace de travail.
- **[HYDRA-UMC-SWARM-SYNC](https://github.com/JuanenRac/HYDRA-UMC-SWARM-SYNC)** — vraie synchronisation d'état CRDT LWW-Element-Map, testée par propriétés pour la convergence multi-cellule.

*Jumeau Numérique & Simulation*
- **[HYDRA-UMC-TWIN](https://github.com/JuanenRac/HYDRA-UMC-TWIN)** — hub d'intégration pour le moteur de jumeau numérique, avec un vrai contrat de synchronisation par compatibilité de version.
- **[HYDRA-UMC-HIL-BRIDGE](https://github.com/JuanenRac/HYDRA-UMC-HIL-BRIDGE)** — vrai verrouillage de sécurité hardware-in-the-loop routant les commandes entre simulation et matériel réel.
- **[HYDRA-UMC-PHYSICS-REPLICA](https://github.com/JuanenRac/HYDRA-UMC-PHYSICS-REPLICA)** — vraie cinématique directe et validation des limites articulaires sur un vrai sous-ensemble URDF.
- **[HYDRA-UMC-SYNTHETIC-DATA-GEN](https://github.com/JuanenRac/HYDRA-UMC-SYNTHETIC-DATA-GEN)** — vrai générateur procédural de scènes 2D avec export d'annotations YOLO/COCO.

*Données & Analytique*
- **[HYDRA-UMC-DATALAKE](https://github.com/JuanenRac/HYDRA-UMC-DATALAKE)** — vrai magasin de séries temporelles basé sur sqlite3, avec une vraie API HTTP d'ingestion/requête.
- **[HYDRA-UMC-ANOMALY-DETECTOR](https://github.com/JuanenRac/HYDRA-UMC-ANOMALY-DETECTOR)** — vrai détecteur d'anomalies FFT + ligne de base statistique, avec surveillance de dérive.
- **[HYDRA-UMC-PRODUCTION-REPORTS](https://github.com/JuanenRac/HYDRA-UMC-PRODUCTION-REPORTS)** — vrai calcul OEE/disponibilité sur l'historique de DATALAKE, avec export CSV reproductible.
- **[HYDRA-UMC-TELEMETRY-COLLECTOR](https://github.com/JuanenRac/HYDRA-UMC-TELEMETRY-COLLECTOR)** — vrai pipeline d'ingestion CAN/WebSocket vers DATALAKE, avec déduplication par séquence.

*Passerelle Industrielle*
- **[HYDRA-UMC-GATEWAY-INDUSTRIAL](https://github.com/JuanenRac/HYDRA-UMC-GATEWAY-INDUSTRIAL)** — hub d'intégration relayant vers les protocoles industriels, avec une vraie couche de liste blanche de commandes/contre-pression.
- **[HYDRA-UMC-OPCUA-SERVER](https://github.com/JuanenRac/HYDRA-UMC-OPCUA-SERVER)** — vrai espace d'adressage OPC-UA, vérifié avec une vraie session client du protocole binaire.
- **[HYDRA-UMC-MQTT-BROKER](https://github.com/JuanenRac/HYDRA-UMC-MQTT-BROKER)** — vrai broker MQTT avec authentification par client optionnelle et ACL de sujets.
- **[HYDRA-UMC-MTCONNECT-ADAPTER](https://github.com/JuanenRac/HYDRA-UMC-MTCONNECT-ADAPTER)** — vrais points de terminaison XML MTConnect `/probe` et `/current`, avec sortie en mode dégradé.

*Outils Complémentaires & Opérations de l'Écosystème*
- **[HYDRA-UMC-DASHBOARD-AI](https://github.com/JuanenRac/HYDRA-UMC-DASHBOARD-AI)** — panneaux Smart Summaries et Anomaly Highlighting sur DATALAKE/ANOMALY-DETECTOR, avec un repli statistique honnête.
- **[HYDRA-UMC-TOOL-CLI](https://github.com/JuanenRac/HYDRA-UMC-TOOL-CLI)** — CLI de flotte avec un vrai contrat de codes de sortie stable, un vrai client en direct de la propre API de HYDRA-UMC-SERVER.
- **[HYDRA-UMC-WATCH](https://github.com/JuanenRac/HYDRA-UMC-WATCH)** — application compagnon WearOS avec de vraies alertes haptiques et un relais vocal vers le téléphone jumelé.
- **[URTC-SMART-RACK](https://github.com/JuanenRac/URTC-SMART-RACK)** — firmware pour un rack de montage de cartes avec décodage réel d'ID d'outil et logique de préchauffage Smart Idle.
- **[URTC-VISION-TOOL](https://github.com/JuanenRac/URTC-VISION-TOOL)** — firmware plus un vrai compagnon de vision Python pour une tête d'outil d'inspection thermique/RGB.
- **[HYDRA-UMC-UPDATER](https://github.com/JuanenRac/HYDRA-UMC-UPDATER)** — outil administratif de bureau qui découvre, clone et met à jour chaque dépôt de cet écosystème.

---

## 📚 Documentation & Communauté

- **[CONTRIBUTING.md](CONTRIBUTING.md)** — pile technologique et lignes directrices de codage pour une pull request.
- **[CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md)** — les normes de comportement attendues dans cette communauté.
- **[SECURITY.md](SECURITY.md)** — comment signaler une vulnérabilité, et les véritables axes de sécurité de ce projet.
- **[SUPPORT.md](SUPPORT.md)** — où poser des questions et signaler des bugs.
- **[LICENSE.md](LICENSE.md)** — la licence propre de ce projet.

## 👤 AUTEUR
**JuanenRac** (Electro Hobby 3D)
📧 electrohobby3d@gmail.com
📺 [youtube.com/@electrohobby3d](https://youtube.com/@electrohobby3d)

## 📜 LICENCE
GPL-3.0 - Voir le fichier LICENSE pour plus de détails.
