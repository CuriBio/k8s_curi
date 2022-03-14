/* CREATE DATABASE curibio; */
/* CREATE EXTENSION IF NOT EXISTS "uuid-ossp"; */

CREATE USER curibio_users;
GRANT ALL PRIVILEGES ON users TO curibio_users;
GRANT USAGE ON SEQUENCE users_row_id_seq TO curibio_users;

CREATE USER curibio_users_ro;
GRANT SELECT ON users TO curibio_users_ro;
