# DICOM Worklist Server - Doctolib → Échographe GE

Serveur DICOM Modality Worklist (MWL) permettant de synchroniser les rendez-vous Doctolib avec un échographe GE Logiq.

## Fonctionnement

```
┌─────────────────┐         ┌──────────────────┐         ┌─────────────────┐
│    Doctolib     │  CSV    │   Ce Serveur     │  DICOM  │  Échographe GE  │
│   (Export RDV)  │ ──────► │   (Worklist)     │ ◄────── │   Logiq P9      │
└─────────────────┘         └──────────────────┘         └─────────────────┘
```

1. Exportez vos RDV depuis Doctolib (fichier CSV)
2. Lancez ce serveur sur votre PC
3. L'échographe interroge le serveur et affiche la liste des patients
4. Sélectionnez le patient directement sur l'échographe

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
  ae_title: "WORKLIST"  # Nom du serveur DICOM
  port: 4242            # Port d'écoute

csv:
  path: ""              # Chemin CSV (auto-détection si vide)
  filter_echo_only: true # Filtrer uniquement les échos
```

### 2. Configuration de l'échographe GE Logiq P9

1. Accédez aux **Paramètres DICOM** de l'échographe
2. Allez dans **Worklist** > **Configuration** > **Add Server**
3. Configurez :
   - **AE Title** : `WORKLIST` (doit correspondre à config.yaml)
   - **IP Address** : L'adresse IP de votre PC
   - **Port** : `4242` (doit correspondre à config.yaml)
4. Sauvegardez et testez la connexion

### Trouver l'adresse IP de votre PC

```cmd
ipconfig
```
Cherchez l'adresse IPv4 (ex: 192.168.1.100)

## Utilisation

### 1. Exporter les RDV depuis Doctolib

1. Connectez-vous à Doctolib Pro
2. Allez dans **Agenda** > **Export**
3. Sélectionnez la date du jour
4. Téléchargez le fichier CSV

### 2. Lancer le serveur

Double-cliquez sur `Lancer_Worklist.bat`

Ou en ligne de commande :
```bash
python main.py
```

### 3. Sur l'échographe

1. Appuyez sur **Patient** ou **Worklist**
2. Cliquez sur **Query** ou **Rechercher**
3. La liste des patients du jour apparaît
4. Sélectionnez le patient pour commencer l'examen

## Structure des fichiers

```
DICOMWorklist/
├── main.py                 # Point d'entrée principal
├── worklist_server.py      # Serveur DICOM Worklist
├── doctolib_parser.py      # Parser CSV Doctolib
├── config.yaml             # Configuration
├── requirements.txt        # Dépendances Python
├── Lancer_Worklist.bat     # Lanceur Windows
└── README.md               # Documentation
```

## Dépannage

### L'échographe ne trouve pas le serveur

1. Vérifiez que le PC et l'échographe sont sur le même réseau
2. Vérifiez que le pare-feu Windows autorise le port 4242
3. Testez avec : `ping [IP de l'échographe]`

### Ajouter une exception au pare-feu Windows

```cmd
netsh advfirewall firewall add rule name="DICOM Worklist" dir=in action=allow protocol=TCP localport=4242
```

### Aucun patient n'apparaît

1. Vérifiez que le fichier CSV est bien dans Downloads
2. Vérifiez que les RDV sont pour la date du jour
3. Vérifiez les logs dans `worklist_server.log`

### Le port 4242 est déjà utilisé

Modifiez le port dans `config.yaml` et sur l'échographe.

## Sécurité

- Ce serveur est destiné à un usage local uniquement
- Ne l'exposez pas sur Internet
- Les données patients transitent en clair sur le réseau local

## Licence

MIT License

---

Développé avec [Claude Code](https://claude.com/claude-code)
