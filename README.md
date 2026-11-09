# SCP Foundation - Facility & Anomalies

Mod Project Zomboid **Build 42** : équipement de la Fondation SCP, portes à carte, anomalies
(SCP-173, SCP-096, SCP-035, SCP-106, SCP-500) et brèches de confinement. Textes en anglais et en français.

> Les modèles 3D, textures, icônes, sons et l'affiche sont **temporaires**.
> Voir [`media/models_X/README.md`](Contents/mods/SCPFoundation/42/media/models_X/README.md) pour la liste à remplacer.

## Installation

Copier le dossier du dépôt dans `~/Zomboid/Workshop/` (ou seulement `Contents/mods/SCPFoundation`
dans `~/Zomboid/mods/`), puis activer **SCP Foundation - Facility & Anomalies** dans le menu Mods.

```
Contents/mods/SCPFoundation/
├── common/                 (requis par la Build 42)
└── 42/
    ├── mod.info, poster.png, icon.png
    └── media/
        ├── clothing/        tenues (XML) + outfits des entités
        ├── scripts/         objets, tenues, armes, sons
        ├── lua/client|shared|server
        ├── lua/shared/Translate/EN|FR
        ├── sandbox-options.txt
        └── textures/, sound/, models_X/
```

## Contenu

**Objets** : combinaison Classe-D, casque / gilet / uniforme NTF, combinaison NRBC, masque à gaz
(+ filtres qui s'usent), cartes d'accès niveaux 1 à 5, SCP-500 (5 pilules), masque SCP-035,
matraque et couteau NTF, document de procédures. Ajoutés au butin vanilla (désactivable).

**Portes à carte** : clic droit sur une porte sécurisée → *Passer la carte*. Une carte de niveau
égal ou supérieur ouvre la porte, qui se reverrouille une fois refermée. Les admins choisissent le
niveau d'une porte par clic droit (*SCP : niveau d'accès de la porte*).

**SCP-500** : clic droit sur le flacon → *Prendre une pilule*. Guérit l'infection, toutes les
blessures, fractures, poison, et remet santé et fatigue à fond.

**SCP-173** : immobile tant qu'un joueur le regarde. Jauge de clignement en haut de l'écran
(touche **B** pour cligner volontairement). Si le joueur cligne ou tourne le dos à moins de
10 cases, il apparaît derrière lui et lui brise la nuque.

**SCP-096** : pleure sans bouger. Le regarder en face déclenche 5 à 10 s de cris, puis il court
après ce joueur en cassant portes, fenêtres et barricades, jusqu'à sa mort.

**SCP-035** : porté, il vide la santé et la santé mentale mais donne endurance, repos et
+8 de capacité de port. Au bout de 30 min il ne s'enlève plus ; gardé trop longtemps en poche,
il se met tout seul. Si le porteur meurt, un « hôte possédé » rapide et résistant se relève.

**SCP-106** : traverse murs et étages en ligne droite vers le joueur le plus proche, laisse des
flaques de corrosion (brûlent les pieds sans combinaison NRBC). Son contact envoie dans la
**dimension de poche** : une salle souterraine où l'on saigne, avec 4 sorties dont une seule
ramène à la surface.

**Brèche de confinement** : coupure de courant, toutes les portes à carte s'ouvrent, sirènes et
lumières rouges, apparition des SCP et de gardes zombifiés à chaque point de confinement.
Fin automatique après 6 h de jeu (courant et verrous rétablis).

## Tester rapidement (solo, mode debug ou admin)

Clic droit au sol → **Fondation SCP (admin)** :
- *Me donner le kit de test SCP* : toutes les cartes, SCP-500, masques, tenues
- *Faire apparaître ici* : SCP-173, 096, 106, hôte de 035, garde zombifié
- *Ajouter un point de confinement* : où chaque SCP sera relâché pendant une brèche
- *Déclencher / Terminer une brèche de confinement*

Tous les réglages (intervalle de clignement, portée de 173, vitesse de 106, chance de brèche…)
sont dans les **options de partie (Sandbox) → SCP Foundation**.

## Limites connues

- Pas de carte de l'installation pour l'instant : les portes et points de confinement se placent
  à la main (menu admin). `SCP.Doors.SpriteLevels` permettra de sécuriser automatiquement les
  portes d'une future carte.
- Pensé en priorité pour le **solo** (pas encore testé en jeu). En multijoueur, les commandes passent par le
  serveur, mais les mouvements de 173 et 106 sont calculés sur le client du joueur ciblé et
  peuvent saccader.
- La dimension de poche est construite localement sous le joueur (niveau Z réglable).
- SCP-096 casse les obstacles, mais pas les murs de la carte.
