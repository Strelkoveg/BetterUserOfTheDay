-- create the database
CREATE DATABASE IF NOT EXISTS test_database;

-- create the user for database
CREATE USER 'bot'@'%' IDENTIFIED BY '11111';
GRANT CREATE, ALTER, INDEX, LOCK TABLES, REFERENCES, UPDATE, DELETE, DROP, SELECT, INSERT ON `test_database`.* TO 'bot'@'%';

FLUSH PRIVILEGES;
