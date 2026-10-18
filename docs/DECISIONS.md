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
| STORE | EXIT | porte d'entrée principale |
| EXIT | END_MENU | arrivée sur le parvis |
| END_MENU | STORE | « Revenir dans le magasin » |
| tout état | ERROR | échec de chargement ou état incohérent |
| ERROR | SAFE_RETURN → STORE | message affiché, joueur replacé au magasin |

- La pause est un drapeau orthogonal, pas un état. Elle se déclenche par `Échap` (perte du verrouillage du pointeur), `P` ou l'onglet masqué ; l'horloge de jeu s'arrête et reprend sans saut.
- Un rayon est marqué « exploré » quand sa chaîne atteint `RECAP` ; un retour anticipé ne le marque pas.
- Si le navigateur refuse le verrouillage du pointeur, la vue se pilote en glisser-déposer à la souris.
- Le toit relève de l'état `REVEAL` ; la timeline commence après. `revealRoof` n'est pas un événement de timeline.

## Contrats de données

- `TimelineStep.event` : `"collect" | "load" | "drive" | "process" | "deliver"`, avec `targets?: string[]` et `pathId?: string`.
- `ChainConfig.exitAnchor` est renommé `returnAnchor`. Champs ajoutés : `systemType`, `recap` (3 cartels max), `validation`.
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
- Les portes s'ouvrent vers le magasin : charnières sur les coins avant extérieurs du rayon, rotation ±90° autour de l'axe vertical, passage libre de 1,8 m. L'animation est pilotée par le code, jamais par un clip Blender.
- Axes : Blender (x, y, z) → glTF (x, z, -y). Le nord du magasin (Blender +Y) est le -Z glTF.
- Le contrat de nommage vit dans `src/core/assetContract.ts` ; `tests/assets.test.ts` le vérifie sur chaque GLB exporté.

## Entrées

- Touches lues via `KeyboardEvent.code` : ZQSD (AZERTY) et WASD (QWERTY) correspondent aux mêmes codes physiques.
- `E` est contextuel : scanner si une cible est visée, sinon interagir.

## Nommage du code

- `src/app/store.ts` devient `src/app/session.ts` (« store » désigne le magasin, `StoreWorld`).

## Outillage

- TypeScript 6 : typescript-eslint ne prend pas encore TS 7 en charge.
