# Mesures de performance — prototype rayon œufs

Budgets de référence : TECH.md §07 (60 fps visés, p95 < 25 ms, 30 fps stables sur matériel modeste). Ces chiffres sont des cibles, pas des garanties.

## Comment mesurer

- Lancer `pnpm dev`, ouvrir `http://localhost:5173/?perf`, ou appuyer sur la touche à gauche de `1` (`²` en AZERTY, `` ` `` en QWERTY).
- L'encart affiche : fps moyen et p95 du temps d'image (fenêtre glissante de 300 images), draw calls, triangles, géométries, textures, tas JS (Chrome uniquement), temps de chargement de chaque GLB.
- Mesurer sur la fenêtre visible et au premier plan : un onglet masqué ne produit pas d'images.

## Relevé du 2026-10-18, après l'étape 6 (Chrome, macOS, fenêtre 858 × 1072, devicePixelRatio 2)

Compteurs de rendu, relevés par image dans le navigateur intégré. Ils ne dépendent pas du matériel. Entre parenthèses, les valeurs de l'étape 5, avant la passe artistique.

| Vue | Draw calls | Triangles |
| --- | ---: | ---: |
| Magasin, vue de départ (allée centrale) | 54 (41) | 20 642 (16 514) |
| Magasin, le long des gondoles | 20 (15) | 8 484 (6 852) |
| Terrasse, chaîne en cours, regard sur le hangar | 74 (36) | 13 146 (1 044) |
| Parvis, vue vers l'extérieur | 14 (13) | 2 772 (2 580) |

| Ressource | Export Blender | Optimisé (servi) | Chargement local |
| --- | ---: | ---: | ---: |
| `store.glb` | 1 179 Ko | 246 Ko | 10 ms |
| `terrace_eggs.glb` | 434 Ko | 200 Ko | 15 ms |

| Autre | Valeur |
| --- | --- |
| Bundle JS de production | 768 Ko (209 Ko gzip), dont three.js, le décodeur meshopt et KTX2Loader |
| Tas JS après une visite | 23 Mo |
| Programmes de shaders | 7 |

Le module de terrasse est préchargé dès que le joueur vise le rayon : les portes s'ouvrent sans attente réseau perceptible.

## Non mesuré

- **fps et p95 réels** : la session de développement tournait dans un onglet en arrière-plan, sans `requestAnimationFrame`. À relever sur les machines cibles (Chrome, Firefox, Safari desktop) avec l'encart `?perf`, en parcourant magasin, terrasse pendant la chaîne et parvis.
- Matériel modeste et mobile : non testé (décision mobile reportée, TECH.md §07).

## Pistes si un budget est dépassé

- Qualité graphique réduite (menu pause) : pixel ratio 1, ombres du soleil coupées.
- Les GLB passent par `scripts/optimize-glb.mjs` : dedup, prune (empties conservés), weld, reorder, compression meshopt par filtres. Pas de quantification : elle déplacerait des échelles dans les transforms de nœuds, dont dépendent pivots et contrat.
- Textures définitives en KTX2 : installer KTX-Software (`toktx`) ; le script signale les textures restées non compressées. Le runtime sait déjà les lire (`KTX2Loader`, transcodeur copié dans `public/basis/`).
- Ne pas basculer `renderer.shadowMap.autoUpdate` à la volée : avec three r186, les matériaux compilés ensuite perdent leurs uniforms de brouillard (scène noyée dans la brume).
