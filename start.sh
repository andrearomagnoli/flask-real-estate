#!/bin/sh

# Creating the environment

docker-compose up -d --build --no-recreate

# Creating sequences and tables

POSTGRES_USER=root
POSTGRES_PASS=password
POSTGRES_DB=docker

set -e
export PGPASSWORD=$POSTGRES_PASS;
psql -h localhost -U $POSTGRES_USER $POSTGRES_DB <<-EOSQL
  \connect $POSTGRES_DB $POSTGRES_USER
  CREATE SEQUENCE IF NOT EXISTS public.listing_sequence
    start with 1
    increment 1;
  CREATE SEQUENCE IF NOT EXISTS public.image_sequence
    start with 5
    increment 1;
  CREATE TABLE IF NOT EXISTS public.listing
  (
    id INT PRIMARY KEY
    ,address VARCHAR(200)
    ,city VARCHAR(50)
    ,price NUMERIC
    ,coordinates geometry(GEOMETRY,4326)
    ,images TEXT[]
  );
EOSQL

# Filling tables

echo ""
if [ "$(psql -h localhost -U root docker -c "SELECT 1 FROM public.listing;" -t | wc -l)" -eq 1 ];
then
  echo "Table 'public.listing' is empty, filling it with sample data...";
psql -h localhost -U $POSTGRES_USER $POSTGRES_DB <<-EOSQL
  \connect $POSTGRES_DB $POSTGRES_USER
  INSERT INTO public.listing
  (id, address, city, price, coordinates, images)
  VALUES
  (nextval('listing_sequence'), 'Via Montebello, 20, 10124 Torino TO', 'Torino', 1252950.0, ST_SetSRID(ST_MakePoint(45.0700962,7.6700891), 4326), ARRAY['localhost:8080/image/1.jpg']),
  (nextval('listing_sequence'), 'Corso Bolzano, 10121 Torino TO', 'Torino', 1252950.0, ST_SetSRID(ST_MakePoint(45.072278,7.6623375), 4326), ARRAY['localhost:8080/image/2.jpg', 'localhost:8080/image/3.jpg']),
  (nextval('listing_sequence'), 'Piazza Principe Amedeo, 7, 10042 Stupinigi, Nichelino TO', 'Stupinigi', 1252950.0, ST_SetSRID(ST_MakePoint(44.9953161,7.6023366), 4326), ARRAY['localhost:8080/image/4.jpg']);
EOSQL
else
  echo "Table 'public.list' is not empty, left it as-is!";
fi
