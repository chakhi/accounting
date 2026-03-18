Rapprochement Partiel Automatique
================================

Vue d'ensemble
--------------

Ce module etend le flux de rapprochement automatique d'Odoo en ajoutant un
assistant de rapprochement partiel avec allocation manuelle.

Au lieu de laisser Odoo rapprocher automatiquement toutes les ecritures
correspondantes, l'utilisateur peut :

* selectionner une ecriture de paiement ou une ecriture client/fournisseur
  ouverte,
* choisir plusieurs ecritures de contrepartie,
* definir le montant a affecter a chaque ecriture,
* valider le rapprochement tout en laissant le solde restant ouvert.

Ce module est utile lorsqu'un paiement doit etre reparti manuellement sur
plusieurs factures, avoirs ou ecritures comptables ouvertes.

Cas d'usage principal
---------------------

Utilisez ce module lorsque le rapprochement automatique standard est trop
rigide et que vous devez controler precisement le montant rapproche pour chaque
ecriture ouverte.

Exemples typiques :

* un paiement client doit etre reparti sur plusieurs factures,
* un paiement fournisseur ne couvre qu'une partie d'une ou plusieurs factures,
* un paiement doit etre rapproche manuellement sans solder completement les
  ecritures ouvertes.

Fonctionnement
--------------

Le module ajoute une nouvelle option nommee ``Rapprochement partiel`` sur
l'assistant standard ``account.auto.reconcile.wizard``.

Lorsque cette option est activee et que l'utilisateur lance le rapprochement,
Odoo ouvre une fenetre dediee permettant de :

* choisir l'ecriture de paiement a repartir,
* visualiser le residuel du paiement,
* ajouter des lignes d'allocation avec une ecriture cible et un montant,
* suivre en temps reel le total alloue et le montant restant,
* confirmer le rapprochement.

L'assistant ne propose que des ecritures de contrepartie valides selon
l'ecriture de paiement selectionnee :

* meme societe,
* meme compte,
* ecritures comptables comptabilisees et non rapprochees,
* signe oppose,
* meme partenaire lorsque l'ecriture de paiement contient un partenaire.

Workflow utilisateur
--------------------

1. Ouvrir l'assistant standard de rapprochement dans la comptabilite.
2. Activer ``Rapprochement partiel``.
3. Cliquer sur le bouton qui lance le rapprochement.
4. Dans l'assistant de rapprochement partiel, selectionner l'ecriture de
   paiement.
5. Ajouter une ou plusieurs lignes d'allocation.
6. Pour chaque ligne, choisir l'ecriture comptable a rapprocher et saisir le
   montant.
7. Cliquer sur ``Rapprocher``.

Apres validation :

* les rapprochements partiels sont crees pour les montants saisis,
* un rapprochement complet est cree automatiquement lorsqu'un groupe rapproche
  devient totalement solde,
* tout residuel non alloue reste ouvert pour un rapprochement ulterieur.

Regles de validation
--------------------

L'assistant empeche les allocations incoherentes. En particulier :

* au moins une ligne d'allocation est obligatoire,
* les montants alloues doivent etre strictement positifs,
* le total alloue ne peut pas depasser le residuel du paiement,
* une meme ecriture de contrepartie ne peut etre ajoutee qu'une seule fois,
* le montant d'allocation ne peut pas depasser le montant encore ouvert de la
  ligne cible,
* l'ecriture de paiement et les ecritures de contrepartie doivent appartenir a
  la meme societe, au meme compte et avoir des signes opposes.

Notes techniques
----------------

* Modele etendu : ``account.auto.reconcile.wizard``
* Nouvel assistant : ``account.auto.partial.reconcile.wizard``
* Nouveau modele de ligne : ``account.auto.partial.reconcile.wizard.line``
* Dependance : ``account_accountant``

La logique de rapprochement prend egalement en charge les mecanismes standard
d'Odoo pour les ecarts de change et la comptabilite de caisse lorsque cela
s'applique.

Rapprochement Partiel Automatique
================================

Overview
--------

This module extends Odoo's automatic reconciliation workflow by adding a
manual partial reconciliation assistant.

Instead of letting Odoo reconcile all matching journal items automatically,
the user can:

* select one payment or open receivable/payable journal item,
* choose several counterpart journal items,
* define the amount to allocate to each item,
* validate the reconciliation while keeping any remaining balance open.

This is useful when one payment must be distributed manually across multiple
invoices, credit notes, or open accounting entries.

Main use case
-------------

Use this module when the standard auto-reconcile process is too rigid and you
need to control exactly how much of a payment is matched against each open
entry.

Typical examples:

* one customer payment must be split across several invoices,
* one supplier payment only covers part of one or more bills,
* a payment must be matched manually because the open amounts should not be
  reconciled in full.

How it works
------------

The module adds a new option named ``Rapprochement partiel`` on the standard
``account.auto.reconcile.wizard``.

When this option is enabled and the user launches auto reconciliation, Odoo
opens a dedicated popup where the user can:

* choose the payment journal item to allocate,
* see the payment residual amount,
* add allocation lines with a target journal item and an amount,
* track the total allocated amount and the remaining amount in real time,
* confirm the reconciliation.

The assistant only proposes valid counterpart lines based on the selected
payment line:

* same company,
* same account,
* posted and unreconciled journal items,
* opposite sign,
* same partner when the payment line has a partner.

User workflow
-------------

1. Open the standard reconciliation assistant in Accounting.
2. Enable ``Rapprochement partiel``.
3. Click the button that launches reconciliation.
4. In the partial reconciliation wizard, select the payment journal item.
5. Add one or more allocation lines.
6. For each line, choose the journal item to reconcile and enter the amount.
7. Click ``Rapprocher``.

After validation:

* partial reconciliations are created for the entered amounts,
* full reconciliation is created automatically when a matched group becomes
  fully settled,
* any unallocated residual amount remains open for later reconciliation.

Validation rules
----------------

The wizard prevents inconsistent allocations. In particular:

* at least one allocation line is required,
* allocated amounts must be strictly positive,
* the total allocated amount cannot exceed the payment residual,
* each counterpart journal item can only be added once,
* each allocation amount cannot exceed the currently open amount of the target
  line,
* payment and counterpart lines must belong to the same company and account and
  must carry opposite signs.

Technical notes
---------------

* Model extended: ``account.auto.reconcile.wizard``
* New wizard: ``account.auto.partial.reconcile.wizard``
* New wizard line model: ``account.auto.partial.reconcile.wizard.line``
* Dependency: ``account_accountant``

The reconciliation logic also supports Odoo's standard exchange difference and
cash basis reconciliation mechanisms when applicable.
