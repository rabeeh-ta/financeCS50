pk_23d4789871c444a5bb9c03fbc477237f

---------------------------------------------------------

python -m flask --app=application.py run
--------------------------------------------------------

CREATE TABLE users (id INTEGER, username TEXT NOT NULL, hash TEXT NOT NULL, cash NUMERIC NOT NULL DEFAULT 10000.00, PRIMARY KEY(id));
CREATE UNIQUE INDEX username ON users (username);