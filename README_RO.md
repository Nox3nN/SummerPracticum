# Library Management System.

- Sistem de tip librarie bazat pe command-lineuri, folosind SQLite pentru Persistent Storage.
- Construit pentru un proiect de vara, completat solo in ~15-16 zile lucratoare.

## Caracteristicile Programului.

- **Login & permissions**: bazat pe email, primul cont creat devine admin.
- **Books**: add, view, search (titlu/autor/categorie), update, delete
- **Users**: inregistrare membri/admini, abilitatea de a vedea toti userii
- **Transactions**: imprumut, returnare, calcul amenda automate pentru incalcarea termenului limita
- **Reports**: istoric tranzactii, abilitatea de a vedea cartile peste terment limita (admin only)
- Validare de date si error handling prin intermediul: dupe ISBN/email, ID-uri invalide, carti curent imprumutate, etc.
- Persistent storage via SQLite — datele raman de la executie la executie

## Cerinte pentru rularea programului.

- Python 3.8+ (se foloseste doar de libraria standard — nu avem nevoie de `pip install`)

## Cum se ruleaza programul?

```bash
python main.py
```

- Prima rulare creaza 'library.db' in fisierul de proiect si arata un menu numerotat. 
- Apoi, se introduce un numar pentru actiunea dorita.

## Structura Proiectului.

```
library_system/
├── main.py                  # CLI menu - intrarea
├── make_admin.py            # Script standalone pentru a initializa administratori in afara programului `main.py` 
├── database.py              # Conexiune SQLite + creare de tabel
├── book_manager.py          # Book CRUD + search
├── user_manager.py          # Inregistrare useri/listare
├── transaction_manager.py   # Logica Imprumut/Inapoiere + calculare amenzi
├── reservation_manager.py   # Lista de asteptare pentru carti fara copii valabile in librarie
├── reports_manager.py       # Statistici: cele mai imprumutate carti, cele mai mari amenzi etc.
└── README.md
```
- Fiecare modul vorbeste cu baza de date prin intermediul 'database.get_connection()'.
- 'main.py' nu se foloseste de SQL direct niciodata, doar apeleaza functii din celelalte 3 module.
- Separatia respectiva ajuta cu testarea si extinderea viitoare a programului (program modular).
- Comentariile care discuta modulele/codul aferent sunt scrisa in romana, iar comentariile
  care discuta o linie de cod/semnificatia liniei sunt scrise in engleza pentru a fi
  in concordanta cu limba aleasa pentru UI, si a nu amesteca limbiile respective.

## Schema bazei de date.

**books** — `id, title, author, isbn (unique), category, total_copies, available_copies`

**users** — `id, name, email (unique), role ('member' | 'admin')`

**transactions** — `id, book_id, user_id, borrow_date, due_date, return_date, fine`

`return_date IS NULL` inseamna ca imprumutul este inca activ.

**reservations** — `id, book_id, user_id, reservation_date, status, ready_date, fulfilled_date`

`status` is one of: `waiting, ready, fulfilled, cancelled.`

## Regulile librariei/bussines-ului.

- Perioada imprumut: termen de 14 zile, de la ziua imprumutului
- Amenda intarziere: $0.50 pe zi dupa termen, calcul facut automat la ziua returnarii
- O carte nu poate fi stearsa daca este in mod curent imprumutata sau daca are un istoric
  de imprumut (acest lucru protejeaza integritatea log-ului de tranzactii - 
  SQLite foreign key constraint => blocheaza stergerea oricum.)
- Reimprospatarea numarului total de copii a unei carti ajusteaza numarul actual de copii
  prin intermediul aceluiasi delta. Ca urmare, numarul curent de copii imprumutate ramane 
  in parametrii corecti.
- Rezervarea se poate efectuea doar daca exista 0 copii valabile. Acestea se fac dupa metoda first-in-first-out. 
  Cand o carte este inapoiata, este automat cedata urmatorului in linie (respectiv cea mai veche data de rezervare). 
  Persoana respectiva tot este obligata sa o "ridice" pentru a incepe procesul de imprumut. Daca o rezervare este stearsa,
  copia respectiva va ajunge la urmatorul in linia de asteptare.

## Oferire de permisiuni admin daca exista o baza de date curenta (blocat in afara).

```bash
python make_admin.py
```

## Cum se calculeaza amenzile?

- Amenzile sunt calculate doar la momentum inapoierii cartii, lucru bazat pe diferenta
  dintre 'due_date' si data actuala (a inapoierii).
- 'get_overdue_loans()' in 'transaction_manager.py' arata o amenda "live" pentru carti 
  care inca nu au fost inapoiate si sunt deja peste termen, doar ca amenda nu este scrisa
  pana cand cartea nu este inapoiata.

## Lucruri pe care le-am testat.

- Am adaugat o carte, am imprumutat-o, am incercat sa o sterg (in aceastea ordine) 
  Rezultat? => rulare blocata, nu se poate efectua o stergere pe o carte imprumutata.

- Am imprumutat o carte, am verificat manual `library.db` cu un browser SQLite pentru a vedea
  schema in actiune.

- Am incercat sa inregister doi useri cu acelasi email si acelasi nume.
  Rezultat? => rulare blocata, emailurile duplicat nu pot exista ele fiind identificatorul unic, 
  distinct al unui user. Numele duplicat, totusi, pot exista.

- Imprumut pentru o carte care nu mai este in stoc.
  Rezultat? => rulare blocata.

## Idei pentru extindere.

- Reservation queue: lasa un user sa "rezerve" o carte care nu mai este in stoc. (Gata)
- Email/console reminders pentru imprumuturi care vor trece timpul limita. 
- Analytics. (Gata)
- Schimb de la CLI la un simplu Flask web front-end.
- Autentificare reala (bcrypt/hashlib, in loc de email)
- CSV export
