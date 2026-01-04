# 🏥 CR-ECHO-AUTO - Automatisation de Comptes Rendus d'Échographie Thyroïdienne

[![PowerShell](https://img.shields.io/badge/PowerShell-5.1+-blue.svg)](https://github.com/PowerShell/PowerShell)
[![Tesseract](https://img.shields.io/badge/Tesseract-5.x-green.svg)](https://github.com/tesseract-ocr/tesseract)
[![License](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> Script PowerShell intelligent pour la génération automatique de comptes rendus d'échographie thyroïdienne avec OCR Tesseract et notifications en temps réel.

## 📋 Table des matières

- [Vue d'ensemble](#-vue-densemble)
- [Fonctionnalités](#-fonctionnalités)
- [Prérequis](#-prérequis)
- [Installation](#-installation)
- [Utilisation](#-utilisation)
- [Structure des fichiers](#-structure-des-fichiers)
- [Configuration](#-configuration)
- [Logs et débogage](#-logs-et-débogage)
- [Dépannage](#-dépannage)
- [Contribution](#-contribution)
- [Licence](#-licence)

## 🎯 Vue d'ensemble

**CR-ECHO-AUTO** est un système d'automatisation médicale qui :
1. Surveille un dossier d'export d'images échographiques
2. Extrait automatiquement les mesures via OCR (Tesseract)
3. Génère des comptes rendus Word/PDF standardisés
4. Notifie l'utilisateur avec signaux audio/visuels
5. Journalise toutes les opérations pour traçabilité

### Workflow typique

```
Images échographie (JPG)
    ↓
Monitoring automatique (toutes les 10s)
    ↓
Extraction OCR des mesures (Tesseract)
    ↓
Redimensionnement images (1200px)
    ↓
Génération CR Word + PDF
    ↓
Notification sonore + visuelle 🔔
```

## ✨ Fonctionnalités

### 🔍 Extraction intelligente OCR
- Reconnaissance automatique des mesures (cm → mm)
- Détection latéralité (RT/LT - Droit/Gauche)
- Identification nodules (N1, N2, etc.)
- Détection isthme thyroïdien
- Extraction volumes (ml)

### 📄 Génération documents
- Templates Word personnalisables
- Export PDF automatique
- Bookmarks dynamiques (NOM, PRENOM, DATE, RESULTAT)
- Intégration images redimensionnées
- Encodage UTF-8 (support caractères français)

### 🔔 Notifications temps réel
- **Succès** : Double BEEP ascendant (800Hz → 1200Hz) + Bannière verte
- **Erreur** : Double BEEP descendant (400Hz ×2) + Bannière rouge
- Affichage console avec code couleur

### 📊 Logging & Traçabilité
- Logs quotidiens rotatifs (`C:\EchoThyr\logs\tess3_YYYY-MM-DD.log`)
- 5 niveaux : INFO, SUCCESS, WARNING, ERROR, DEBUG
- Horodatage précis de toutes opérations
- Stack traces pour débogage

### 🛡️ Robustesse
- Validation prérequis au démarrage
- Gestion erreurs avec `finally` blocks
- Cleanup garanti objets COM (Word)
- Vérification exit codes Tesseract
- Traitement continu malgré erreurs ponctuelles

## 🔧 Prérequis

### Logiciels requis

| Logiciel | Version minimale | Usage |
|----------|-----------------|-------|
| **Windows** | 10 / Server 2016+ | Système d'exploitation |
| **PowerShell** | 5.1+ | Exécution script |
| **Tesseract OCR** | 5.0+ | Extraction texte images |
| **Microsoft Word** | 2016+ | Génération documents |

### Installation Tesseract

1. Télécharger depuis [UB-Mannheim/tesseract](https://github.com/UB-Mannheim/tesseract/wiki)
2. Installer dans `C:\Program Files\Tesseract-OCR\`
3. Vérifier avec : `tesseract --version`

### Structure dossiers requise

```
C:\EchoThyr\
├── export\              # Dossier surveillé (dépôt images)
├── logs\                # Logs (créé automatiquement)
└── Modele_Echo.docx     # Template Word
```

## 📥 Installation

### 1️⃣ Cloner le dépôt

```powershell
cd C:\Users\VotreNom\Desktop
git clone https://github.com/ES-Vibe/CR-ECHO-AUTO.git
cd CR-ECHO-AUTO
```

### 2️⃣ Créer la structure de dossiers

```powershell
New-Item -ItemType Directory -Path "C:\EchoThyr\export" -Force
New-Item -ItemType Directory -Path "C:\EchoThyr\logs" -Force
```

### 3️⃣ Configurer le template Word

Placez votre fichier `Modele_Echo.docx` dans `C:\EchoThyr\`

**Bookmarks requis dans le template :**
- `NOM` : Nom du patient
- `PRENOM` : Prénom du patient
- `DATE` : Date examen
- `RESULTAT` : Résultats échographie

### 4️⃣ Vérifier la configuration

```powershell
# Vérifier Tesseract
& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version

# Tester les chemins
Test-Path "C:\EchoThyr\export"
Test-Path "C:\EchoThyr\Modele_Echo.docx"
```

## 🚀 Utilisation

### Lancement rapide

**Option 1 : Avec fenêtre visible (recommandé pour tests)**
```
Double-cliquez sur : Lancer_EchoThyr.bat
```

**Option 2 : En arrière-plan silencieux**
```
Double-cliquez sur : Lancer_EchoThyr_Silencieux.vbs
```

**Option 3 : Ligne de commande**
```powershell
cd C:\Users\VotreNom\Desktop\CR-ECHO-AUTO
.\tess3.ps1
```

### Arrêt du script

**Si lancé avec fenêtre visible :**
- Appuyez sur `Ctrl+C` dans la fenêtre PowerShell

**Si lancé en arrière-plan :**
```
Double-cliquez sur : Arreter_EchoThyr.bat
```

### Format dossier patient

Créer un dossier dans `C:\EchoThyr\export\` avec la structure :

```
C:\EchoThyr\export\NOM Prenom\
    ├── Image1.jpg
    ├── Image2.jpg
    ├── Image3.jpg
    └── ...
```

**Exemple :** `C:\EchoThyr\export\DUPONT Jean\`

### Sortie générée

Après traitement, le dossier contiendra :

```
C:\EchoThyr\export\DUPONT Jean\
    ├── Image1.jpg
    ├── Image2.jpg
    ├── $Image1.jpg                                    # Images redimensionnées
    ├── $Image2.jpg
    ├── CR ECHO THYR DUPONT Jean 04-01-2026.docx      # Document Word
    └── CR ECHO THYR DUPONT Jean 04-01-2026.pdf       # Document PDF
```

## 📁 Structure des fichiers

```
CR-ECHO-AUTO/
│
├── tess3.ps1                           # Script principal PowerShell
├── Lancer_EchoThyr.bat                 # Lanceur avec fenêtre visible
├── Lancer_EchoThyr_Silencieux.vbs      # Lanceur arrière-plan
├── Arreter_EchoThyr.bat                # Stopper le script
├── COMMENT_UTILISER.txt                # Guide utilisateur détaillé
├── README.md                           # Documentation (ce fichier)
├── .gitignore                          # Fichiers exclus de Git
│
└── (Non versionnés)
    ├── tess.ps1                        # Version 1 (ancien)
    ├── tess2.ps1                       # Version 2 (ancien)
    └── Modele_Echo.docx                # Template (local uniquement)
```

## ⚙️ Configuration

### Modification des chemins

Éditez `tess3.ps1` lignes 6-10 :

```powershell
$dossierSource = "C:\EchoThyr\export"                           # Dossier surveillé
$cheminModele = "C:\EchoThyr\Modele_Echo.docx"                  # Template Word
$largeurCible = 1200                                             # Largeur images (px)
$tesseractExe = "C:\Program Files\Tesseract-OCR\tesseract.exe"  # Chemin Tesseract
$env:TESSDATA_PREFIX = "C:\Program Files\Tesseract-OCR\tessdata" # Données langues
```

### Intervalle de surveillance

Par défaut : 10 secondes. Modifier ligne ~441 :

```powershell
Start-Sleep -Seconds 10  # Changer à 5, 15, 30, etc.
```

### Démarrage automatique Windows

**Méthode 1 - Dossier Démarrage :**

1. Copiez `Lancer_EchoThyr_Silencieux.vbs`
2. Collez dans : `C:\Users\VotreNom\AppData\Roaming\Microsoft\Windows\Start Menu\Programs\Startup`

**Méthode 2 - Planificateur de tâches :**

1. Ouvrez `Planificateur de tâches`
2. Créer une tâche de base
3. Déclencheur : "Au démarrage de l'ordinateur"
4. Action : Démarrer un programme
5. Programme : `C:\chemin\vers\Lancer_EchoThyr_Silencieux.vbs`

## 📊 Logs et débogage

### Emplacement logs

```
C:\EchoThyr\logs\tess3_YYYY-MM-DD.log
```

Exemple : `C:\EchoThyr\logs\tess3_2026-01-04.log`

### Niveaux de log

| Niveau | Usage | Fichier | Console |
|--------|-------|---------|---------|
| `INFO` | Informations générales | ✅ | ✅ |
| `SUCCESS` | Opérations réussies | ✅ | ✅ |
| `WARNING` | Avertissements non bloquants | ✅ | ✅ |
| `ERROR` | Erreurs bloquantes | ✅ | ✅ |
| `DEBUG` | Détails techniques | ✅ | ❌ |

### Exemple de log

```
[2026-01-04 14:32:15] [INFO] Script started
[2026-01-04 14:32:15] [SUCCESS] Tesseract version check passed: tesseract v5.5.0
[2026-01-04 14:32:30] [INFO] Found 1 new folder(s) to process
[2026-01-04 14:32:30] [INFO] Processing folder: DUPONT Jean
[2026-01-04 14:32:31] [DEBUG] Processing image: C:\EchoThyr\export\DUPONT Jean\Image1.jpg
[2026-01-04 14:32:32] [DEBUG] Extracted measurement: Cote=RT, Nodule=, Isthme=False, Mesure=45.2 x 23.1 x 18.5 mm
[2026-01-04 14:32:45] [SUCCESS] Report generated successfully: CR ECHO THYR DUPONT Jean 04-01-2026 for DUPONT Jean
```

### Consulter les logs

**PowerShell :**
```powershell
Get-Content "C:\EchoThyr\logs\tess3_2026-01-04.log" -Tail 50
```

**Notepad :**
```powershell
notepad "C:\EchoThyr\logs\tess3_2026-01-04.log"
```

**Filtrer erreurs uniquement :**
```powershell
Get-Content "C:\EchoThyr\logs\tess3_2026-01-04.log" | Select-String "ERROR"
```

## 🔧 Dépannage

### Problème : "Execution Policy" erreur

**Symptôme :** Script refuse de s'exécuter

**Solution :**
```powershell
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

### Problème : Tesseract non trouvé

**Symptôme :** `[ERROR] Tesseract executable not found`

**Solutions :**
1. Vérifier installation : `& "C:\Program Files\Tesseract-OCR\tesseract.exe" --version`
2. Réinstaller Tesseract depuis [GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
3. Vérifier chemin dans `tess3.ps1` ligne 9

### Problème : Aucune mesure extraite

**Symptôme :** `[WARNING] No measurements extracted from images`

**Causes possibles :**
- Images de mauvaise qualité
- Texte illisible par OCR
- Format non supporté (utiliser JPG)

**Solution :**
1. Consulter logs DEBUG pour voir texte extrait
2. Vérifier que les mesures sont en format "XX.X cm"
3. Tester manuellement Tesseract sur une image :
```powershell
& "C:\Program Files\Tesseract-OCR\tesseract.exe" "C:\chemin\image.jpg" stdout --psm 6 -l eng
```

### Problème : Caractères mal encodés (é → Ã©)

**Symptôme :** Caractères français corrompus dans Word

**Solution :** Le script utilise maintenant UTF-8 avec BOM. Si problème persiste :
```powershell
$content = Get-Content .\tess3.ps1 -Raw
$utf8 = New-Object System.Text.UTF8Encoding $true
[System.IO.File]::WriteAllText(".\tess3.ps1", $content, $utf8)
```

### Problème : Word ne se ferme pas

**Symptôme :** Processus `WINWORD.EXE` reste actif

**Solution :** Le script utilise `finally` blocks pour cleanup. Si processus bloqué :
```powershell
Stop-Process -Name WINWORD -Force
```

### Problème : Script s'arrête sans message

**Symptôme :** Fenêtre se ferme immédiatement

**Solution :**
1. Lancer depuis PowerShell au lieu du .bat
2. Consulter logs dans `C:\EchoThyr\logs\`
3. Vérifier validation prérequis au démarrage

## 🤝 Contribution

Les contributions sont les bienvenues ! Pour contribuer :

1. **Fork** le projet
2. Créez une branche feature (`git checkout -b feature/AmazingFeature`)
3. Commitez vos changements (`git commit -m 'Add AmazingFeature'`)
4. Pushez vers la branche (`git push origin feature/AmazingFeature`)
5. Ouvrez une **Pull Request**

### Roadmap / Idées d'amélioration

- [ ] Interface graphique WPF pour révision manuelle mesures
- [ ] Export statistiques mensuelles (nombre CR, taux succès)
- [ ] Support multi-templates (différents types d'examens)
- [ ] Notification email automatique
- [ ] API REST pour intégration PACS
- [ ] Support autres formats d'images (DICOM, PNG)
- [ ] Mode batch pour traitement historique
- [ ] Détection automatique anomalies (IA/ML)

## 📄 Licence

Ce projet est sous licence **MIT** - voir le fichier [LICENSE](LICENSE) pour plus de détails.

---

## 📞 Support

Pour toute question ou problème :

1. 📖 Consultez d'abord `COMMENT_UTILISER.txt`
2. 🔍 Vérifiez les [Issues](https://github.com/ES-Vibe/CR-ECHO-AUTO/issues) existantes
3. 🆕 Ouvrez une nouvelle issue si besoin

---

## 🙏 Remerciements

- [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) - Moteur OCR open-source
- [PowerShell Gallery](https://www.powershellgallery.com/) - Ressources PowerShell
- [Claude Code](https://claude.com/claude-code) - Assistance développement

---

<div align="center">

**Fait avec ❤️ pour améliorer l'efficacité médicale**

🤖 *Generated with [Claude Code](https://claude.com/claude-code)*

</div>
