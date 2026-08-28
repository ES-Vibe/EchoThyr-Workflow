# Lexique des localisations spatiales des nodules

Vocabulaire utilisé pour situer un nodule, depuis la légende de l'échographe
jusqu'au compte rendu Word. Ce document décrit ce que le code fait réellement :
les sources sont `src/schema/position_parser.py`, `src/schema/models.py`,
`src/schema/thyroid_renderer.py` et `src/schema/measurement_table.py`.

---

## 1. Convention de lecture du schéma

Le schéma est vu **de face, comme on regarde le patient**. Le lobe **droit du
patient est donc affiché à gauche** de l'image.

Le point le plus important : **les axes ne signifient pas la même chose selon la
vue.** C'est la source d'erreur la plus fréquente à la relecture.

| Vue | Axe horizontal | Axe vertical |
|---|---|---|
| **Vue de face** (centre) | transverse — droite ↔ gauche | craniocaudal — haut ↔ bas |
| **Coupe longitudinale** (côtés) | craniocaudal — haut ↔ bas | antéro-postérieur — avant ↔ arrière |

Sur une coupe longitudinale, l'axe haut/bas du patient est donc représenté
**horizontalement**. Les croix d'orientation sous chaque vue rappellent cette
correspondance.

---

## 2. Abréviations des croix d'orientation

| Sigle | Signification | Équivalent anatomique |
|---|---|---|
| **HT** | haut | supérieur, crânial |
| **BS** | bas | inférieur, caudal |
| **AV** | avant | antérieur, ventral |
| **AR** | arrière | postérieur, dorsal |
| **D** | droite du patient | lobe droit |
| **G** | gauche du patient | lobe gauche |

- Croix des **coupes longitudinales** : AV (haut), AR (bas), HT (gauche), BS (droite)
- Croix de la **vue de face** : HT (haut), BS (bas), D (gauche), G (droite)

---

## 3. Les trois axes de localisation

Un nodule est décrit par trois descripteurs indépendants, plus un cas
particulier (isthme). Chacun peut être inconnu.

### 3.1 Étage — axe craniocaudal

Où le nodule se situe dans la hauteur du lobe.

| Valeur | Libellé au compte rendu | `VerticalLevel` |
|---|---|---|
| SUP | tiers supérieur | `SUPERIOR` |
| MOY | tiers moyen | `MIDDLE` |
| INF | tiers inférieur | `INFERIOR` |
| — | *(omis)* | `UNKNOWN` |

### 3.2 Profondeur — axe antéro-postérieur

Où le nodule se situe entre la face avant et la face arrière du lobe.

| Valeur | Libellé au compte rendu | `DepthLevel` |
|---|---|---|
| ANT | antérieur | `ANTERIOR` |
| POST | postérieur | `POSTERIOR` |
| — | *(omis)* | `UNKNOWN` |

### 3.3 Latéralité — axe transverse

Où le nodule se situe entre le bord externe du lobe et l'isthme. À ne pas
confondre avec le **côté** (lobe droit / lobe gauche), qui est une information
distincte.

| Valeur | Libellé au compte rendu | `LateralLevel` | Direction |
|---|---|---|---|
| LAT | latéral | `LATERAL` | vers l'extérieur du cou |
| MED | médial | `MEDIAL` | vers l'isthme, la trachée |
| — | *(omis)* | `UNKNOWN` | centré dans le lobe |

### 3.4 Isthme

Un nodule isthmique n'appartient à aucun lobe. Il porte le libellé « isthme »
seul, sans étage ni profondeur ni latéralité, apparaît au centre de la vue de
face et **n'est représenté sur aucune coupe longitudinale**.

---

## 4. Où chaque descripteur est visible

Toutes les vues ne portent pas toute l'information. Un descripteur absent d'une
vue n'y est simplement pas représenté — ce n'est pas une omission.

| Descripteur | Vue de face | Coupe longitudinale | Tableau |
|---|---|---|---|
| Côté (D / G) | ✅ lobe concerné | ✅ coupe concernée | ✅ colonne « Côté » |
| Étage (SUP / MOY / INF) | ✅ hauteur | ✅ position horizontale | ✅ colonne « Siège » |
| Profondeur (ANT / POST) | ❌ | ✅ position verticale | ✅ colonne « Siège » |
| Latéralité (LAT / MED) | ✅ décalage horizontal | ❌ | ✅ colonne « Siège » |
| Isthme | ✅ centre | ❌ | ✅ « Isthme » |

La profondeur ne se lit donc **que** sur les coupes longitudinales, et la
latéralité **que** sur la vue de face. Le tableau, lui, porte toujours
l'information complète.

### Décalages appliqués

Valeurs en pixels du repère de dessin, pour référence de maintenance.

| Vue | Descripteur | Décalage |
|---|---|---|
| Face | SUP / MOY / INF | y = 202 / 282 / 352 |
| Face | LAT | 26 px vers l'extérieur |
| Face | MED | 15 px vers l'isthme |
| Coupe | SUP / MOY / INF | x = −52 / 0 / +52 |
| Coupe | ANT / POST | y = −18 / +20 |

L'asymétrie 26 / 15 est voulue : le décalage médial reste plus faible pour que
le nodule ne franchisse pas le bord médial du lobe.

Ce sont les décalages **nominaux**. Ils peuvent être réduits à l'affichage : une
ellipse est recentrée sur la place réellement disponible à son niveau, le lobe
étant plus étroit à ses pôles qu'en son milieu.

---

## 5. Vocabulaire reconnu à la lecture des légendes

L'OCR lit la légende incrustée par l'échographe. Le parser accepte plusieurs
formes pour chaque notion, y compris des erreurs de lecture courantes.

| Notion | Formes acceptées |
|---|---|
| Supérieur | `SUP`, `SUPERIEUR`, `SUPER` |
| Moyen | `MOY`, `MOYEN`, `MID`, `MIDDLE` |
| Inférieur | `INF`, `INFERIEUR`, `INFER` |
| Antérieur | `ANT`, `ANTERIEUR` |
| Postérieur | `POST`, `POSTERIEUR`, `OOST` ⚠, `P0ST` ⚠ |
| Latéral | `EXT`, `EXTERNE`, `LAT`, `LATERAL` |
| Médial | `INT`, `INTERNE`, `MED`, `MEDIAL` |
| Isthme | `ISTHME`, `ISTHMUS`, `ISTHMIQUE` |

⚠ = erreur de lecture OCR tolérée (`O` lu pour `P`, `0` lu pour `O`).

Noter que l'échographe GE écrit la latéralité **`EXT` / `INT`** (externe /
interne) là où le compte rendu dit **latéral / médial**. Les deux couples
désignent la même chose.

### Termes ignorés

Ces mots peuvent apparaître dans la légende sans être des descripteurs de
position ; ils sont écartés :

`KYSTE`, `AMAS`, `PONCTION`, `MACROCAL`, `MICROCALC`, `NODULE`, `LOBE`,
`THYROID`, `THYROIDE`, `DROIT`, `GAUCHE`, `RIGHT`, `LEFT`, `RT`, `LT`,
`TRANS`, `LONG`, `SAG`

### Format de légende GE

```
RT THYROID LOBE N1 SUP EXT POST A0%
                └┬┘ └─────┬────┘
            n° nodule   position
```

Les descripteurs sont extraits entre le numéro de nodule et le marqueur `A…%`,
par l'expression `N\d+[DG]?\s+(.*?)\s*A[O0]?\d*%`.

---

## 6. Dimensions

Trois dimensions par nodule, chacune sur un des trois axes anatomiques.

| Colonne du tableau | Axe | Champ du code |
|---|---|---|
| **Long.** (L) | craniocaudal | `height_mm` |
| **Larg.** (l) | antéro-postérieur | `length_mm` |
| **Épais.** (É) | transverse | `width_mm` |

> ⚠ Convention issue du design : « Épaisseur » désigne ici l'axe **transverse**,
> et « Largeur » l'axe **antéro-postérieur**. En pratique courante ces deux
> termes sont souvent employés dans l'autre sens — se fier à l'axe, pas au mot.

Les en-têtes sont écrits « Long. / Larg. / Épais. » et non « L / l / É » : en
capitales, `L` et `l` deviennent indistinguables.

**Volume** — ellipsoïde, exprimé en mL :

```
V = π/6 × L × l × É        (mm³ ÷ 1000)
```

### Taille des nodules sur le schéma

Un nodule occupe sur le schéma **la même fraction du lobe que dans la réalité**.
L'échelle est déduite des dimensions du lobe, pas d'une constante : un nodule de
15 mm paraît deux fois plus petit dans un lobe de 90 mm que dans un lobe de
45 mm.

Un nodule plus gros que le lobe déborde volontairement du contour ; le tracé de
l'organe est redessiné par-dessus pour que le dépassement se lise comme une
information et non comme un défaut d'affichage.

---

## 7. Exemple complet

Légende lue sur l'image :

```
RT THYROID LOBE N1 SUP EXT POST A0%
```

Interprétation :

| Descripteur | Valeur |
|---|---|
| Côté | lobe droit *(affiché à gauche du schéma)* |
| Étage | tiers supérieur |
| Latéralité | latéral *(`EXT`)* |
| Profondeur | postérieur |

Ligne produite au compte rendu :

| Nodule | Côté | Siège | Long. | Larg. | Épais. | Volume |
|---|---|---|---|---|---|---|
| N1 | Droit | tiers supérieur, postérieur, latéral | 12,5 | 8,3 | 9,1 | 0,49 |

Le siège est dérivé des mêmes descripteurs que la position sur le schéma : il
n'est jamais saisi une seconde fois, schéma et tableau ne peuvent donc pas se
contredire.
