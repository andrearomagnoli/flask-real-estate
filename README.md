# Introduction

## Purpose

This is a simple REST APIs solution that allows to add new real estate properties, containing images and spatial
coordinates, and return posted data. It allows filtering data by city or by range, otherwise you can choose to avoid
specifying a lookup mode and require only optional values.

Lookup mode `city`:

* `city`: City used for filter results.

Lookup mode `range`:

* `lat_from`: Latitude
* `long_from`: Longitude
* `range`: Radius expressed in kilometers

Optional paging arguments:

* `limit`: Limit number of records
* `page`: Requires `limit` if set, returns only the specified page of results

## Requirements

This real estate properties management API is built using:

* `Flask`
* `Docker`
* `PostgreSQL` with `PostGIS` (for geoip coordinates)

This solution runs on its own `Werkzeug` development server.

## IDE and testing

The IDE I've chosen for the development are `PyCharm Community Edition` and `DBeaver`.

Testing is performed using `Unittest`, that is natively integrated into `Python`.

# Quickstart

Requirements:

* Linux shell to execute `start.sh` script
* `postgresql-client` installed
* `docker` installed
* `docker-compose` installed

Place yourself into the project root directory and execute `start.sh` to set up and run the application:

```shell
./start.sh
```

Please note that the container with the web application waits until the database is up, and the health check is
performed correctly. Then, creates necessary database structures and populates sample data. Sample data is created only
during the first execution of the script.

# Testing

The solution uses `Unittest` for testing purposes. It requires a working environment to work, thus the
`./start.sh` must have been run previously. If the environment is running, tests create its own directories and database
structures that are isolated from the other logic, that keeps its consistency. Test cases need to be run from the 
`services/web` directory.

To run test cases, is required to execute the following commands from the root:

```shell
./start.sh
cd services/web
python test_real_estate.py
```

In order to collect the coverage, run the following commands:

```shell
./start.sh
cd services/web
coverage run --source=real_estate -m unittest test_real_estate.py && \
coverage run -a --source=utility -m unittest test_real_estate.py && \
coverage report -m
```

To date, there is a coverage of 95%.

# Swagger

The application provides a swagger API playground for testing purpose. Access it using http://localhost:8080/apidocs/
