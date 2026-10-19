# Décisions de cohérence

Arbitrages entre DA.md, GDD.md et TECH.md, validés le 2026-10-18. En cas de conflit, ce fichier prime sur les trois documents de référence.

## Machine à états

États : `INTRO`, `STORE`, `SCANNING`, `OPENING`, `TERRACE`, `REVEAL`, `CHAIN`, `RECAP`, `RETURN`, `EXIT`, `END_MENU`, `ERROR`, `SAFE_RETURN`.

| Depuis | Vers | Déclencheur |
| --- | --- | --- |
| INTRO | STORE | lancement de l'expérience |
| STORE | SCANNING | cible visée + validation |
| SCANNING | OPENING | module de filière chargé, collisions prêtes |
| OPENING | TERRACE | animation des portes terminée |
| TERRACE | REVEAL | joueur dans la zone `ANCHOR_*_VIEW` |
| REVEAL | CHAIN | toit retiré |
| CHAIN | RECAP | timeline terminée |
| RECAP | CHAIN | « Revoir » |
| TERRACE, REVEAL, CHAIN, RECAP | RETURN | joueur refranchit le seuil |
| RETURN | STORE | portes refermées après le passage |
| RETURN | TERRACE | joueur repasse côté terrasse avant la fermeture (portes rouvertes) |
| STORE | EXIT | joueur franchit le seuil de la porte d'entrée |
| EXIT | END_MENU | arrivée sur le parvis |
| EXIT | STORE | joueur rentré dans le magasin avant le parvis |
| END_MENU | STORE | « Revenir dans le magasin » |
| tout état | ERROR | échec de chargement ou état incohérent |
| ERROR | SAFE_RETURN → STORE | message affiché, joueur replacé au magasin |

- La pause est un drapeau orthogonal, pas un état. Elle se déclenche par `Échap` (perte du verrouillage du pointeur), `P` ou l'onglet masqué ; l'horloge de jeu s'arrête et reprend sans saut.
- Un rayon est marqué « exploré » quand sa chaîne atteint `RECAP` ; un retour anticipé ne le marque pas.
- Si le navigateur refuse le verrouillage du pointeur, la vue se pilote en glisser-déposer à la souris.
- Le toit relève de l'état `REVEAL` ; la timeline commence après. `revealRoof` n'est pas un événement de timeline.

## Contrats de données

- `TimelineStep.event` : `"collect" | "load" | "drive" | "process" | "deliver"`. Au lieu d'un tableau `targets` positionnel, des champs nommés : `from` / `to` (groupes dont les enfants apparaissent ou disparaissent un à un) pour collect, load, process, deliver ; `vehicle` + `pathId` pour drive.
- La scène d'une chaîne est une fonction pure du temps écoulé : état initial, puis chaque étape commencée dans l'ordre. Pause, replay et reprise sont donc déterministes.
- `ChainConfig` : `captions`, `terraceCaption`, `revealCaption`, `timeline`, `recap` (3 cartels max), `sources`, `systemType`. `exitAnchor` est abandonné (le retour s'appuie sur la façade du rayon).
- Fin de chaîne : le panneau récapitulatif libère le pointeur et propose « Revoir la chaîne », « Revenir au magasin » et « Rester sur la terrasse » ; les sources sont dans un `<details>` accessible au clavier.
- Schéma des cartels : voir CONTENT_SCHEMA.md.

## Filière œufs (prototype)

- Système d'élevage représenté : non tranché. `systemType` vaut `TODO_SOURCE` et un cartel l'indique tant que L214 n'a pas choisi.
- Fin de vie des poules : hors prototype.
- Aucun camion d'animaux ni abattoir dans le circuit des œufs.

## Conventions Blender / GLB (complément à TECH.md §03)

| Élément | Nom | Rôle |
| --- | --- | --- |
| Collider | `COL_*` | volume simplifié, caché au rendu |
| Trajectoire | `PATH_<FILIÈRE>_<ROUTE>_<NN>` | suite d'empties ordonnés → `CatmullRomCurve3` (le glTF n'exporte pas les courbes) |
| Apparition | `SPAWN_PLAYER` | position du joueur ; regard vers son -Z local (glTF) |
| Sortie | `TRIGGER_EXIT` | volume devant la porte d'entrée |
| Signalétique | `SIGN_*` | panneau ; le libellé est dessiné à l'exécution |
| Données de maillage | `ME_*` | évite toute collision avec les noms de nœuds |

- Les nœuds `COL_*`, `SCAN_*`, `TRIGGER_*` sont exportés puis masqués par `AssetManager`.
- Le module de terrasse est un GLB distinct, posé sur `ANCHOR_<FILIÈRE>_TERRACE` (face arrière du mur, niveau du sol) et retiré de la scène au retour en `STORE`.
- `TRIGGER_<FILIÈRE>_ENTRY` couvre le seuil, de la façade du rayon jusqu'au-delà du mur ; hors de ce volume, le côté de son plan médian indique magasin ou terrasse.
- Les portes ne bougent jamais tant que le joueur est dans leur zone de débattement ; un message lui demande de s'écarter. Le menu pause propose « Revenir au magasin » dès qu'une terrasse est ouverte.
- Les portes s'ouvrent vers le magasin : charnières sur les coins avant extérieurs du rayon, rotation ±90° autour de l'axe vertical, passage libre de 1,8 m. L'animation est pilotée par le code, jamais par un clip Blender.
- Axes : Blender (x, y, z) → glTF (x, z, -y). Le nord du magasin (Blender +Y) est le -Z glTF.
- Le contrat de nommage vit dans `src/core/assetContract.ts` ; `tests/assets.test.ts` le vérifie sur chaque GLB exporté.

## Terrasse et révélation

- Terrasse à 24 m au-dessus du sol, hangar proche et bas : depuis le garde-corps, le mur avant masque peu l'intérieur une fois le toit retiré.
- Intérieur du hangar volontairement neutre (plateformes, bande de collecte) tant que le système d'élevage n'est pas choisi ; un cartel « Contenu provisoire » le signale.
- Toit : levée de 4 m et fondu en 3 s ; fondu seul en mode « Réduire les mouvements ». Le toit ne se referme qu'au déchargement du module.
- Cadrage facultatif vers le hangar à l'entrée en `REVEAL`, interrompu par tout mouvement de souris, désactivé en mode réduit.
- Lumière : mélange amorti (≈ 1 s) entre éclairage magasin et extérieur (soleil rasant, ciel brumeux, ombres à l'échelle des bâtiments), piloté par la position du joueur et l'ouverture des portes.

## Sortie et fin de visite

- Le parvis fait partie de `store.glb` (petit, contigu à l'entrée). Portes automatiques : les deux vantaux coulissent dans le mur dès que le joueur approche (0,8 m avant `TRIGGER_EXIT` côté magasin, 3 m côté parvis) et se referment quand plus personne n'est près, jamais sur le joueur. Elles ne s'ouvrent qu'en `STORE` ou `EXIT` (pas pendant la visite d'un rayon). Franchir le seuil déclenche la sortie ; revenir dans le magasin l'annule ; l'arrivée sur le parvis ouvre le menu de fin.
- Les bénévoles sont des figures stylisées, immobiles, sur le côté du passage ; aucun ne bloque la sortie. Tracts et stand sans texte ni logo.
- Menu de fin : liens uniquement vers `l214.com` en HTTPS, ouverts dans un nouvel onglet sur clic explicite ; une adresse inconnue reste `null` et s'affiche « lien à confirmer ». « Terminer la visite » ne demande rien.

## Erreurs

- Toute erreur d'exécution pendant une filière déclenche le retour sûr ; au magasin, elle est journalisée une seule fois par message. Échec du chargement du magasin : bouton « Réessayer ». Perte du contexte WebGL : pause et message.

## Accessibilité (complément)

- `I` ouvre le détail du cartel affiché (texte long, portée, source ou « à compléter ») et fige le temps de jeu pendant la lecture.
- Chaque son a un sous-titre descriptif (activé par défaut) ; volume 0 = mode sans audio. Qualité réduite : pixel ratio 1, sans ombres.

## Assets, compression et son (étape 6)

- Les assets restent générés par script : c'est une passe artistique de blockout (toits à deux pans, silos, ventilations, quais, camions, champs, haies, collines ; caisses, rails de prix, têtes de gondole au magasin), pas des assets validés. L'intérieur du hangar reste neutre tant que le système d'élevage n'est pas choisi. Un `.blend` retouché par un artiste remplace le blockout sans toucher au code, tant que le contrat de nommage est respecté.
- Export brut dans `blender/out/` (hors dépôt), puis `scripts/optimize-glb.mjs` vers `public/assets/`. KTX2 conditionné à KTX-Software.
- Son entièrement synthétisé (aucun enregistrement à licencier) : ventilation et nappe musicale au magasin, nappe atténuée et grondement grave après le scan, vent sur la terrasse et le parvis, moteurs spatialisés sur chaque objet `TRUCK_*` en mouvement. Aucun son animal. Contexte audio suspendu pendant la pause.

## Lot 1 : magasin détaillé

- Géométrie procédurale enrichie : gondoles par catégorie générique (Épicerie, Petit-déjeuner, Boissons, Hygiène), produits aux silhouettes variées (boîtes, sachets, briques, bouteilles, bocaux, canettes, pots) avec bandes de couleur et étiquettes vierges, vitrines réfrigérées à portes vitrées, faux plafond, gaines, caisses détaillées, chariots et paniers, encadrement d'entrée, plinthes et bandeau.
- Rayon œufs vedette : boîtes à couvercle nervuré et pastille vierge, deux boîtes ouvertes par vantail à hauteur des yeux (œufs bruns et crème), rail de prix, bandeau lumineux, charnières visibles, pictogramme `PICTO_SCAN_<FILIÈRE>` (contrat).
- Chanfreins par modificateur Bevel (arêtes > 50°), appliqués à l'export ; pas de chanfrein sur les marchandises (invisibles à distance de rayon, coûteux en triangles).
- Occlusion ambiante bakée par Cycles dans une couleur de sommet (`AO`, par point, exportée en `COLOR_0`, quantifiée sur 8 bits), adoucie à 75 %. Les objets marqués `ao_skip` (vitres, luminaires, joints de sol, ossature du plafond) n'y participent pas.
- Sols, plafond et faces intérieures des murs maillés en grille (environ 0,4–0,5 m) pour que l'occlusion par sommet montre les ombres de contact.
- Faces jamais visibles des marchandises (dessous, dos côté panneau central) supprimées.
- Les enseignes d'allées `AISLE_SIGN_*` portent leur libellé en extra glTF (`label`) ; le texte est dessiné à l'exécution, des deux côtés.

## Lot 2 : hangar, logistique et terrasse

- Hangar : portiques, arbalétriers, pannes et faîtage sous le toit (visibles après la révélation), soubassement béton, bardage nervuré, ventilateurs à grille, salle des œufs avec porte sectionnelle et auvent de quai, silos détaillés (échelles, trappes, cônes de vidange, conduites d'alimentation). L'intérieur reste neutre ; aucune poule.
- `ROOF_EGGS` est exclu du bake d'occlusion : retiré à la révélation, il ne doit pas assombrir ce qu'il couvrait.
- Unités de la timeline : palettes (caisses ajourées sur palette, cartons filmés et cerclés) au lieu de blocs. Camions détaillés sans marque (cabine, vitrages, rétroviseurs, feux, essieux tandem, plateau à ridelles). Centre de conditionnement : portes de quai avec abris et butoirs, chariot élévateur statique.
- Itinéraire de livraison redessiné à l'est des hangars (x = 45), marquages au sol ; plus aucune route ni aucun arbre ne traverse un bâtiment.
- Garde-corps en verre (vue dégagée sur la ferme). Pas de pupitre sur la terrasse : le cartel affiché reste celui du DOM (source accessible), sans copie dans la scène.
- Pas de chanfrein sur les objets vus de loin et nombreux (caisses, bardage) : invisible à plus de 15 m, coûteux en triangles.

## Lot 3 : paysage

- Terrain en grille (cellules de 5 m) : plat sous les bâtiments, les routes et le socle du magasin (fondu sur 25 m), relief doux qui s'accentue vers l'horizon (bruit de Perlin, uniquement en surélévation), et plateau derrière le magasin qui porte le parvis (même altitude que le sol du parvis) : le magasin domine la plaine depuis une butte.
- Mosaïque de champs par matériau de face sur un treillis de 45 × 55 m (prairie, blé, labour, culture, jachère), cour engravillonnée autour des zones plates.
- Routes avec accotements gravillonnés et lignes de rive continues ; l'itinéraire de livraison se termine devant le socle du magasin, sous la terrasse, donc visible.
- Haies en ellipsoïdes sur certaines limites de champs, arbres de trois essences (feuillus, conifères, peupliers en alignement), bosquets mêlés ; tout est déterministe.
- Clôture d'enceinte de la ferme, loin des bâtiments, ouverte sur le chemin du camion : rien ne doit évoquer un parcours extérieur tant que le système d'élevage n'est pas choisi.
- Ligne électrique sur poteaux bois, traverses, isolateurs et trois conducteurs en chaînette, du centre de conditionnement à la ferme.

## Lot 4 : parvis

- Façade sud : soubassement, panneaux à joints, vitrines teintées à meneaux, acrotère sur tout le pourtour du toit. Enseigne `STORE_SIGN` au mot générique « Supermarché » (extra glTF `label`, dessiné à l'exécution) : aucune marque, aucun logo.
- Marquise d'entrée en porte-à-faux sur deux poteaux, éclairage chaud en sous-face ; pavage en grille fine (ombres de contact) avec joints ; bancs à lattes, arceaux vélos, corbeilles ; jardinières plantées, arbres du paysage.
- Bénévoles : figures stylisées sans traits du visage, posture calme, tract vierge à la main, carnations, coiffures et vêtements variés, sacoche ou chignon pour les distinguer ; tous à l'écart du passage. Stand à jupe unie, piles de tracts et kakémono vierges.
- Le passage de l'entrée au déclencheur du parvis reste dégagé (vérifié en jeu).

## Scanner tenu en main

- Le point de visée est remplacé par une main droite stylisée tenant un terminal d'inventaire rectangulaire (`scanner_hand.glb`, contrat `SCANNER_CONTRACT`) : un outil de magasin tenu comme un téléphone, pas un pistolet (DA §05 : non militarisé).
- Rendu en seconde passe par-dessus la scène (profondeur effacée) : l'outil ne traverse jamais les rayons ni les murs. Caméra dédiée à 50°, éclairage propre, sans brouillard.
- L'écran du terminal affiche « Prêt / Visez un rayon », puis le nom du rayon visé, « Maintenir pour scanner » et la progression, puis « Scanné ». La fenêtre de scan s'allume pendant la visée, un trait discret la relie au centre de la vue.
- Repères de visée sans point central : contour du rayon visé, invite texte (accessible) et écran du terminal.
- L'outil est levé au magasin (`STORE`, `SCANNING`, `OPENING`), baissé sur la terrasse et à la sortie, masqué sous les dialogues ; levée et descente instantanées en mode « Réduire les mouvements ».

## Entrées

- Touches lues via `KeyboardEvent.code` : ZQSD (AZERTY) et WASD (QWERTY) correspondent aux mêmes codes physiques.
- `←` / `→` tournent la vue (environ 100° par seconde) ; `↑` / `↓` avancent et reculent ; `Q`/`D` (`A`/`D`) restent des pas de côté. C'est l'alternative clavier à la souris prévue par GDD.md §04.
- `E` est contextuel : scanner si une cible est visée, sinon interagir.

## Nommage du code

- `src/app/store.ts` devient `src/app/session.ts` (« store » désigne le magasin, `StoreWorld`).

## Outillage

- TypeScript 6 : typescript-eslint ne prend pas encore TS 7 en charge.
