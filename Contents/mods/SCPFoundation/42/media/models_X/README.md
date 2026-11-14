# Modèles 3D et textures (à remplacer)

Les tenues utilisent les **modèles vanilla** (repris des fichiers du jeu) avec des **textures SCP** dans `media/textures/SCP/`.
Les textures sont repeintes sur la carte UV des modèles vanilla (même taille, mêmes zones), puis vérifiées par des rendus 3D.
Attention : sur `Boilersuit`, `BulletVest`, `Hazmat` et `JacketLong`, le milieu du dos est coupé par la couture UV (colonnes u = 53 et u = 203 sur 256) ; un texte au dos doit être coupé en deux de part et d'autre.

| Objet | Modèle vanilla de base | Texture |
|---|---|---|
| Combinaison Classe-D | `Boilersuit_Prisoner` | `SCP_ClassD_Jumpsuit.png` |
| Uniforme NTF | `Boilersuit_SWAT` | `SCP_MTF_Uniform.png` |
| Casque NTF | `Hat_Army` | `SCP_MTF_Helmet.png` |
| Gilet NTF | `Vest_BulletSWAT` | `SCP_MTF_Vest.png` |
| Combinaison NRBC | `HazmatSuit` | `SCP_Hazmat_Suit.png` |
| Blouse du scientifique | `JacketLong_Doctor` (`Bob_JacketLong` / `Kate_JacketLong`) | `SCP_LabCoat.png` |
| Masque à gaz | `Hat_GasMask` | `SCP_GasMask.png` |
| SCP-035 | `Hat_HockeyMask` | `SCP_035_Mask.png` |
| SCP-049 | `Boilersuit` + `Hat_GasMask` | `SCP_049_Robe.png`, `SCP_049_Mask.png` |
| SCP-049-2 / 173 / 096 / 106 / 939 / 966 | `Boilersuit` | `SCP_049_2_Skin.png`, `SCP_173_Shell.png`, `SCP_096_Skin.png`, `SCP_106_Skin.png`, `SCP_939_Skin.png`, `SCP_966_Skin.png` |

Pour retoucher une texture : ouvrir le PNG dans Krita / Photopea et peindre par-dessus **sans changer la taille ni déplacer les zones**.

Pour remplacer : déposer le modèle `.fbx`/`.x` ici (par ex. `models_X/Skinned/Clothes/SCP_MTF_Helmet.fbx`),
puis changer `m_MaleModel` / `m_FemaleModel` dans le XML correspondant de `media/clothing/clothingItems/`.

Déjà remplacés (images Gemini) : icônes `media/textures/Item_SCP_*.png`, `poster.png`, `icon.png`, `preview.png`.
Planches de concept pour les futurs modèles 3D : `art/concepts/` à la racine du dépôt (hors du mod).

## Modèles 3D propres (branche `models/creatures-tiles`)

Générés par `tools/build_models.py` (Blender, hors du dépôt) : géométrie, poids sur le squelette de Bob
(transférés depuis `MaleBody.x`), texture cuite depuis des matériaux procéduraux.

| Objet | Modèle | Texture | Remarque |
|---|---|---|---|
| SCP-173 | `skinned/clothes/scp_173.x` | `SCP/SCP_173_Model.png` | statue rigide (os `Bip01_Pelvis`) |
| SCP-096 / 939 / 106 / 966 | `skinned/clothes/scp_0xx.x` | `SCP/SCP_0xx_Model.png` | squelette complet |
| SCP-049 (capuche + bec) | `static/clothes/scp_049_mask.x` | `SCP/SCP_049_BeakMask.png` | os de la tête |
| Lunettes de vision nocturne | `static/clothes/scp_nvg.x` | `SCP/SCP_NVG.png` | os de la tête |
| SCP-714 | `skinned/clothes/scp_714_ring.x` | `SCP/SCP_714_Ring.png` | os `Bip01_L_Finger1` |

Les créatures masquent tout le corps (masques 0 à 10) et apparaissent toujours en homme
(`MALE_ONLY` dans `SCP_Spawner.lua`), car leurs poids sont calculés pour le squelette de Bob.
Les anciennes textures sur combinaison (`SCP_173_Shell.png`, `SCP_096_Skin.png`…) restent en repli.

## Tuiles 2D

`media/texturepacks/scp_facility.pack` + `media/scp_facility.tiles` (déclarés dans `mod.info`, numéro 1914),
tileset `scp_facility_01` : 0-2 SCP-914 (entrée, engrenages, sortie), 3 SCP-294, 4 terminal SCP-079,
5 panneau de générateur, 6 console de l'ogive Alpha, 7-8 portique Tesla (bord ouest / nord).
Planche : `art/scp_facility_01_tilesheet.png`. Si le pack ne se charge pas, `F.Fallback`
(`SCP_Facility.lua`) remet les tuiles vanilla d'avant.

Encore temporaires :
- Sons : `media/sound/*.ogg` (bips et bruits générés)
- Tuiles de corrosion / dimension de poche : constantes en haut de `media/lua/shared/SCP_106_Logic.lua`
