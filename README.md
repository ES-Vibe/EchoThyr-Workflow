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
  4. TRAITEMENT OCR & GÉNÉRATION CR                                 │
  ┌──────────────────────────────────────────────────────────────┐ │
  │              EchoThyr-Python (Surveillance)                   │ │
  │  ┌────────────┐   OCR    ┌──────────┐   Generate  ┌────────┐ │ │
  │  │ Tesseract  │◄─────────│  Images  │◄────────────│ Watch  │◄┘ │
  │  │  Engine    │          │ Processor│             │ Folder │   │
  │  └─────┬──────┘          └──────────┘             └────────┘   │
  │        │ Mesures                                                │
  │        ▼                                                        │
  │  ┌────────────┐                                                │
  │  │   Word/PDF │                                                │
  │  │  Generator │                                                │
  │  └────────────┘                                                │
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
| **[EchoThyr-Python](EchoThyr-Python/)** | Génération automatique de CR avec OCR Tesseract | - | ✅ Production |
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

Dès que les images sont archivées :
- EchoThyr détecte les nouvelles images
- Extrait automatiquement les mesures (OCR)
- Génère le compte rendu Word + PDF
- Notification sonore de fin de traitement

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
├── EchoThyr-Python/            # Génération automatique CR (v2.0 - Python)
│   ├── main.py                 # Point d'entrée principal
│   ├── config.yaml             # Configuration externe
│   ├── requirements.txt        # Dépendances Python
│   │
│   ├── src/                    # Code source modulaire
│   │   ├── ocr/                # Extraction mesures OCR
│   │   │   ├── tesseract_engine.py
│   │   │   └── image_processor.py
│   │   ├── document/           # Génération Word/PDF
│   │   │   ├── word_generator.py
│   │   │   └── pdf_exporter.py
│   │   ├── monitor/            # Surveillance dossiers
│   │   │   └── folder_watcher.py
│   │   ├── ml/                 # Préparé pour IA/ML
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

### Workflow actuel (manuel)

1. DICOMStore archive les images DICOM
2. DICOMStore exporte en PNG dans `DICOM_Archive/`
3. **Étape manuelle** : Copier les PNG vers `C:\EchoThyr\export\`
4. EchoThyr-Python détecte et traite automatiquement

### Intégration future (planifiée)

**Version 3.0 - Intégration native DICOM** :
- EchoThyr lit directement depuis `DICOM_Archive/`
- Parsing métadonnées DICOM (nom, prénom, date)
- Pas de copie manuelle nécessaire
- Liaison automatique Worklist → Store → CR

Module `EchoThyr-Python/src/dicom/` à créer :
```python
# src/dicom/dicom_reader.py
- Lecture fichiers DICOM depuis archive
- Extraction métadonnées patient
- Conversion DICOM → images pour OCR

# src/dicom/archive_watcher.py
- Surveillance DICOM_Archive/
- Détection nouvelles études
- Déclenchement auto génération CR
```

---

## 🎯 Roadmap / Évolutions futures

### Court terme (v2.1)

- [ ] **Interface graphique WPF** - Révision manuelle mesures OCR
- [ ] **Statistiques mensuelles** - Nombre CR, taux succès, temps moyen
- [ ] **Notification email** - Envoi automatique CR au médecin/patient
- [ ] **DICOMStore Viewer Pro** - Amélioration interface web viewer
  - Annotations sur images
  - Mesures interactives
  - Export multi-format (JPEG, TIFF, PDF)

### Moyen terme (v3.0 - Intégration DICOM native)

- [ ] **EchoThyr : Lecture DICOM native** - Direct depuis `DICOM_Archive/`
- [ ] **Support multi-modalités** - Echo thyroïde, sein, foie, etc.
- [ ] **Templates multiples** - CR personnalisés par type examen
- [ ] **API REST** - Communication inter-services
  - `POST /worklist/patients` - Ajouter patient
  - `GET /store/studies/{patient_id}` - Récupérer études
  - `POST /echothyr/generate` - Générer CR à la demande

### Long terme (v4.0 - Intelligence Artificielle)

- [ ] **Détection anomalies IA/ML** (TensorFlow, PyTorch)
  - Classification nodules (bénin/malin)
  - Segmentation automatique thyroïde
  - Score Ti-RADS automatique
  - Détection calcifications, vascularisation
- [ ] **OCR avancé** - Transformers (BERT, GPT-based OCR)
- [ ] **Super-resolution images** - Amélioration qualité (ESRGAN)
- [ ] **Prédiction diagnostics** - Aide à la décision médicale

---

## 📊 Performances

### Benchmarks typiques

| Opération | Temps moyen | Notes |
|-----------|-------------|-------|
| Worklist Query | < 100 ms | Réponse quasi-instantanée |
| Réception image DICOM (C-STORE) | 200-500 ms/image | Dépend taille image |
| Export PNG depuis DICOM | 100-300 ms/image | Conversion Pillow |
| OCR extraction mesures | 1-2 s/image | Tesseract PSM 6 |
| Génération CR Word + PDF | 3-5 s | Includes Word COM + docx2pdf |

### Optimisations appliquées

- **DICOMStore** : Threading pour C-STORE simultanés
- **EchoThyr** : Cache images redimensionnées (préfixe `$`)
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
1. Vérifier qualité images (résolution > 800px)
2. Consulter logs DEBUG : `EchoThyr-Python/logs/`
3. Tester Tesseract manuellement :
   ```cmd
   tesseract image.jpg stdout --psm 6 -l eng
   ```
4. Vérifier format mesures : `XX.X cm` ou `XX x YY mm`

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
