# SCP Foundation - Facility & Anomalies

Mod Project Zomboid **Build 42** : un site de la Fondation SCP à explorer (souterrain sur trois zones,
complexe fortifié en surface), ses SCP, ses anomalies, ses armes, les portes à carte et les brèches de
confinement. Textes en anglais et en français.

> Les modèles 3D, textures, icônes, sons et l'affiche sont **temporaires**.
> Voir [`media/models_X/README.md`](Contents/mods/SCPFoundation/42/media/models_X/README.md) pour la liste à remplacer.

## Installation

Copier le dossier du dépôt dans `~/Zomboid/Workshop/` (ou seulement `Contents/mods/SCPFoundation`
dans `~/Zomboid/mods/`), puis activer **SCP Foundation - Facility & Anomalies** dans le menu Mods.

## Organisation du dépôt

```
Contents/mods/SCPFoundation/      le mod lui-même (c'est ce dossier qu'on installe)
├── common/                       requis par la Build 42
└── 42/
    ├── mod.info, poster.png, icon.png
    └── media/
        ├── lua/client|shared|server   logique (shared/SCP_Facility_Data.lua est généré)
        ├── lua/shared/Translate/EN|FR
        ├── scripts/              objets, armes, modèles, tenues, sons
        ├── clothing/             tenues (XML) et outfits des entités
        ├── maps/SCP Site/        région de départ « Site SCP » (sans nouvelles cellules)
        ├── models_X/             modèles 3D (voir son README)
        ├── textures/, sound/, texturepacks/, scp_facility.tiles
        └── sandbox-options.txt
tools/                            scripts qui génèrent le plan, les tuiles, les icônes, les armes (voir tools/README.md)
art/
├── tilesheets/                   planches de tuiles (sources éditables du .pack)
├── renders/                      plan et aperçus du site, rendus des armes
├── concepts/                     planches de concept (hors jeu)
└── sources/cb_textures/          textures de SCP – Containment Breach (CC BY-SA 3.0)
docs/TODO.md                      liste des demandes et de leur avancement
CREDITS_SOUNDS.md, CREDITS_TEXTURES.md   crédits et licences des sons et textures
preview.png, workshop.txt         fichiers du Steam Workshop
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

**SCP-173** : une statue, indestructible. Jauge de clignement en haut de l'écran (touche **B** pour
cligner volontairement). Tant que personne ne le regarde, il avance par sauts d'une case ; collé à un
joueur qui cligne ou tourne le dos, il lui brise la nuque.

**SCP-096** : pleure sans bouger. Le regarder en face déclenche 5 à 10 s de cris, puis il court
après ce joueur en cassant portes, fenêtres et barricades, jusqu'à sa mort.

**SCP-035** : porté, il vide la santé et la santé mentale mais donne endurance, repos et
+8 de capacité de port. Au bout de 30 min il ne s'enlève plus ; gardé trop longtemps en poche,
il se met tout seul. Si le porteur meurt, un « hôte possédé » rapide et résistant se relève.

**SCP-106** : traverse murs et étages en ligne droite vers le joueur le plus proche, laisse des
flaques de corrosion (brûlent les pieds sans combinaison NRBC). Son contact envoie dans la
**dimension de poche** : une salle souterraine où l'on saigne, avec 4 sorties dont une seule
ramène à la surface.
Reconfinement : le **broyeur de fémur** (Heavy Containment, carte niveau 5). Déposer un corps à côté
de la console (le sacrifice), puis *Activer le broyeur de fémur* : les cris attirent SCP-106 pendant
30 min. Quand il est dans le broyeur, lancer le *Rappel magnétique* : il retourne dans sa cellule et y
dort, même pendant la brèche en cours, jusqu'à la brèche suivante.

**SCP-049** : marche vers le patient le plus proche et parle ; il ne mord pas, son toucher tue et la victime
se relève en SCP-049-2. Il « soigne » aussi les cadavres proches. Ses 049-2 le suivent et attaquent
quiconque s'approche de lui.

**Petites anomalies** : SCP-207 (cola), 268 (casquette), 330 (bonbons), 005 (passe-partout), 109 (gourde),
458 (pizza), 427 (médaillon), 018 (super balle), clic droit pour les utiliser.

**Armes de la Fondation** : masse à choc à deux mains (décharge électrique, 20 charges, se recharge avec une
pile), carabine Epsilon (5.56), fusil à pompe anti-émeute, pistolet de service (9 mm). Modèles faits par
`tools/make_weapon_models.py`, munitions et sons de tir du jeu.

**SCP-079** : une IA dans un terminal en Heavy Containment. Tant qu'elle est active, elle verrouille ou
ouvre les portes autour des joueurs, déclenche des alarmes qui attirent les zombies, coupe le courant du
confinement (les SCP se réveillent) et diffuse des menaces à la radio sur 107.9 MHz. Pour la reconfiner :
démarrer les 3 panneaux de la salle des générateurs, puis « Surcharger SCP-079 » depuis son terminal
(ce qui termine aussi une brèche en cours).

**SCP-914** : la machine à engrenages (Light Containment), entre deux cabines. On dépose les objets dans la
cabine d'entrée (à gauche, comme un meuble), clic droit sur la machine → *Utiliser SCP-914* → un réglage
(Brut, Grossier, 1:1, Fin, Très fin). Après 16 s, le résultat sort dans la cabine de droite. Recettes
dédiées (bois, métal, lames, armes, tissu, médicaments, électronique, équipement de la Fondation),
puis règles générales : Brut détruit en débris, Grossier démonte ou use, 1:1 échange, Fin répare ou
améliore, Très fin est imprévisible (parfait, doublé, transformé ou disparu). Les cartes changent de niveau.

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

**Professions** : Classe-D (commence dans les cellules pendant une brèche), Scientifique (bureau des
chercheurs, carte niveau 3) et Garde NTF (salle de sécurité, carte niveau 4). Un écran noir cache le
transfert vers le site au début de la partie.

**Site SCP** : un niveau souterrain en trois zones qui s'enchaînent comme dans Containment Breach (confinement
léger, confinement lourd, zone d'entrée), couloirs de 2 cases, points de contrôle à carte entre les zones. En
surface : un complexe fortifié en béton, relié à la ville par une route d'accès. Mur d'enceinte de deux
étages avec barbelés, grande porte, cour d'entrée avec poste de garde et tour de guet (escaliers jusqu'à la
cabine vitrée), porte intérieure, puis trois cours : garage, bâtiment de la Porte A (toit avec panneaux
solaires et ventilations) et centrale électrique. L'ascenseur de la Porte A est une cabine dans un puits :
on voit le personnage descendre et la zone d'entrée apparaître (option *Ascenseur : descente visible*,
désactivable pour revenir à un fondu). Les portes du site coulissent.
Placement :
- région de départ **Site SCP** (nouvelle partie) : toujours au même endroit, en forêt au nord-est de
  West Point, marqué « SITE SCP » sur la carte du monde ;
- sinon, au début d'une partie avec un métier SCP : sur le terrain libre le plus proche (sans maisons) ;
- ou menu admin → *Construire le site SCP* à l'endroit où la route d'accès rejoint une route.
Plan : `art/renders/site_plan.png`, rendu : `art/renders/rendu_exterieur_site.png`.

**Brèche de confinement** : coupure de courant, toutes les portes à carte s'ouvrent, sirènes et
lumières rouges, apparition des SCP et de gardes zombifiés à chaque point de confinement.
Fin automatique après 6 h de jeu (courant et verrous rétablis).

## Sons

La plupart des sons viennent de *SCP – Containment Breach* (CC BY-SA 3.0) ; ceux de la masse à choc et de
quelques anomalies sont synthétisés par le mod : voir `CREDITS_SOUNDS.md`.

## Tester rapidement (solo, mode debug ou admin)

Clic droit au sol → **Fondation SCP (admin)** :
- *Me donner le kit de test SCP* : toutes les cartes, SCP-500, masques, tenues
- *Faire apparaître ici* : SCP-173, 096, 106, 049, 939, 966, hôte de 035, garde zombifié
- *Ajouter un point de confinement* : où chaque SCP sera relâché pendant une brèche
- *Déclencher / Terminer une brèche de confinement*

Tous les réglages (intervalle de clignement, portée de 173, vitesse de 106, chance de brèche…)
sont dans les **options de partie (Sandbox) → SCP Foundation**.

## Limites connues

- Le site est construit par le mod sur la carte du jeu (pas encore de cellules de carte à lui).
- Pensé en priorité pour le **solo** (pas encore testé en jeu). En multijoueur, les commandes passent par le
  serveur, mais les mouvements de 173 et 106 sont calculés sur le client du joueur ciblé et
  peuvent saccader.
- La dimension de poche est construite localement sous le joueur (niveau Z réglable).
- SCP-096 casse les obstacles, mais pas les murs de la carte.
