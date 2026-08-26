# 🐍 EchoThyr Automation - Version Python 2.3.0

Version Python moderne du système d'automatisation de comptes rendus d'échographie thyroïdienne.

## 🎯 Fonctionnalités

- ✅ **3 modes de détection** : SR pur, hybride SR+OCR, OCR seul
- ✅ **Structured Reports GE** : Parsing du XML propriétaire GE (tag 6005,1010)
- ✅ **Schéma thyroïdien automatique** : Vue frontale + coupe transversale avec nodules positionnés
- ✅ **Architecture modulaire** : Code organisé en modules (OCR, DICOM, document, schéma)
- ✅ **Configuration YAML** : Paramétrage facile
- ✅ **Prêt pour IA/ML** : Compatible TensorFlow, scikit-learn, OpenCV

## 📁 Structure du projet

```
EchoThyr-Python/
├── main.py                    # Point d'entrée principal + pipeline 3 voies
├── config.yaml                # Configuration
├── requirements.txt           # Dépendances Python
│
├── src/                       # Code source modulaire
│   ├── dicom/                 # Lecture DICOM + Structured Reports
│   │   ├── dicom_reader.py   # Lecture fichiers DICOM, conversion JPEG
│   │   └── sr_parser.py      # Parser SR GE (ThyroidReport, NoduleMeasurement)
│   ├── ocr/                   # Extraction OCR
│   │   ├── tesseract_engine.py  # OCRContext + extract_context()
│   │   └── image_processor.py
│   ├── hybrid/                # Matching hybride SR + OCR
│   │   └── matcher.py        # HybridMatcher
│   ├── schema/                # Génération schéma thyroïdien
│   │   ├── models.py         # NodulePosition, ThyroidGeometry, enums
│   │   ├── position_parser.py # Extraction position depuis légendes OCR
│   │   └── thyroid_renderer.py # Rendu Pillow (vue frontale + transversale)
│   ├── document/              # Génération documents
│   │   ├── word_generator.py # Génération Word avec schéma intégré
│   │   └── pdf_exporter.py
│   ├── monitor/               # Surveillance dossiers
│   │   └── folder_watcher.py
│   ├── utils/                 # Utilitaires
│   │   ├── logger.py         # Logging avec couleurs
│   │   ├── config.py         # Gestion configuration
│   │   └── notifications.py  # Notifications audio/visuelles
│   └── ml/                    # Future IA/ML (préparé)
│       └── anomaly_detector.py
│
├── legacy/                    # Version PowerShell (v1.x)
│   └── tess3.ps1
│
└── tests/                     # Tests unitaires (à venir)
```

## 🚀 Installation

### 1. Prérequis

- **Python 3.8+** : [Télécharger](https://www.python.org/downloads/)
- **Tesseract OCR** : Pour extraction OCR des légendes échographiques
- **Microsoft Word** : Pour génération documents (optionnel si python-docx suffit)

### 2. Installation dépendances

```bash
# Installation complète
pip install -r requirements.txt

# Installation minimale (production)
pip install pytesseract Pillow python-docx pydicom watchdog PyYAML colorlog plyer
```

### 3. Configuration

Éditez `config.yaml` si nécessaire (chemins par défaut identiques à version PowerShell).

## 🎮 Utilisation

### Lancement rapide

**Méthode 1 : Batch file (recommandé)**
```
Double-cliquez sur : Lancer_EchoThyr_Python.bat
```

**Méthode 2 : Ligne de commande**
```bash
python main.py
```

**Méthode 3 : Arrière-plan silencieux**
```
Double-cliquez sur : Lancer_EchoThyr_Python_Silencieux.vbs
```

### Arrêt

- **Console visible** : `Ctrl+C`
- **Arrière-plan** : Utilisez `Arreter_EchoThyr.bat` (fonctionne aussi pour Python)

## ⚙️ Configuration

Le fichier `config.yaml` permet de personnaliser :

```yaml
# Chemins
source_dir: "C:\\EchoThyr\\export"
template_path: "C:\\EchoThyr\\Modele_Echo.docx"

# Images
target_width: 1200

# Monitoring
check_interval: 10

# OCR
ocr_language: "eng"
ocr_psm: 6

# Notifications
enable_beep: true
enable_banner: true
```

## 🔬 Pipeline de traitement (3 voies)

Le pipeline détecte automatiquement le mode optimal selon les données disponibles :

| Mode | Condition | Mesures | Position nodules |
|------|-----------|---------|------------------|
| **SR pur** | SR + outil thyroïde GE | Depuis le SR | OCR légendes pour position |
| **Hybride** | SR + outil Volume générique | SR (valeurs) + OCR (contexte) | OCR légendes |
| **OCR seul** | Pas de SR | OCR complet | OCR légendes |

### Étapes du pipeline DICOM

1. **Analyse SR** : Détection et parsing du Structured Report GE
2. **Info patient** : Extraction depuis SR ou DICOM header
3. **Conversion JPEG** : DICOM → JPEG pour le document Word
4. **Mesures** : Extraction selon le mode détecté (SR/hybride/OCR)
5. **Schéma thyroïdien** : Génération automatique du schéma anatomique
6. **Document Word** : Génération du compte-rendu avec schéma intégré
7. **Export PDF** : Conversion Word → PDF (optionnel)

## 🖼️ Schéma thyroïdien automatique

Le module `src/schema/` génère un schéma anatomique montrant la position et la taille proportionnelle des nodules :

- **Vue frontale (coronale)** : Trachée, lobes proportionnels aux mesures, isthme, nodules positionnés (S/M/I, lat/méd)
- **Coupe transversale (axiale)** : Profondeur antérieur/postérieur des nodules
- **Légende** : Couleurs distinctes par nodule avec dimensions

### Positionnement des nodules

La position est extraite des légendes de l'échographe GE (format : `RT THYROID LOBE N1 SUP EXT POST A0%`) :

| Axe | Tokens reconnus |
|-----|----------------|
| Vertical | SUP, MOY/MID, INF |
| Profondeur | ANT, POST |
| Latéral | EXT/LAT, INT/MED |
| Isthme | ISTHME, ISTHMUS |

Le parser tolère les erreurs OCR courantes (`OOST` → POST, `P0ST` → POST).

### Rendu

- Technique de supersampling 3x + LANCZOS pour un rendu anti-aliasé de qualité
- Convention anatomique : lobe droit affiché à gauche (vue de face du patient)
- Le schéma est inséré au placeholder `[SCHEMA]` dans le template Word, ou en fin de document

## 🐛 Dépannage

### Python non trouvé

```bash
python --version
# Ajouter Python au PATH si nécessaire
```

### Dépendances manquantes

```bash
pip install --upgrade -r requirements.txt
```

### Schéma non généré

Le schéma nécessite des nodules avec des données de position. Vérifier :
- Que les images DICOM contiennent des légendes avec format GE (`N1 SUP EXT POST A0%`)
- Que Tesseract OCR fonctionne correctement
- L'échec du schéma est non-fatal : le rapport est généré sans schéma

## 📝 Logs

```
C:\EchoThyr\logs\echothyr_python_YYYY-MM-DD.log
```

Format :
```
[INFO] Processing DICOM study: PATIENT_NAME (12 files)
[INFO] Mode SR: outil thyroide specifique detecte
[INFO] Thyroid schema generated: $thyroid_schema.png
[INFO] Word document generated: CR ECHO THYR NOM Prenom DD-MM-YYYY.docx
```

---

**Version** : 2.3.0
**Licence** : MIT
