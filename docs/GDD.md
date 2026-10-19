# DERRIÈRE LE RAYON

**DOCUMENT 02 — GAME DESIGN DOCUMENT**

Systèmes, parcours, narration, scénarios de rayons et critères de validation.

*Statut : proposition de production — non validée par L214.*

Périmètre commun : supermarché FPS → scan d’un rayon → ouverture double → terrasse en hauteur → exploitation → transport → transformation/abattage suggérés → retour au magasin → sortie et ressources L214.

## 01 — Vision produit et objectifs

Expérience web à la première personne, courte et réexplorable. Promesse : « Scanner un rayon pour voir le parcours caché derrière le produit ». Le joueur est un témoin actif et dispose toujours de la liberté de revenir au magasin.

- Objectif pédagogique : comprendre qu’une filière comporte plusieurs étapes et que ces étapes diffèrent selon les produits.
- Objectif émotionnel : provoquer une prise de conscience sans images graphiques et sans effet de peur.
- Objectif d’action : ouvrir une suite volontaire vers des informations sourcées et des possibilités d’engagement auprès de L214.
- Mesures de réussite envisagées : compréhension des étapes au test utilisateur, taux de rayon terminé, possibilité de retour, taux d’accès volontaire aux ressources ; suivi respectueux de la vie privée.
## 02 — Périmètre et hypothèses

| Lot | Inclus | Hors périmètre initial |
| --- | --- | --- |
| Prototype | magasin compact, rayons œufs et viande bovine, terrasses, filières et retour, sortie L214 | monde ouvert massif |
| Extension | volaille, porc, poisson avec scénarios distincts | multijoueur, moteur physique avancé |
| Production | sourcing et validation de contenus, accessibilité, optimisation | prétention à représenter toutes les exploitations |

Durée indicative : 5 à 8 minutes pour un premier rayon, à mesurer en tests ; navigation non chronométrée. Ordre de visite libre. La sortie peut être proposée à tout moment, avec un récapitulatif adapté aux rayons réellement consultés.

## 03 — Parcours principal joueur

1. Accueil : intention, commandes, option réduire les mouvements, avertissement sur l’évocation de l’exploitation animale et choix de lancer l’expérience.
2. Magasin : marche, observation, scanner tenu en main, rayons identifiables.
3. Ciblage : activation du scan sur un rayon disponible ; feedback explicite.
4. Ouverture : le rayon se sépare en deux portes ; zone de passage sécurisée.
5. Terrasse : le joueur franchit le seuil, peut s’avancer jusqu’au garde-corps, lire une première contextualisation.
6. Révélation : le toit du bâtiment est retiré ; apparaît l’organisation intérieure.
7. Chronologie animée : production/élevage, chargement éventuel, transport, installation aval, transformation/conditionnement, transport des produits au magasin.
8. Compréhension : synthèse courte, sources consultables, bouton « Revoir » et retour libre.
9. Retour : franchissement du seuil ; portes se referment en sécurité après sortie ; nouveau rayon disponible.
10. Sortie principale : parvis avec militants représentés respectueusement, distribution de tracts, menu L214 sans obligation de cliquer.
## 04 — Contrôles et règles de caméra

| Action | Ordinateur | Alternative |
| --- | --- | --- |
| Déplacer | ZQSD / WASD | flèches / mode guidé |
| Regarder | souris | clavier / contrôle accessible à définir |
| Scanner | clic maintenu ou E | bouton explicite |
| Interagir / lire | E ou clic sur UI | focus clavier |
| Pause / pointeur | Échap | bouton pause |

Le déplacement est libre dans le magasin et sur la terrasse, mais la terrasse possède des limites de collision. Les éléments lointains de la filière s’observent depuis le point de vue principal ; la caméra n’est pas téléportée brusquement vers l’abattoir.

## 05 — Machine à états et garde-fous

| État | Déclencheur | Sortie |
| --- | --- | --- |
| STORE | entrée ou retour | SCAN |
| SCAN | cible + validation | OPENING |
| OPENING | animation portes terminée | TERRACE |
| TERRACE | joueur atteint la zone observatoire | REVEAL |
| REVEAL | toit animé | CHAIN |
| CHAIN | timeline / narration | RECAP |
| RECAP | revoir / revenir | CHAIN ou RETURN |
| RETURN | joueur refranchit seuil | STORE |
| EXIT | porte d’entrée principale | END_MENU |

- Invariant : un seul rayon actif ; pas de second scan en cours d’ouverture.
- Invariant : animation du toit et séquence de transport rejouables sans créer de duplications.
- Invariant : le retour au magasin fonctionne depuis terrasse, révélation et récapitulatif.
- Invariant : l’ouverture/fermeture ne peut pas emprisonner le joueur ; possibilité de rétablir l’état sûr.
- Invariant : le chargement d’un GLB peut échouer sans bloquer la session : affichage de message et retour au magasin.
## 06 — Script détaillé : rayon œufs / prototype

### 0 — Avant le scan

Signalétique « Œufs ». Un petit pictogramme indique que le rayon est analysable. Le joueur vise, un contour fin parcourt les deux moitiés du meuble.

### 1 — Ouverture / 0–5 s (indicatif)

Le meuble s’ouvre en deux vantaux autour des pivots latéraux. Un environnement extérieur apparaît ; caméra inchangée, éclairage exposé progressivement.

### 2 — Terrasse / exploration libre

Le joueur s’avance sur la terrasse. Un hangar est visible au premier plan, avec une route et un centre de conditionnement plus loin.

### 3 — Coupe du bâtiment / 3–5 s

Le toit s’élève ou devient transparent ; les éléments d’une installation représentative, explicitement documentée, deviennent visibles. Court message expliquant le système précis représenté (cages, sol ou plein air, selon la filière choisie).

### 4 — Chaîne / 30–60 s modulables

Les œufs sont collectés, transportés vers un centre de tri et de conditionnement, puis chargés en camion vers le magasin. Après ce parcours, un changement d’échelle temporelle signale la fin de la période de ponte : les poules sont chargées puis transportées vers un abattoir hors champ. Cette séquence reste distincte du transport des œufs (docs/DECISIONS.md).

### 5 — Synthèse / libre

Trois cartels au maximum : conditions du système représenté, étape de collecte/conditionnement, distinction entre cas étudié et toute la filière. Lien « Voir les sources » accessible au clavier.

### 6 — Retour / libre

Le joueur retourne par la terrasse. Les portes se referment après son passage. Le rayon porte un marqueur « exploré » non intrusif.

## 07 — Variantes narratives par rayon

| Rayon | Parcours représenté | Point de vigilance |
| --- | --- | --- |
| Viande bovine | engraissement en bâtiment → transport vivant → attente et amenée à l’abattoir → mise à mort hors champ → réfrigération → découpe/conditionnement → livraison | un système d’engraissement ne représente ni toute la vie du bovin ni toute la viande rouge |
| Poulet | élevage → camion d’animaux → abattoir suggéré → distribution | âge et pratiques selon filière/source |
| Porc | élevage → transport vivant → abattage non explicite → découpe → distribution | séparer exploitation type et règles générales |
| Poisson élevé | aquaculture → récolte/transport → transformation → magasin | espèce et modalité d’abattage spécifiques |
| Œufs | élevage de pondeuses → collecte → tri/conditionnement → distribution | éviter de confondre œuf et viande |

Chaque filière doit posséder une fiche de validation : territoire, espèce, type de système, provenance des données, scènes non représentatives signalées et sources consultables.

La filière bovine représente un engraissement en bâtiment, sans reproduire un site réel ni attribuer une densité aux effectifs visibles. Les bovins marchent dans les couloirs et sur les rampes ; le camion d’animaux et le camion frigorifique ont des chargements distincts. Le toit révèle l’élevage et les espaces d’attente, tandis que la zone de mise à mort reste opaque. Les cartels nomment l’étourdissement et la saignée sans les montrer. Le joueur observe depuis la terrasse et conserve le retour libre.

Les affirmations et leurs sources figurent dans [la configuration bovine](../src/data/chains/beef.ts). Elles attendent la validation éditoriale. Le récapitulatif propose aussi le parcours complet en texte, consultable sans animation.

## 08 — Interface pédagogique et contenu

- Cartels sur événements, chacun limité à une idée principale et environ 140 caractères dans la vue immersive ; texte détaillé dans un panneau à la demande.
- Différencier « illustration schématique » de « chiffre vérifié » ; dater et sourcer chaque chiffre.
- Éviter les généralisations (« tous les animaux... ») ; contextualiser par pays, filière et période.
- Récapitulatif d’un rayon : ce que le joueur a observé, ce qu’il faut retenir, lien vers des sources.
- Aucune progression forcée par lecture exhaustive ; possibilité de mettre en pause les animations.
## 09 — Sortie et fin de session

À la porte d’entrée, le joueur peut quitter même sans avoir scanné tous les rayons. Sur le parvis : quelques bénévoles au ton calme distribuent des tracts fictifs. Aucun personnage ne bloque physiquement la sortie.

- Menu proposé : « Découvrir L214 », « Lire les enquêtes », « Agir », « Faire un don », « Revenir dans le magasin ».
- Liens officiels à vérifier lors de l’intégration ; ouverture externe explicite et sans redirection automatique.
- Ne pas utiliser le logo officiel ou présenter le projet comme une campagne validée sans accord de l’association. Tracts et banderole du parvis portent un mot-symbole de substitution jusqu’à la remise du fichier validé (docs/DECISIONS.md).
- L’utilisateur peut fermer le menu et terminer sans contribution.
### Mesures qualité / tests

Tester la compréhension avec questions neutres (« Que devient le produit après cette étape ? »), mesurer abandon lors des transitions, vérifier que l’expérience est accessible sans audio et qu’aucune scène ne produit de malaise de caméra.

## 10 — Backlog priorisé et critères d’acceptation

| Priorité | Story | Acceptation |
| --- | --- | --- |
| P0 | Déplacement FPS | collisions et pause fonctionnent |
| P0 | Scanner rayon œufs | rayon activé une seule fois par interaction |
| P0 | Portes doubles | ouverture sûre, passage possible, retour possible |
| P0 | Terrasse + coupe | toit se retire sans collision ni artefact majeur |
| P0 | Timeline filière œufs | séquence cohérente, pause/replay, sans faux abattoir |
| P0 | Retour supermarché | état de rayon mémorisé, aucune duplication |
| P1 | Sortie et menu L214 | liens explicites, bouton fermeture |
| P1 | Sources et sous-titres | accessibles au clavier |
| P2 | Autres filières | mêmes interfaces mais timelines propres |

Définition de terminé : scénario jouable du début à la fin, scènes documentées, tests de retour/erreur, mode réduit de mouvement, navigateur desktop cible validé.
