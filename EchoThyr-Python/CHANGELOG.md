# Changelog - EchoThyr Python

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

---

## [2.0.0] - 2026-01-05

### 🎉 Version Python - Refonte complète

Réécriture complète en Python avec architecture modulaire professionnelle.

Cette version représente une refonte totale du projet initialement écrit en PowerShell, avec une architecture moderne et extensible.

### ✨ Ajouté
- **Architecture modulaire** : Code organisé en modules (utils, ocr, document, monitor, ml)
- **Configuration YAML** : `config.yaml` pour paramétrage externe
- **Modules Python** :
  - `src/utils/logger.py` : Logging avec colorlog
  - `src/utils/config.py` : Gestion configuration YAML
  - `src/utils/notifications.py` : Notifications audio/visuelles
  - `src/ocr/tesseract_engine.py` : Extraction mesures OCR
  - `src/ocr/image_processor.py` : Traitement images (resize)
  - `src/document/word_generator.py` : Génération Word avec python-docx
  - `src/document/pdf_exporter.py` : Export PDF (docx2pdf/COM)
  - `src/monitor/folder_watcher.py` : Surveillance dossiers
  - `src/ml/` : Préparé pour IA/ML future
- **Point d'entrée** : `main.py` avec classe `EchoThyrApp`
- **Tests unitaires** : Structure `tests/` prête pour pytest
- **Scripts lanceurs** :
  - `Lancer_EchoThyr.bat` : Lancement avec fenêtre
  - `Lancer_EchoThyr_Silencieux.vbs` : Arrière-plan
  - `Arreter_EchoThyr.bat` : Arrêt processus Python
- **Documentation** :
  - `README.md` : Documentation complète Python
  - `INSTALL_PYTHON.txt` : Guide installation Python/dépendances
  - `CHANGELOG.md` : Historique versions (ce fichier)
- **Outils de test** :
  - `test_installation.bat` : Vérification installation Python
  - `verif_rapide.bat` : Test rapide fonctionnalités
- **Requirements** : `requirements.txt` avec dépendances commentées :
  - `pytesseract` : Interface Python pour Tesseract OCR
  - `Pillow` : Traitement d'images
  - `python-docx` : Génération documents Word
  - `docx2pdf` : Export PDF (Windows)
  - `PyYAML` : Parsing configuration YAML
  - `colorlog` : Logging coloré
  - `pywin32` : API Windows (notifications audio)

### 🔄 Modifié par rapport à la version PowerShell
- **Langage** : Python 3.8+ au lieu de PowerShell
- **Dépendances** : Packages Python au lieu de modules PowerShell natifs
- **Génération Word** : `python-docx` au lieu de COM Word (plus portable)
- **Configuration** : YAML externe au lieu de variables hardcodées dans script
- **Logging** : Module `colorlog` avec formatage structuré et couleurs
- **Architecture** : Programmation orientée objet (classes) au lieu de fonctions scriptées
- **Organisation** : Structure modulaire avec séparation des responsabilités

### 🎯 Avantages version Python
- **Maintenabilité** : Code modulaire, séparation des préoccupations, tests unitaires
- **Évolutivité** : Prêt pour intégration ML/IA (TensorFlow, scikit-learn, OpenCV)
- **Portabilité** : Multi-plateformes (Windows/Linux/Mac avec adaptations mineures)
- **Communauté** : Écosystème Python riche (ML, vision par ordinateur, data science)
- **Tests** : Infrastructure pytest, coverage, type checking (mypy)
- **Débogage** : Meilleur outillage IDE (VSCode, PyCharm)

### 📊 Compatibilité avec version PowerShell
- **Fonctionnalités identiques** : Même workflow que version PowerShell v1.0.0
- **Format sortie** : Documents Word/PDF identiques
- **Configuration** : Même structure dossiers `C:\EchoThyr\`
- **Coexistence** : Les 2 versions peuvent tourner en parallèle
- **Migration** : Aucune perte de fonctionnalité

### 🔮 Préparé pour futur
Module ML (`src/ml/`) prêt pour :
- Classification nodules thyroïdiens (bénin/malin)
- Détection automatique anomalies
- Segmentation zones d'intérêt dans images
- OCR avancé avec Transformers (BERT, LayoutLM)
- Super-resolution images médicales
- Prédiction risque selon classification TI-RADS

### 🔧 Fonctionnalités héritées de PowerShell v1.0.0
Toutes les fonctionnalités de la version PowerShell stable sont présentes :
- Extraction OCR intelligente (mesures, latéralité, nodules, isthme, volumes)
- Génération documents Word/PDF avec templates
- Bookmarks dynamiques (NOM, PRENOM, DATE, RESULTAT)
- Notifications audio/visuelles (succès/erreur)
- Logging complet (INFO, SUCCESS, WARNING, ERROR, DEBUG)
- Validation prérequis au démarrage
- Gestion erreurs robuste
- Support UTF-8 caractères français
- Surveillance continue dossiers

---

## [Unreleased] - Roadmap future

### 🔮 Planifié pour v2.1.0
- [ ] Tests unitaires complets (pytest, coverage >80%)
- [ ] Support Docker pour déploiement conteneurisé
- [ ] API REST pour intégration externe (FastAPI)
- [ ] Interface web de monitoring (Flask/React)

### 🔮 Planifié pour v2.2.0
- [ ] Module ML : Classification nodules avec CNN
- [ ] OCR avancé avec deep learning (Transformer models)
- [ ] Détection automatique anomalies thyroïdiennes
- [ ] Dashboard statistiques (nombre CR, taux succès, temps traitement)

### 🔮 Planifié pour v3.0.0
- [ ] Support multi-templates (différents types examens médicaux)
- [ ] Intégration PACS (DICOM)
- [ ] Support cloud (AWS S3, Azure Blob)
- [ ] Notification email/Slack automatique
- [ ] Mode batch traitement historique
- [ ] Super-resolution images avec GAN

---

## Notes de version

### Versioning sémantique

Ce projet utilise [Semantic Versioning](https://semver.org/lang/fr/) :

- **MAJOR** (X.0.0) : Changements incompatibles API ou refonte majeure
- **MINOR** (x.X.0) : Ajout fonctionnalités rétro-compatibles
- **PATCH** (x.x.X) : Corrections bugs rétro-compatibles

**Note :** Le passage de PowerShell à Python est considéré comme un changement MAJOR (v1.0.0 → v2.0.0) en raison du changement de langage, même si les fonctionnalités restent identiques.

### Types de changements

- **Ajouté** : Nouvelles fonctionnalités
- **Modifié** : Changements fonctionnalités existantes
- **Déprécié** : Fonctionnalités bientôt supprimées
- **Supprimé** : Fonctionnalités retirées
- **Corrigé** : Corrections de bugs
- **Sécurité** : Corrections vulnérabilités

---

**Légende émojis :**
- 🎉 Version majeure
- ✨ Nouvelle fonctionnalité
- 🔧 Correction bug
- 🔄 Modification
- ⚠️ Avertissement/Dépréciation
- 🔮 Futur/Roadmap
- 📊 Performance
- 🔒 Sécurité
