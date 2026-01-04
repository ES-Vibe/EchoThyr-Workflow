# Changelog

Tous les changements notables de ce projet seront documentés dans ce fichier.

Le format est basé sur [Keep a Changelog](https://keepachangelog.com/fr/1.0.0/),
et ce projet adhère au [Semantic Versioning](https://semver.org/lang/fr/).

## [1.0.0] - 2026-01-04

### 🎉 Version initiale stable

Première version complète avec toutes les fonctionnalités de production.

### ✨ Ajouté
- **Système de logging complet** : Logs quotidiens rotatifs dans `C:\EchoThyr\logs\`
  - 5 niveaux : INFO, SUCCESS, WARNING, ERROR, DEBUG
  - Horodatage de toutes opérations
  - Stack traces pour débogage
- **Validation prérequis au démarrage** : Vérification chemins, Tesseract, template Word
  - Fail-fast avant boucle infinie
  - Test fonctionnel Tesseract (`--version`)
- **Notifications audio/visuelles** :
  - Succès : Double BEEP ascendant (800Hz → 1200Hz) + bannière verte
  - Erreur : Double BEEP descendant (400Hz ×2) + bannière rouge
  - Informations contextuelles (patient, CR, heure)
- **Fonctions de notification** : `Invoke-SuccessNotification`, `Invoke-ErrorNotification`
- **Fonctions de logging** : `Initialize-Logging`, `Write-Log`, `Write-LogDebug`
- **Fonction de validation** : `Test-Prerequisites`
- **Encodage UTF-8** : Support complet caractères français (é, è, ï, à, ô)
- **Fichiers lanceurs** :
  - `Lancer_EchoThyr.bat` : Lancement avec fenêtre visible
  - `Lancer_EchoThyr_Silencieux.vbs` : Lancement arrière-plan
  - `Arreter_EchoThyr.bat` : Arrêt processus
- **Documentation** :
  - `README.md` : Documentation GitHub complète
  - `COMMENT_UTILISER.txt` : Guide utilisateur détaillé
  - `CHANGELOG.md` : Historique versions (ce fichier)

### 🔧 Corrigé
- **Bug critique ligne 183** : Paramètre Tesseract `quiet` → supprimé et redirigé `2>$null`
  - Le paramètre `--quiet` n'est pas supporté par toutes les versions de Tesseract
  - Utilisation de redirection stderr à la place
- **Catch vides éliminés** : Toutes erreurs maintenant loggées avec contexte
  - Ligne 236 : Get-Measurements avec vraie gestion erreur
  - Ligne 329-337 : Image processing avec logging WARNING
- **Cleanup COM robuste** : Finally blocks garantissant fermeture Word
  - Évite processus WINWORD.EXE bloqués
  - Cleanup même en cas d'exception
- **Encodage caractères** : Fichier PowerShell converti en UTF-8 avec BOM
  - Résout problème "thyroÃ¯dien" → "thyroïdien"

### 🔄 Modifié
- **Fonction `Get-Measurements` réécrite** :
  - Validation chemin image en entrée
  - Vérification `$LASTEXITCODE` après Tesseract
  - Logging debug texte extrait et mesures
  - Gestion erreurs complète avec stack trace
- **Boucle principale refactorisée** :
  - Try-catch-finally pour protection complète
  - Logging progression toutes étapes
  - ErrorAction SilentlyContinue sur Get-ChildItem
  - Validation bookmarks avec warnings
- **Initialisation améliorée** :
  - Appel `Initialize-Logging` au démarrage
  - Appel `Test-Prerequisites` avant boucle
  - Bannière console enrichie avec chemin log
- **Traitement images** :
  - Ajout logging debug chaque image
  - Cleanup forcé objets en cas d'erreur

### 📊 Performance
- Aucun impact performance grâce logging asynchrone
- Cleanup garanti évite fuites mémoire

---

## [0.3.0] - 2024-12-24 (tess3.ps1 - version précédente)

### ✨ Ajouté
- **Intégration Word/PDF** : Génération automatique documents depuis template
- **Système bookmarks** : NOM, PRENOM, DATE, RESULTAT
- **Export PDF** : Conversion automatique depuis Word
- **Extraction infos patient** : Fonction `Get-PatientInfoFromFolderName`
- **Intégration images** : Embedding images redimensionnées dans Word
- **Rapport structuré multi-sections** :
  - Volume thyroïdien (lobes droit/gauche, isthme)
  - Echogénicité et vascularisation
  - Documentation nodules
  - Évaluation ganglions

### 🔧 Corrigé
- Séparation mesures normales / nodules / isthme
- Catégorisation par latéralité et type structure

### ⚠️ Problèmes connus (corrigés en v1.0.0)
- Paramètre Tesseract `quiet` invalide
- Catch vides cachent erreurs
- Pas de logging
- Pas de validation démarrage
- Encodage caractères défaillant

---

## [0.2.0] - 2024-12-23 (tess2.ps1)

### ✨ Ajouté
- **Standardisation décimales** : Conversion universelle séparateur point (.)
- **Objets structurés PowerShell** : PSCustomObject avec propriétés
  - `Cote` (RT/LT)
  - `Nodule` (numéro)
  - `Isthme` (boolean)
  - `Texte` (mesure formatée)
- **Conversion unités** : cm → mm automatique (×10)
- **Gestion volumes** : Extraction et formatage volumes
- **Rapport texte structuré** : Génération `_Compte_Rendu.txt`
- **Filtrage amélioré** : Écriture seulement mesures valides

### 🔄 Modifié
- Format sortie : Objets structurés au lieu de chaînes simples
- Meilleure organisation données mesures

---

## [0.1.0] - 2024-12-23 (tess.ps1)

### 🎉 Version initiale

Première version fonctionnelle du concept.

### ✨ Ajouté
- **Extraction OCR basique** : Tesseract pour lecture texte images
- **Sortie texte simple** : Fichier `_Mesures_Globales.txt`
- **Détection structures** :
  - Numéros nodules (N1, N2, etc.)
  - Détection isthme
- **Redimensionnement images** : Largeur 1200px avec préfixe `$`
- **Extraction mesures** : Pattern regex pour format "XX.X cm"

### ⚠️ Limitations
- Pas de normalisation décimales (mix virgule/point)
- Pas d'intégration Word
- Sortie texte brut uniquement
- Pas de structuration données

---

## [Unreleased] - Roadmap future

### 🔮 Planifié pour v1.1.0
- [ ] Interface graphique WPF révision manuelle mesures
- [ ] Statistiques mensuelles (nombre CR, taux succès)
- [ ] Notification email automatique

### 🔮 Planifié pour v2.0.0
- [ ] Support multi-templates (différents examens)
- [ ] API REST intégration PACS
- [ ] Support DICOM natif
- [ ] Détection anomalies IA/ML

---

## Notes de version

### Versioning sémantique

Ce projet utilise [Semantic Versioning](https://semver.org/lang/fr/) :

- **MAJOR** (X.0.0) : Changements incompatibles API
- **MINOR** (x.X.0) : Ajout fonctionnalités rétro-compatibles
- **PATCH** (x.x.X) : Corrections bugs rétro-compatibles

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
