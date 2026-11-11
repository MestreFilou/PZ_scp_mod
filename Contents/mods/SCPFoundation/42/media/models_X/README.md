# Modèles 3D et textures (à remplacer)

Les tenues utilisent les **modèles vanilla** (repris des fichiers du jeu) avec des **textures SCP** dans `media/textures/SCP/`.
Ces textures sont des recolorations des textures d'origine : le patron (carte UV) est donc respecté.

| Objet | Modèle vanilla de base | Texture |
|---|---|---|
| Combinaison Classe-D | `Boilersuit_Prisoner` | `SCP_ClassD_Jumpsuit.png` |
| Uniforme NTF | `Boilersuit_SWAT` | `SCP_MTF_Uniform.png` |
| Casque NTF | `Hat_Army` | `SCP_MTF_Helmet.png` |
| Gilet NTF | `Vest_BulletSWAT` | `SCP_MTF_Vest.png` |
| Combinaison NRBC | `HazmatSuit` | `SCP_Hazmat_Suit.png` |
| Masque à gaz | `Hat_GasMask` | `SCP_GasMask.png` |
| SCP-035 | `Hat_HockeyMask` | `SCP_035_Mask.png` |
| SCP-173 / 096 / 106 | `Boilersuit` | `SCP_173_Shell.png`, `SCP_096_Skin.png`, `SCP_106_Skin.png` |

Pour retoucher une texture : ouvrir le PNG dans Krita / Photopea et peindre par-dessus **sans changer la taille ni déplacer les zones**.

Pour remplacer : déposer le modèle `.fbx`/`.x` ici (par ex. `models_X/Skinned/Clothes/SCP_MTF_Helmet.fbx`),
puis changer `m_MaleModel` / `m_FemaleModel` dans le XML correspondant de `media/clothing/clothingItems/`.

Déjà remplacés (images Gemini) : icônes `media/textures/Item_SCP_*.png`, `poster.png`, `icon.png`, `preview.png`.
Planches de concept pour les futurs modèles 3D : `art/concepts/` à la racine du dépôt (hors du mod).

Encore temporaires :
- Modèles 3D propres aux SCP (173, 096, 106 portent pour l'instant une combinaison)
- Sons : `media/sound/*.ogg` (bips et bruits générés)
- Tuiles de corrosion / dimension de poche : constantes en haut de `media/lua/shared/SCP_106_Logic.lua`
