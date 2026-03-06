# 🏥 Écosystème DICOM Medical Suite

[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://www.python.org/)
[![PowerShell](https://img.shields.io/badge/PowerShell-5.1+-blue.svg)](https://github.com/PowerShell/PowerShell)
[![DICOM](https://img.shields.io/badge/DICOM-Standard-green.svg)](https://www.dicomstandard.org/)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Suite complète d'outils DICOM pour échographie thyroïdienne : worklist, archivage, et génération automatique de comptes rendus

---

## 📋 Vue d'ensemble

Cette suite intègre 3 projets complémentaires formant un workflow médical complet pour l'échographie thyroïdienne :

```
┌─────────────────────────────────────────────────────────────────────────┐
│                        WORKFLOW MÉDICAL COMPLET                          │
└─────────────────────────────────────────────────────────────────────────┘

  1. PLANIFICATION                2. ACQUISITION               3. ARCHIVAGE
  ┌──────────────┐               ┌──────────────┐            ┌──────────────┐
  │  Doctolib    │   CSV         │ Échographe   │   DICOM    │ DICOMStore   │
  │  (Export)    │───────►       │   GE Logiq   │   C-STORE  │  (Port 4243) │
  └──────────────┘               └──────┬───────┘  ─────────►└──────────────┘
         │                              │                             │
         │ Parse CSV                    │ DICOM Worklist              │ Export
         ▼                              │ Query/Retrieve              │ PNG/JPEG
  ┌──────────────┐                     │                             ▼
  │DICOMWorklist │◄────────────────────┘                     ┌──────────────┐
  │ (Port 4242)  │                                           │DICOM_Archive/│
  └──────────────┘                                           └──────┬───────┘
                                                                    │
  4. TRAITEMENT & GÉNÉRATION CR                                      │
  ┌──────────────────────────────────────────────────────────────┐   │
  │              EchoThyr-Python (Surveillance)                   │   │
  │                                                               │   │
  │  ┌────────┐   DICOM    ┌───────────┐                         │   │
  │  │ Watch  │◄───────────│  Archive  │◄────────────────────────┘   │
  │  │ Folder │            └─────┬─────┘                             │
  │  └────────┘                  │                                   │
  │                    ┌─────────┴─────────┐                         │
  │                    │                   │                          │
  │              ┌─────▼─────┐     ┌───────▼───────┐                 │
  │              │ SR Parser │     │  OCR Engine   │                 │
  │              │(Structured│     │(Tesseract sur │                 │
  │              │  Report)  │     │ pixels DICOM) │                 │
  │              └─────┬─────┘     └───────┬───────┘                 │
  │                    │                   │                          │
  │              ┌─────▼───────────────────▼─────┐                   │
  │              │     Hybrid Matcher            │                   │
  │              │  (SR values + OCR context)    │                   │
  │              └──────────────┬────────────────┘                   │
  │                             │                                    │
  │                      ┌──────▼──────┐                             │
  │                      │  Word/PDF   │                             │
  │                      │  Generator  │                             │
  │                      └─────────────┘                             │
  └──────────────────────────────────────────────────────────────┘
         │
         ▼
  Compte Rendu Final (Word + PDF)
```

---

## 🎯 Projets inclus

| Projet | Description | Port | Statut |
|--------|-------------|------|--------|
| **[DICOMWorklist](DICOMWorklist/)** | Serveur DICOM Modality Worklist - Sync Doctolib → Échographe | 4242 | ✅ Production |
| **[DICOMStore](DICOMStore/)** | Serveur d'archivage DICOM (PACS local) + Viewer Web | 4243 | ✅ Production |
| **[EchoThyr-Python](EchoThyr-Python/)** | Génération automatique de CR : hybride SR + OCR sur DICOM brut | - | ✅ Production |
| **[legacy/EchoThyr-PowerShell](legacy/EchoThyr-PowerShell/)** | Version PowerShell historique (archivée) | - | 📦 Archived |

---

## 🚀 Démarrage rapide

### Prérequis système

- **Windows** 10/11 ou Server 2016+
- **Python** 3.8+ ([télécharger](https://www.python.org/downloads/))
- **Tesseract OCR** 5.0+ ([télécharger](https://github.com/UB-Mannheim/tesseract/wiki))
- **Microsoft Word** 2016+ (pour génération CR)
- **Échographe GE Logiq** (P9/E9/etc.) avec DICOM activé

### Installation

#### 1. Cloner le dépôt

```bash
cd C:\Users\VotreNom\Desktop
git clone https://github.com/ES-Vibe/Medical-DICOM-Suite.git Claude
cd Claude
```

#### 2. Installer les dépendances Python

```bash
# DICOMWorklist
cd DICOMWorklist
pip install -r requirements.txt
cd ..

# DICOMStore
cd DICOMStore
pip install -r requirements.txt
cd ..

# EchoThyr-Python
cd EchoThyr-Python
pip install -r requirements.txt
cd ..
```

#### 3. Configuration échographe GE Logiq

**Pour le Worklist (liste patients)** :
1. Menu échographe → **DICOM** → **Worklist** → **Configuration**
2. **Add Server** :
   - AE Title : `WORKLIST`
   - IP Address : `[IP de votre PC]`
   - Port : `4242`
3. **Test Connection** → OK

**Pour le Storage (archivage images)** :
1. Menu échographe → **DICOM** → **Store** → **Configuration**
2. **Add Server** :
   - AE Title : `PACS_LOCAL`
   - IP Address : `[IP de votre PC]`
   - Port : `4243`
3. **Test Connection** → OK

**Trouver l'IP de votre PC** :
```cmd
ipconfig
```
Cherchez l'adresse IPv4 (ex: `192.168.1.100`)

#### 4. Configuration pare-feu Windows

```cmd
# Autoriser port Worklist
netsh advfirewall firewall add rule name="DICOM Worklist" dir=in action=allow protocol=TCP localport=4242

# Autoriser port Storage
netsh advfirewall firewall add rule name="DICOM Storage" dir=in action=allow protocol=TCP localport=4243
```

---

## 📖 Utilisation quotidienne

### Scénario type d'une journée d'échographies

#### Matin - Préparation

1. **Exporter les RDV Doctolib** :
   - Connectez-vous à Doctolib Pro
   - Menu → Agenda → Export
   - Téléchargez le CSV du jour

2. **Démarrer les serveurs DICOM** :
   ```
   Double-clic : DICOMWorklist\Lancer_Worklist.bat
   Double-clic : DICOMStore\Lancer_PACS.bat
   ```

3. **Démarrer la surveillance CR automatique** :
   ```
   Double-clic : EchoThyr-Python\Lancer_EchoThyr.bat
   ```

#### Pendant les consultations

1. Sur l'échographe, appuyez sur **Worklist** → **Query**
2. La liste des patients du jour apparaît
3. Sélectionnez le patient → commence l'examen
4. Prenez les clichés échographiques
5. À la fin, appuyez sur **Store** → Images envoyées automatiquement

#### Automatique - Génération des CR

Dès que les images sont archivées, EchoThyr détecte et traite automatiquement via **3 voies de détection** :

| Voie | Condition | Méthode |
|------|-----------|---------|
| **SR-only** | Outil "Thyroid Volume" GE utilisé | Mesures directement depuis le Structured Report DICOM |
| **Hybride SR+OCR** | Outil "Volume" générique GE utilisé | Valeurs SR + contexte OCR (côté, nodule) depuis pixels DICOM bruts |
| **OCR-only** | Pas de SR reçu | Extraction complète par Tesseract sur pixels DICOM (pleine résolution) |

Fonctionnalités :
- **Matching hybride 4 passes** : volume, dimensions complètes, dimensions partielles + côté, isthme
- **Détection nodules** : N1, N2... et format GE N1D/N1G (suffixe Droit/Gauche)
- **Calcul volume** : formule ellipsoïde (pi/6 x H x W x L) si absent du SR
- **OCR sur DICOM brut** : pixels natifs pleine résolution (pas de compression JPEG)
- **Gestion misreads OCR** : Ni/Nl reconnus comme N1 (confusion Tesseract 1/i/l)
- **Attente SR** : 20s après réception images (race condition échographe)
- Génération Word (python-docx) + export PDF automatique

---

## 📁 Structure du dépôt

```
Claude/
│
├── DICOMWorklist/              # Serveur Worklist (Doctolib → Échographe)
│   ├── main.py                 # Point d'entrée
│   ├── worklist_server.py      # Serveur DICOM MWL
│   ├── doctolib_parser.py      # Parser CSV Doctolib
│   ├── config.yaml             # Configuration
│   ├── requirements.txt        # Dépendances Python
│   ├── Lancer_Worklist.bat     # Lanceur Windows
│   └── README.md               # Documentation détaillée
│
├── DICOMStore/                 # Serveur Storage + Viewer (Archivage)
│   ├── main.py                 # Point d'entrée
│   ├── storage_server.py       # Serveur DICOM C-STORE
│   ├── web_viewer.py           # Viewer web basique
│   ├── web_viewer_pro.py       # Viewer web avancé
│   ├── config.yaml             # Configuration
│   ├── requirements.txt        # Dépendances Python
│   ├── DICOM_Archive/          # Archive des images (non versionné)
│   ├── Lancer_PACS.bat         # Lanceur serveur Storage
│   ├── Lancer_Viewer.bat       # Lanceur viewer web
│   └── README.md               # Documentation détaillée
│
├── EchoThyr-Python/            # Génération automatique CR (v3.0 - Hybride SR+OCR)
│   ├── main.py                 # Point d'entrée + orchestration 3 voies
│   ├── config.yaml             # Configuration externe
│   ├── requirements.txt        # Dépendances Python
│   │
│   ├── src/                    # Code source modulaire
│   │   ├── dicom/              # Lecture DICOM native
│   │   │   ├── dicom_reader.py # Extraction pixels + métadonnées patient
│   │   │   └── sr_parser.py    # Parser Structured Reports GE (XML tag 0x6005,0x1010)
│   │   ├── hybrid/             # Matching hybride SR + OCR
│   │   │   └── matcher.py      # 4 passes : volume, dims, partiel+côté, isthme
│   │   ├── ocr/                # Extraction mesures OCR
│   │   │   └── tesseract_engine.py  # OCR sur PIL Image (DICOM brut)
│   │   ├── document/           # Génération Word/PDF
│   │   │   ├── word_generator.py    # python-docx (template replacement)
│   │   │   └── pdf_exporter.py      # Export PDF via COM Word
│   │   ├── monitor/            # Surveillance dossiers
│   │   │   └── folder_watcher.py
│   │   └── utils/              # Utilitaires
│   │       ├── logger.py
│   │       ├── config.py
│   │       └── notifications.py
│   │
│   ├── Lancer_EchoThyr.bat     # Lanceur avec fenêtre
│   ├── Lancer_EchoThyr_Silencieux.vbs  # Lanceur arrière-plan
│   ├── Arreter_EchoThyr.bat    # Stopper le script
│   ├── CHANGELOG.md            # Historique versions
│   └── README.md               # Documentation détaillée
│
├── legacy/                     # Versions archivées
│   └── EchoThyr-PowerShell/    # Version 1.0 PowerShell (archivée)
│       ├── EchoThyr.ps1        # Script PowerShell (ex-tess3.ps1)
│       ├── CHANGELOG.md        # Historique
│       └── README.md           # Documentation
│
├── README.md                   # Ce fichier (documentation globale)
└── .gitignore                  # Fichiers exclus de Git
```

---

## 🔧 Configuration détaillée

### DICOMWorklist - Configuration

Éditez `DICOMWorklist/config.yaml` :

```yaml
server:
  ae_title: "WORKLIST"        # AE Title du serveur
  port: 4242                  # Port d'écoute DICOM

csv:
  path: ""                    # Chemin CSV (auto-détection si vide)
  filter_echo_only: true      # Filtrer uniquement RDV écho

logging:
  level: "INFO"               # DEBUG, INFO, WARNING, ERROR
  file: "worklist_server.log"
```

### DICOMStore - Configuration

Éditez `DICOMStore/config.yaml` :

```yaml
server:
  ae_title: "PACS_LOCAL"      # AE Title du serveur
  port: 4243                  # Port d'écoute DICOM

storage:
  root_path: "C:/Users/Emeric/Desktop/Claude/DICOMStore/DICOM_Archive"
  folder_structure: "{patient_name}_{patient_id}/{study_date}/{modality}_{series_number}"
  keep_dicom: true            # Conserver fichiers DICOM
  export_images: true         # Exporter en PNG/JPEG
  image_format: "png"         # png ou jpeg

logging:
  level: "INFO"
  file: "dicom_store.log"
```

### EchoThyr-Python - Configuration

Éditez `EchoThyr-Python/config.yaml` :

```yaml
paths:
  source_folder: "C:/EchoThyr/export"
  template_word: "C:/EchoThyr/Modele_Echo.docx"
  tesseract_exe: "C:/Program Files/Tesseract-OCR/tesseract.exe"

processing:
  target_width: 1200          # Largeur images redimensionnées (px)
  check_interval: 10          # Intervalle surveillance (secondes)

logging:
  level: "INFO"               # DEBUG pour plus de détails
  log_folder: "C:/EchoThyr/logs"
```

---

## 🔗 Intégration DICOM → EchoThyr

### Workflow automatique (v3.0 - en production)

1. DICOMStore archive les images DICOM dans `DICOM_Archive/`
2. EchoThyr surveille `DICOM_Archive/` et détecte les nouvelles études
3. Lecture native DICOM : métadonnées patient + pixels bruts + Structured Reports
4. Matching hybride SR+OCR pour classification automatique (lobes, nodules, isthme)
5. Génération automatique du compte rendu Word + PDF

**Aucune intervention manuelle nécessaire** entre l'envoi des images depuis l'échographe et la génération du CR.

### Architecture de détection

```
Échographe GE Logiq P9
    │
    ├── Images DICOM (US) ──► DICOMStore (C-STORE, port 4243)
    │                              │
    └── Structured Report ─────► DICOM_Archive/Patient/Date/SR_1/
                                   │
                            EchoThyr détecte ──► SR Parser (mesures précises)
                                   │                    +
                                   │              OCR Engine (contexte: côté, nodule)
                                   │                    │
                                   │              Hybrid Matcher (4 passes)
                                   │                    │
                                   └──────────────► Word + PDF
```

---

## 🎯 Roadmap / Évolutions futures

### Réalisé (v3.0 - en production)

- [x] **Lecture DICOM native** - Direct depuis `DICOM_Archive/`
- [x] **SR Parser** - Extraction mesures depuis Structured Reports GE
- [x] **Matching hybride SR+OCR** - 4 passes (volume, dimensions, partiel, isthme)
- [x] **OCR sur pixels DICOM bruts** - Pleine résolution, sans compression
- [x] **Détection nodules avancée** - N1D/N1G, gestion misreads OCR
- [x] **Calcul volume ellipsoïde** - Quand absent du SR
- [x] **Génération python-docx** - Remplace COM Word (plus fiable)
- [x] **Anti-doublon worklist** - Tue l'ancienne instance au démarrage

### Court terme (v3.1)

- [ ] **Interface graphique** - Révision manuelle mesures avant validation CR
- [ ] **Statistiques mensuelles** - Nombre CR, taux succès, temps moyen
- [ ] **Support multi-modalités** - Echo thyroïde, sein, foie, etc.
- [ ] **Templates multiples** - CR personnalisés par type examen

### Moyen terme (v4.0)

- [ ] **API REST** - Communication inter-services
- [ ] **Notification email** - Envoi automatique CR
- [ ] **DICOMStore Viewer Pro** - Annotations, mesures interactives

### Long terme (v5.0 - Intelligence Artificielle)

- [ ] **Détection anomalies IA/ML** (TensorFlow, PyTorch)
  - Classification nodules (bénin/malin)
  - Score Ti-RADS automatique
  - Segmentation automatique thyroïde
- [ ] **Prédiction diagnostics** - Aide à la décision médicale

---

## 📊 Performances

### Benchmarks typiques

| Opération | Temps moyen | Notes |
|-----------|-------------|-------|
| Worklist Query (C-FIND) | < 100 ms | Réponse quasi-instantanée |
| Réception image DICOM (C-STORE) | 200-500 ms/image | Dépend taille image |
| SR Parsing (Structured Report) | < 50 ms | Extraction XML GE tag 0x6005,0x1010 |
| OCR sur DICOM brut (PIL Image) | 1-2 s/image | Tesseract PSM 6, pleine résolution |
| Matching hybride (4 passes) | < 10 ms | Volume + dimensions + partiel + isthme |
| Génération CR Word + PDF | 3-5 s | python-docx + export PDF COM Word |

### Optimisations appliquées

- **DICOMStore** : Threading pour C-STORE simultanés
- **EchoThyr** : OCR sur pixels DICOM bruts (pas de compression JPEG intermédiaire)
- **EchoThyr** : Attente 20s pour SR (race condition échographe GE)
- **Worklist** : Anti-doublon automatique au démarrage (kill ancien processus)
- **Worklist** : Parsing CSV une seule fois au démarrage
- **Logging** : Rotation quotidienne, pas de surcharge I/O

---

## 🛡️ Sécurité & Conformité

### Données médicales

- **RGPD** : Les données patients restent en local, pas de cloud
- **HDS** : Compatible hébergement données de santé (sur infra certifiée)
- **DICOM Security** : Serveurs en écoute locale uniquement (pas exposés Internet)
- **Logs** : Horodatage de toutes opérations pour traçabilité

### Recommandations déploiement

- Serveurs DICOM sur réseau local isolé uniquement
- Pare-feu activé (ports 4242, 4243 autorisés en local seulement)
- Sauvegardes régulières de `DICOM_Archive/`
- Pas d'exposition Internet directe (utiliser VPN si accès distant nécessaire)

---

## 🔧 Dépannage

### Port déjà utilisé

**Symptôme** : `OSError: [Errno 10048] Address already in use`

**Solution** :
```cmd
# Trouver le processus utilisant le port 4242 ou 4243
netstat -ano | findstr :4242
# Tuer le processus (remplacer PID)
taskkill /PID [PID] /F
```

### Échographe ne trouve pas le serveur

**Solutions** :
1. Vérifier IP PC : `ipconfig`
2. Ping échographe : `ping [IP échographe]`
3. Désactiver temporairement pare-feu pour tester
4. Vérifier AE Title (sensible à la casse)

### OCR n'extrait aucune mesure

**Solutions** :
1. Vérifier les logs DEBUG : `C:\EchoThyr\logs\`
2. Vérifier que Tesseract est installé : `tesseract --version`
3. L'OCR fonctionne sur les pixels DICOM bruts (pleine résolution) - pas besoin de PNG/JPEG
4. Nodules non détectés ? Vérifier le format de légende (N1, N1D, N1G supportés)

### Nodules/mesures classés comme lobe au lieu de nodule

**Cause** : Le format de légende GE n'est pas reconnu par le regex OCR
**Solutions** : Vérifier dans les logs la ligne `OCR context:` - le champ `nodule=` doit contenir un chiffre

### Pour plus d'aide

Consultez les README spécifiques de chaque projet :
- [DICOMWorklist/README.md](DICOMWorklist/README.md)
- [DICOMStore/README.md](DICOMStore/README.md)
- [EchoThyr-Python/README.md](EchoThyr-Python/README.md)

---

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. **Fork** le projet
2. Créez une branche feature : `git checkout -b feature/AmazingFeature`
3. Commitez vos changements : `git commit -m 'Add AmazingFeature'`
4. Push vers la branche : `git push origin feature/AmazingFeature`
5. Ouvrez une **Pull Request**

### Conventions de code

- **Python** : PEP 8, type hints encouragés
- **Docstrings** : Google style
- **Commits** : Messages explicites en français
- **Tests** : Pytest pour nouveaux modules critiques

---

## 📄 Licence

Ce projet est sous licence **MIT** - voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 📞 Support

Pour toute question ou problème :

1. 📖 Consultez les README spécifiques de chaque projet
2. 🔍 Vérifiez les [Issues](https://github.com/ES-Vibe/Medical-DICOM-Suite/issues) existantes
3. 🆕 Ouvrez une nouvelle issue si besoin

---

## 🙏 Remerciements

### Technologies utilisées

- **[pydicom](https://github.com/pydicom/pydicom)** - Manipulation fichiers DICOM
- **[pynetdicom](https://github.com/pydicom/pynetdicom)** - Protocole réseau DICOM
- **[Tesseract OCR](https://github.com/tesseract-ocr/tesseract)** - Moteur OCR open-source
- **[python-docx](https://github.com/python-openxml/python-docx)** - Génération documents Word
- **[Flask](https://flask.palletsprojects.com/)** - Framework web viewer
- **[Pillow](https://pillow.readthedocs.io/)** - Traitement images Python

### Crédits

- [DICOM Standard](https://www.dicomstandard.org/) - Norme médicale internationale
- [GE Healthcare](https://www.gehealthcare.com/) - Documentation échographes Logiq
- [Doctolib](https://www.doctolib.fr/) - Plateforme de gestion RDV médicaux
- [Claude Code](https://claude.com/claude-code) - Assistance développement IA

---

<div align="center">

**Fait avec ❤️ pour améliorer l'efficacité médicale**

![Medical DICOM Suite](https://img.shields.io/badge/Medical-DICOM%20Suite-blue?style=for-the-badge)

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*

</div>
