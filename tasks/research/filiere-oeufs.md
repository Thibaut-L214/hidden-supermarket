# Filière œufs — vérification factuelle

Date de vérification : 19 octobre 2026.

## Objet et périmètre

Cette note vérifie les affirmations visibles dans [`src/data/chains/eggs.ts`](../../src/data/chains/eggs.ts). Elle couvre un élevage français de poules pondeuses en cages aménagées et le circuit d'œufs coquille destinés à un magasin. Elle ne décrit pas les œufs destinés à l'industrie ni tous les circuits courts.

Avant cette vérification, le fichier ne contenait aucun chiffre. Il comptait quatre textes marqués `TODO_SOURCE`, tous les cartels restaient au statut `draft`, et la liste `sources` était vide. Selon les règles du projet, ce contenu ne pouvait pas être publié en l'état ([schéma éditorial](../../docs/CONTENT_SCHEMA.md)).

## Conclusion

Le parcours « élevage → centre d'emballage → magasin » convient à un cas français d'œufs coquille vendus en magasin. En 2025, l'administration française exige le classement par un centre d'emballage pour tout producteur qui fournit un commerce de détail, même s'il détient au plus 250 poules. Ce centre peut toutefois être attenant à l'élevage : le transport routier entre les deux sites n'est pas systématique ([ministère de l'Agriculture, instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 2 à 4](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement)).

Le choix des cages reste factuel s'il désigne un cas, pas le système majoritaire. En France, 28 % des œufs de consommation produits en 2024 provenaient d'élevages en cage, contre 72 % d'élevages au sol, en plein air ou biologiques. Agreste obtient ces valeurs avec un modèle statistique : ce ne sont pas des comptages exhaustifs ([Agreste, *Graph'Agri 2025*, données 2024, chapitre « Aviculture — œufs »](https://agreste.agriculture.gouv.fr/agreste-web/download/publication/publie/GraFra2025Integral/GraphAgri2025_accessible.pdf)).

La scène ne doit pas appeler ces installations de simples « cages ». Depuis le 1er janvier 2012, l'Union européenne interdit les cages non aménagées. Une cage autorisée doit offrir au moins 750 cm² par poule, dont 600 cm² utilisables, un nid, une litière permettant le picotage et le grattage, et 15 cm de perchoir par poule ([directive 1999/74/CE, version consolidée au 14 décembre 2019, articles 5 et 6](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:01999L0074-20191214)). En France, la loi interdit aussi la mise en production d'un bâtiment nouveau ou réaménagé destiné aux pondeuses en cages depuis le 2 novembre 2018, sans fermer les bâtiments existants ([Code rural, article L. 214-11, version en vigueur depuis le 2 novembre 2018](https://www.legifrance.gouv.fr/codes/article_lc/LEGIARTI000037556890)).

## Mise en œuvre retenue

La configuration corrigée suit d'abord les œufs jusqu'au magasin, puis ouvre une séquence distincte de fin de ponte. Elle nomme les cages « aménagées », précise que la vue 3D ne montre pas tous leurs équipements, limite le camion vers le centre d'emballage au cas représenté et indique que les poules partent vers un abattoir hors champ. Ce dernier choix décrit le scénario montré ; l'avis de l'EFSA établit ce trajet, mais ne mesure pas sa part parmi toutes les destinations.

Les cartels séparent les périmètres : minima réglementaires européens, statistique française de 2024 et avis scientifique de 2022. Chaque affirmation chiffrée pointe vers une source primaire. Le statut `review` maintient la validation éditoriale L214 comme étape distincte.

## Audit des textes initiaux

### 1. Système d'élevage

**Texte initial :** « Poules pondeuses en cages » et « cages superposées ».

**Ce qui tient :** les cages aménagées existaient encore en France en 2024 et produisaient 28 % des œufs de consommation ([Agreste, *Graph'Agri 2025*, données 2024](https://agreste.agriculture.gouv.fr/agreste-web/download/publication/publie/GraFra2025Integral/GraphAgri2025_accessible.pdf)). La réglementation européenne autorise encore les cages aménagées au 19 octobre 2026 ; la Commission annonçait une proposition de suppression progressive pour la fin de 2026, pas une interdiction déjà applicable ([Commission européenne, calendrier de révision consulté le 19 octobre 2026](https://food.ec.europa.eu/animals/animal-welfare/evaluations-and-impact-assessment/revision-eu-animal-welfare-legislation_en)).

**Ce qui doit changer :** « cages » peut être compris comme incluant les cages non aménagées, interdites dans l'UE depuis 2012. Le jeu doit écrire « cages aménagées » et préciser « France, 2024 » pour la part de production ([directive 1999/74/CE, version consolidée au 14 décembre 2019](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:01999L0074-20191214)).

**Limite visuelle :** le générateur 3D crée des planchers, des barreaux et trois niveaux, mais ne crée pas de nid, de litière ni de perchoir ([`battery_cages`](../../blender/scripts/terrace_props.py)). La correction précise donc que la vue schématise les rangées et ne montre pas tous les équipements réglementaires.

### 2. Chargement et départ des poules

**Texte initial :** le jeu charge les poules et fait partir leur camion avant de collecter les œufs.

**Ce qui tient :** les règles françaises de 2025 encadrent le transport routier des volailles, y compris dans des conteneurs ; elles imposent notamment l'aptitude au transport, une aération et une surface adaptées, ainsi que des autorisations au-delà de 65 km ([ministère de l'Agriculture, « La protection des animaux d'élevage pendant le transport », 3 juin 2025](https://agriculture.gouv.fr/la-protection-des-animaux-delevage-pendant-le-transport)). Une instruction sanitaire française de 2025 prévoit aussi l'envoi de lots de poules pondeuses vers un abattoir après des prélèvements valables six à dix semaines selon le système d'élevage ([instruction DGAL/SDEIGIR/2025-477, publiée le 28 août 2025, annexe III](https://info.agriculture.gouv.fr/boagri/instruction-2025-477/telechargement)).

**Ce qui doit changer :** l'ordre actuel peut faire croire que le même lot quitte le bâtiment puis continue à produire les œufs collectés dans la scène suivante. L'Anses indique qu'en France la ponte commence généralement à 18 à 20 semaines et que la durée de vie totale d'une pondeuse est d'environ 80 semaines. Ces valeurs décrivent un ordre de grandeur national, pas chaque lot ([Anses, avis 2023-SA-0053, version finale de mai 2025, p. 21](https://www.anses.fr/sites/default/files/AP-2023-SA-0053RA.pdf)). Le cartel doit annoncer une ellipse temporelle et présenter le chargement comme une séquence de fin de lot, distincte de la collecte courante.

**Limite :** les sources retenues établissent le transport de poules en fin de ponte vers l'abattoir, mais elles ne donnent pas sa part parmi toutes les destinations en 2024 ou 2025. La correction attribue cette destination au cas montré sans la généraliser à tous les lots.

### 3. Collecte et transport des œufs

**Texte initial :** « Les œufs sont rassemblés au bout du bâtiment, puis placés en caisses » et « Un camion emporte les caisses ».

**Ce qui tient :** l'administration française demande aux centres d'emballage de décrire le flux des œufs depuis l'élevage et l'usage d'alvéoles jetables ou nettoyées et désinfectées pour stocker les œufs collectés ([instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 4](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement)). La réglementation européenne exige que l'emballage de transport porte le producteur, son code, la quantité ou le poids, la période de ponte et la date d'expédition ([règlement délégué (UE) 2023/2465, version consolidée au 14 octobre 2024, article 7](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:02023R2465-20241014)).

**Ce qui doit changer :** « caisses » reste compréhensible dans une scène schématique, mais « emballages de transport » ou « alvéoles de transport » correspond mieux aux textes officiels. Le camion vers un site séparé ne représente qu'une organisation possible : un centre d'emballage peut se trouver sur le même site que l'élevage ([instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 2 à 4](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement)).

### 4. Tri et conditionnement

**Texte initial :** « Au centre, les œufs sont triés puis emballés pour la vente ».

**Ce qui tient :** seuls les centres d'emballage agréés peuvent classer, emballer ou remballer les œufs et étiqueter les emballages dans l'UE ([règlement d'exécution (UE) 2023/2466 du 17 août 2023, article 3](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32023R2466)). Pour les œufs de catégorie A, le centre classe par qualité et par poids, marque puis emballe dans les dix jours suivant la ponte ([règlement délégué (UE) 2023/2465, version consolidée au 14 octobre 2024, articles 4 à 6](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:02023R2465-20241014)).

**Ce qui doit changer :** remplacer « triés » par « contrôlés, classés par qualité et poids, marqués puis emballés » si la scène veut expliquer le travail réglementaire du centre. Le délai de dix jours concerne les œufs de catégorie A ; il ne doit pas qualifier tous les œufs.

### 5. Centre d'emballage et magasin

**Texte initial :** « La filière des œufs passe par un centre de conditionnement entre l'élevage et le magasin ».

**Ce qui tient :** pour un producteur français qui livre un commerce de détail en 2025, les œufs coquille doivent être classés par un centre d'emballage, quel que soit l'effectif de pondeuses ([instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 3](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement)).

**Ce qui doit changer :** la phrase généralise à toute la filière et suggère un site intermédiaire distinct. En France, un producteur détenant au plus 250 poules peut vendre toute sa production directement au consommateur sans classement par un centre, sous conditions. Un centre agréé peut aussi être attenant à l'élevage ([instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 2 à 4](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement)). Il faut limiter la phrase au cas montré.

### 6. Livraison

**Texte initial :** « Les boîtes partent en camion vers le magasin, jusqu'au rayon ».

**Verdict :** cette formulation convient comme description de la scène. Elle ne doit pas devenir « tous les œufs sont livrés en camion », car la réglementation française de 2025 reconnaît aussi la vente directe au consommateur pour certains producteurs de 250 poules au plus ([instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 3](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement)).

## Formulations étudiées

Ces textes restent sous 140 caractères pour le champ `short`. Les détails séparent les échelles France et UE.

### `eggs.system`

- **Titre :** `Poules pondeuses en cages aménagées`
- **Short :** `Cette scène montre des cages aménagées. En France, 28 % des œufs produits en 2024 provenaient d'élevages en cage.`
- **Détail :** `Dans l'Union européenne, une cage aménagée doit offrir au moins 750 cm² par poule, dont 600 cm² utilisables, un nid, une litière et 15 cm de perchoir par poule. La scène schématise la disposition des cages ; elle ne montre pas tous ces équipements.`
- **Scope :** `France, production 2024 ; Union européenne, réglementation en vigueur au 19 octobre 2026.`
- **Sources :** [Agreste, données 2024 publiées dans *Graph'Agri 2025*](https://agreste.agriculture.gouv.fr/agreste-web/download/publication/publie/GraFra2025Integral/GraphAgri2025_accessible.pdf) ; [directive 1999/74/CE, version consolidée au 14 décembre 2019](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:01999L0074-20191214).

### `eggs.hens.load`

- **Titre :** `Fin du lot de ponte`
- **Short :** `À la fin d'un lot, des poules sont placées dans des conteneurs puis chargées pour leur transport.`
- **Détail :** `Cette séquence se déroule après la période de ponte. Elle ne précède pas la collecte montrée ensuite : la timeline rapproche deux moments distincts. En France, la ponte commence généralement vers 18 à 20 semaines et la durée de vie totale d'une pondeuse est d'environ 80 semaines ; ces valeurs varient selon les lots.`
- **Scope :** `France, ordre de grandeur publié en mai 2025 ; transport, règles françaises consultées le 19 octobre 2026.`
- **Sources :** [Anses, avis 2023-SA-0053, mai 2025, p. 21](https://www.anses.fr/sites/default/files/AP-2023-SA-0053RA.pdf) ; [ministère de l'Agriculture, transport des animaux, 3 juin 2025](https://agriculture.gouv.fr/la-protection-des-animaux-delevage-pendant-le-transport).

### `eggs.hens.leave`

- **Titre :** `Transport des poules`
- **Short :** `Le camion quitte l'élevage avec les poules. La scène ne montre ni sa destination ni la durée du trajet.`
- **Détail :** `Le transport des poules appartient à la fin du lot de ponte, pas au parcours des œufs. Le jeu ne documente pas ici la destination des animaux.`
- **Scope :** `Cas schématique français ; règles de transport consultées le 19 octobre 2026.`
- **Source :** [ministère de l'Agriculture, transport des animaux, 3 juin 2025](https://agriculture.gouv.fr/la-protection-des-animaux-delevage-pendant-le-transport).

### `eggs.collect`

- **Titre :** `Collecte des œufs`
- **Short :** `Les œufs sont collectés dans le bâtiment puis placés sur des alvéoles de transport.`
- **Détail :** `La scène représente une collecte schématique. Les équipements et la fréquence de collecte varient selon l'exploitation.`
- **Scope :** `France, cas schématique fondé sur les règles applicables aux centres d'emballage en 2025.`
- **Source :** [instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 4](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement).

### `eggs.transport`

- **Titre :** `Vers un centre d'emballage`
- **Short :** `Dans le cas montré, un camion transporte les œufs vers un centre d'emballage agréé.`
- **Détail :** `Le centre peut être séparé de l'élevage ou installé sur le même site. Le camion illustre un circuit possible.`
- **Scope :** `France, circuit vers le commerce de détail, règles 2025.`
- **Source :** [instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 2 à 4](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement).

### `eggs.process`

- **Titre :** `Classement et emballage`
- **Short :** `Le centre contrôle, classe, marque et emballe les œufs de catégorie A pour leur vente.`
- **Détail :** `Les œufs de catégorie A sont classés par qualité et par poids, marqués puis emballés dans les dix jours suivant la ponte.`
- **Scope :** `Union européenne, règles en vigueur au 19 octobre 2026.`
- **Sources :** [règlement d'exécution (UE) 2023/2466, article 3](https://eur-lex.europa.eu/legal-content/FR/TXT/?uri=CELEX:32023R2466) ; [règlement délégué (UE) 2023/2465, version consolidée au 14 octobre 2024, articles 4 à 6](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:02023R2465-20241014).

### `eggs.delivery`

- **Titre :** `Livraison au magasin`
- **Short :** `Dans le cas montré, les œufs emballés sont livrés au magasin puis placés en rayon.`
- **Détail :** `Cette livraison termine le circuit représenté. Elle ne décrit pas la vente directe à la ferme ou sur un marché.`
- **Scope :** `France, circuit schématique vers un commerce de détail, 2025.`
- **Source :** [instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 3](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement).

### `eggs.recap.system`

- **Titre :** `Le système représenté`
- **Short :** `Cette scène montre un élevage français en cages aménagées, qui ne représente pas toute la production.`
- **Détail :** `En 2024, 28 % des œufs de consommation produits en France provenaient d'élevages en cage. Cette part est une estimation statistique.`
- **Scope :** `France, production 2024.`
- **Source :** [Agreste, *Graph'Agri 2025*, données 2024](https://agreste.agriculture.gouv.fr/agreste-web/download/publication/publie/GraFra2025Integral/GraphAgri2025_accessible.pdf).

### `eggs.recap.steps`

- **Titre :** `Le parcours montré`
- **Short :** `Collecte, transport, classement, marquage, emballage et livraison : ce circuit conduit les œufs au magasin.`
- **Détail :** `Dans ce cas français, un centre d'emballage agréé intervient avant la vente en magasin. Il peut être attenant à l'élevage. Le départ des poules forme une séquence distincte de fin de lot.`
- **Scope :** `France, circuit vers un commerce de détail, règles 2025.`
- **Source :** [instruction DGAL/SDSSA/2025-1, version rectifiée du 10 juin 2025, p. 2 à 4](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement).

### `eggs.recap.scope`

- **Titre :** `Un cas, pas toute la filière`
- **Short :** `La scène montre un circuit français vers un magasin. D'autres systèmes d'élevage et circuits de vente existent.`
- **Détail :** `Elle ne représente ni les élevages au sol, en plein air ou biologiques, ni la vente directe, ni les œufs destinés à l'industrie.`
- **Scope :** `France, limites du cas représenté, données et règles 2024-2025.`
- **Sources :** [Agreste, répartition des productions en 2024](https://agreste.agriculture.gouv.fr/agreste-web/download/publication/publie/GraFra2025Integral/GraphAgri2025_accessible.pdf) ; [instruction DGAL/SDSSA/2025-1, circuits de commercialisation, version rectifiée du 10 juin 2025](https://info.agriculture.gouv.fr/boagri/instruction-2025-1/telechargement).

## Chiffres à retenir et limites

| Chiffre | Périmètre | Usage conseillé | Limite |
| --- | --- | --- | --- |
| 28 % des œufs produits en cage | France, œufs de consommation, 2024 | Situer le cas représenté | Estimation issue du modèle SSP-ITAVI-CNPO, pas recensement exhaustif. [Agreste, *Graph'Agri 2025*](https://agreste.agriculture.gouv.fr/agreste-web/download/publication/publie/GraFra2025Integral/GraphAgri2025_accessible.pdf) |
| 750 cm² par poule, dont 600 cm² utilisables | UE, minimum d'une cage aménagée, règle consolidée en 2019 et consultée le 19 octobre 2026 | Expliquer la norme minimale | Ce minimum ne mesure pas l'espace réellement utilisé ni l'état d'un élevage précis. [Directive 1999/74/CE, article 6](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:01999L0074-20191214) |
| Ponte vers 18 à 20 semaines ; vie totale d'environ 80 semaines | France, description publiée en mai 2025 | Situer la fin de lot | Ordres de grandeur, variables selon le lot et la conduite d'élevage. [Anses, avis 2023-SA-0053, p. 21](https://www.anses.fr/sites/default/files/AP-2023-SA-0053RA.pdf) |
| Dix jours après la ponte | UE, classement, marquage et emballage des œufs de catégorie A | Décrire le délai réglementaire | Ne concerne pas toutes les catégories ni tous les débouchés. [Règlement délégué (UE) 2023/2465, article 6](https://eur-lex.europa.eu/legal-content/FR/TXT/PDF/?uri=CELEX:02023R2465-20241014) |

## Conséquence pour le modèle de contenu

Le champ `source` d'un cartel n'accepte qu'une seule référence ([type `Caption`](../../src/features/content/types.ts)). La configuration corrigée conserve ce modèle et sépare la norme européenne de la statistique française dans deux cartels. Une future rédaction qui réunirait plusieurs faits propriétaires dans un même cartel devrait faire évoluer ce champ vers une liste de sources.
