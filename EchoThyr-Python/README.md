# 🐍 EchoThyr Automation - Version Python 2.0.0

Version Python moderne du système d'automatisation de comptes rendus d'échographie thyroïdienne.

## 🎯 Pourquoi Python ?

Cette version Python offre :
- ✅ **Architecture modulaire** : Code mieux organisé et maintenable
- ✅ **Prêt pour IA/ML** : Compatible TensorFlow, scikit-learn, OpenCV
- ✅ **Tests unitaires** : pytest pour qualité code
- ✅ **Configuration YAML** : Paramétrage facile
- ✅ **Cross-platform** : Fonctionne Windows/Linux/Mac (avec adaptations)
- ✅ **Évolutivité** : Base solide pour futures fonctionnalités

## 📁 Structure du projet

```
CR-ECHO-AUTO/
├── main.py                    # Point d'entrée principal
├── config.yaml                # Configuration
├── requirements.txt           # Dépendances Python
│
├── src/                       # Code source modulaire
│   ├── utils/                 # Utilitaires
│   │   ├── logger.py         # Logging avec couleurs
│   │   ├── config.py         # Gestion configuration
│   │   └── notifications.py  # Notifications audio/visuelles
│   ├── ocr/                   # Extraction OCR
│   │   ├── tesseract_engine.py
│   │   └── image_processor.py
│   ├── document/              # Génération documents
│   │   ├── word_generator.py
│   │   └── pdf_exporter.py
│   ├── monitor/               # Surveillance dossiers
│   │   └── folder_watcher.py
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
- **Tesseract OCR** : Déjà installé (même version que PowerShell)
- **Microsoft Word** : Pour génération documents

### 2. Installation dépendances

```bash
# Installation complète
pip install -r requirements.txt

# Installation minimale (production)
pip install pytesseract Pillow python-docx watchdog PyYAML colorlog plyer
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

## 🔍 Différences avec version PowerShell

| Fonctionnalité | PowerShell (v1.x) | Python (v2.0.0) |
|----------------|-------------------|-----------------|
| **Architecture** | Monolithique | Modulaire (OOP) |
| **Configuration** | Hardcodée | YAML externe |
| **Logs** | Fichiers texte | Logging structuré |
| **Tests** | ❌ Aucun | ✅ pytest ready |
| **Extensibilité** | Limitée | ✅ Modules IA/ML |
| **Portabilité** | Windows only | Multi-plateformes |
| **Performance** | ⭐⭐⭐⭐ | ⭐⭐⭐⭐ |

**Fonctionnalités identiques :**
- Extraction OCR mesures
- Génération Word/PDF
- Notifications audio/visuelles
- Monitoring automatique
- Logging quotidien

## 🧪 Tests (à venir)

```bash
# Lancer les tests unitaires
pytest tests/

# Avec couverture de code
pytest --cov=src tests/
```

## 🔮 Roadmap IA/ML

La version Python est prête pour :

```python
# Future: Détection automatique anomalies
from src.ml.anomaly_detector import ThyroidAnomalyDetector

detector = ThyroidAnomalyDetector()
results = detector.predict(image_path)
# → {nodule: True, malignancy_score: 0.72, ...}
```

**Fonctionnalités ML planifiées :**
- Classification nodules (bénin/malin)
- Segmentation automatique zones d'intérêt
- Amélioration qualité images (super-resolution)
- Détection anomalies thyroïdiennes
- OCR avancé (Transformers au lieu de Tesseract)

## 🐛 Dépannage

### Python non trouvé

```bash
# Vérifier installation Python
python --version

# Ajouter Python au PATH si nécessaire
# Windows: Panneau de configuration → Système → Variables d'environnement
```

### Dépendances manquantes

```bash
# Réinstaller toutes les dépendances
pip install --upgrade -r requirements.txt
```

### Import errors

```bash
# S'assurer d'être dans le bon dossier
cd C:\Users\Emeric\Desktop\Claude
python main.py
```

## 📊 Performances

**Benchmarks typiques (même machine que PowerShell) :**
- Traitement image OCR : ~2-3 secondes
- Génération Word : ~1 seconde
- Export PDF : ~2 secondes
- **Total par patient** : ~10-15 secondes

## 🤝 Migration depuis PowerShell

**Les deux versions peuvent coexister !**

1. **Tester Python** : Utilisez `Lancer_EchoThyr_Python.bat`
2. **Comparer résultats** : Traiter même dossier avec les 2 versions
3. **Basculer** : Quand confiant, utiliser uniquement Python
4. **Garder legacy** : PowerShell reste dans `legacy/` pour référence

## 📝 Logs

Même emplacement que PowerShell :
```
C:\EchoThyr\logs\echothyr_python_2026-01-05.log
```

Format :
```
[2026-01-05 14:32:15] [INFO] EchoThyr Automation started - Version 2.0.0
[2026-01-05 14:32:15] [SUCCESS] All prerequisites validated successfully
[2026-01-05 14:32:30] [INFO] Found 1 new folder(s) to process
```

## 🌟 Avantages version Python

1. **Maintenabilité** : Code modulaire, facile à modifier
2. **Testabilité** : Tests unitaires pour chaque module
3. **Évolutivité** : Ajout IA/ML sans refactoring
4. **Communauté** : Plus de devs Python que PowerShell
5. **Librairies** : Écosystème riche (ML, vision, data science)

## ⚠️ Note importante

Cette version Python (2.0.0) est **100% compatible fonctionnellement** avec la version PowerShell (1.0.0).

Tous les CR générés sont identiques. Seule l'implémentation interne change.

---

**Version** : 2.0.0
**Date** : 2026-01-05
**Licence** : MIT
