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

**SCP-049** : son toucher tue, et la victime se relève en SCP-049-2. Il « soigne » aussi les cadavres
proches. Ses 049-2 le suivent et attaquent quiconque s'approche de lui.

**SCP-079** : une IA dans un terminal en Heavy Containment. Tant qu'elle est active, elle verrouille ou
ouvre les portes autour des joueurs, déclenche des alarmes qui attirent les zombies, coupe le courant du
confinement (les SCP se réveillent) et diffuse des menaces à la radio sur 107.9 MHz. Pour la reconfiner :
démarrer les 3 panneaux de la salle des générateurs, puis « Surcharger SCP-079 » depuis son terminal
(ce qui termine aussi une brèche en cours).

**SCP-914** : la machine à engrenages (Light Containment). Clic droit → *Utiliser SCP-914*, puis un
réglage (Brut, Grossier, 1:1, Fin, Très fin) pour détruire, abîmer, échanger, réparer ou améliorer l'objet
en main. Une carte d'accès passée en « Fin » monte d'un niveau.

**SCP-008** : chambre du prion en Heavy Containment. Sans masque à gaz filtré ni combinaison NRBC, l'air
infecte. Échantillon et rapport dans la salle.

**SCP-966** et **SCP-939** : 966 est invisible sans les lunettes de vision nocturne et épuise ceux qu'il approche ;
939 imite des voix humaines pour attirer les joueurs, et ne voit pas ceux qui avancent accroupis.

**SCP-294** : distributeur de boissons (Entrance Zone). Eau, café, thé, chocolat… ou une boisson bizarre.

**SCP-714** : l'anneau de jade rend somnolent mais protège du toucher de SCP-049 et de SCP-035.

**SCP-1025** : l'encyclopédie des maladies. Lire une page donne la maladie décrite (rhume, poison,
fracture… ou l'infection de Knox).

**Portes Tesla** : couloirs électrifiés en Heavy Containment, qui frappent tout ce qui passe
(joueurs gravement blessés, zombies détruits).

**Éclairage** : le site est sombre, les lumières clignotent et passent au rouge pendant une brèche.

**Ogive Alpha** : salle de contrôle en Entrance Zone (carte niveau 5). L'armer lance un compte à rebours de
30 min ; à zéro, le site et tout ce qui s'y trouve est détruit. Annulable depuis le même terminal.

**Professions** : Classe-D (commence dans les cellules pendant une brèche), Scientifique (labo, carte
niveau 2) et Garde NTF (salle de sécurité, carte niveau 3).

**Site SCP** : trois niveaux souterrains (Entrance, Heavy et Light Containment) reliés par des ascenseurs
(case jaune), construits au chargement de la zone. Placement : menu admin → *Construire le site SCP ici*.

**Brèche de confinement** : coupure de courant, toutes les portes à carte s'ouvrent, sirènes et
lumières rouges, apparition des SCP et de gardes zombifiés à chaque point de confinement.
Fin automatique après 6 h de jeu (courant et verrous rétablis).

## Tester rapidement (solo, mode debug ou admin)

Clic droit au sol → **Fondation SCP (admin)** :
- *Me donner le kit de test SCP* : toutes les cartes, SCP-500, masques, tenues
- *Faire apparaître ici* : SCP-173, 096, 106, 049, 939, 966, hôte de 035, garde zombifié
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
