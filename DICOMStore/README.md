# DICOM Storage Server (PACS Local)

Serveur d'archivage DICOM local pour recevoir et stocker automatiquement les images depuis un échographe GE Logiq.

## Fonctionnement

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│  Échographe GE  │  DICOM  │   Ce Serveur     │         │  Fichiers       │
│   Logiq P9      │ ──────► │   (C-STORE)      │ ──────► │  organisés      │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

1. Configurez l'échographe pour envoyer les images vers ce serveur
2. À chaque fin d'examen, les images sont automatiquement archivées
3. Les fichiers sont organisés par patient et date

## Installation

### Prérequis

- Python 3.8+
- Échographe GE Logiq avec DICOM activé
- PC et échographe sur le même réseau

### Installation des dépendances

```bash
pip install -r requirements.txt
```

## Configuration

### 1. Configuration du serveur (config.yaml)

```yaml
server:
  ae_title: "PACS_LOCAL"  # Nom du serveur DICOM
  port: 4243              # Port d'écoute

storage:
  root_path: "C:/Users/Emeric/Documents/DICOM_Archive"
  folder_structure: "{patient_name}_{patient_id}/{study_date}"
  export_images: true     # Exporter aussi en PNG
```

### 2. Configuration de l'échographe GE Logiq P9

1. Accédez aux **Paramètres DICOM** de l'échographe
2. Allez dans **Store** ou **Archive** > **Configuration** > **Add Server**
3. Configurez :
   - **AE Title** : `PACS_LOCAL`
   - **IP Address** : L'adresse IP de votre PC
   - **Port** : `4243`
4. Sauvegardez et testez la connexion

## Utilisation

### Lancer le serveur

Double-cliquez sur `Lancer_PACS.bat`

Ou en ligne de commande :
```bash
python main.py
```

### Sur l'échographe

1. Effectuez votre examen normalement
2. À la fin, appuyez sur **Store** ou **Archive**
3. Sélectionnez le serveur `PACS_LOCAL`
4. Les images sont envoyées automatiquement

## Structure des fichiers archivés

```
DICOM_Archive/
├── DUPONT_Jean_12345/
│   ├── 2026-01-06/
│   │   ├── 1.2.3.4.5.6.7.8.dcm
│   │   ├── 1.2.3.4.5.6.7.8.png
│   │   └── ...
│   └── 2026-01-07/
│       └── ...
└── MARTIN_Marie_67890/
    └── ...
```

## Dépannage

### L'échographe ne trouve pas le serveur

1. Vérifiez que le PC et l'échographe sont sur le même réseau
2. Vérifiez que le pare-feu Windows autorise le port 4243
3. Testez avec : `ping [IP du PC]`

### Ajouter une exception au pare-feu Windows

```cmd
netsh advfirewall firewall add rule name="DICOM Storage" dir=in action=allow protocol=TCP localport=4243
```

## Utilisation avec le Worklist

Ce serveur peut fonctionner en parallèle avec le serveur Worklist :

| Serveur | Port | Fonction |
|---------|------|----------|
| Worklist | 4242 | Liste des patients à examiner |
| Storage | 4243 | Archivage des images |

## Licence

MIT License

---

Développé avec [Claude Code](https://claude.com/claude-code)
