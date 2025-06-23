-- Log in as administrator to run this initial setup
-- choose a password

CREATE USER watersense IDENTIFIED BY "MyStrongPassword";

GRANT CONNECT, RESOURCE TO watersense;
GRANT EXECUTE ON DBMS_CRYPTO TO WATERSENSE;

ALTER USER watersense QUOTA UNLIMITED ON data;

