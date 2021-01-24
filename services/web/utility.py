import os
from base64 import b64encode, b64decode, decodebytes
from binascii import Error
from imghdr import what

from flask import jsonify, make_response, request
from sqlalchemy import create_engine
from sqlalchemy.engine import ResultProxy
from werkzeug.exceptions import abort


class HttpError(RuntimeError):
    """
    Custom exception for handling HTTP errors.
    """
    def __init__(self, arg):
        self.args = [arg]


class Database:

    @staticmethod
    def add_listing(address: str, city: str, price: float, coordinates: list, images: list) -> int:
        """
        Add a new listing to the database. All fields are required.

        Parameters
        ----------
        address : str
            Address of the property.

        city : str
            City of the property.

        price : float
            Price of the property, expressed in euros.

        coordinates : list
            List of str with geoip coordinates (latitude, longitude).

        images : list
            List of base64 str, containing images data.

        Returns
        -------
        int
            Listing unique ID.
        """
        db = create_engine(f"postgresql+psycopg2://root:password@database/docker")
        schema = os.getenv('TEST_SCHEMA') if os.getenv('TEST_SCHEMA') else 'public'

        # Fetch the next sequence
        listing_id = Database.next_sequence('listing_sequence')

        # Insert record into database
        db.execute(
            f"INSERT INTO {schema}.listing(id, address, city, price, coordinates, images) "
            "VALUES (%s, %s, %s, %s, ST_SetSRID(ST_MakePoint(%s, %s), 4326), %s);",
            listing_id, address, city, price, coordinates[0], coordinates[1], images
        )

        # Return sequence
        return listing_id

    @staticmethod
    def get_listings(km_range: float = None, gps: tuple = None, city: str = None,
                     limit: int = None, page: int = None) -> ResultProxy:
        """
        Get all listings, using optional paging argument. Please note that page is not allowed unless the limit is
        specified.

        Parameters
        ----------
        km_range : float (Default: None)
            Range used for spatial filtering.

        gps : tuple (Default: None)
            Geoip coordinate for spatial filtering.

        city : str (Default: None)
            City used to filter data.

        limit : int (Default: None)
            Limit of record to fetch.

        page : int (Default: None)
            Page to fetch.

        Returns
        -------
        ResultProxy
            Result of the query execution.
        """
        order_by = 'ORDER BY id ASC'
        where = ''

        # Compose order by clause
        if limit is not None:
            order_by += f" LIMIT {limit}"
            if page is not None:
                order_by += f" OFFSET {page * limit - limit}"

        # Compose where clause
        if city is not None:
            where = f"WHERE city='{city}'"

        if km_range is not None and gps is not None:
            where = f"{where} AND " if where != '' else "WHERE "
            where += f"ST_DWithin(" \
                     f"coordinates::geography, " \
                     f"ST_MakePoint({gps[0]}, {gps[1]})::geography, " \
                     f"{km_range * 1000.0})"

        # Execute query
        db = create_engine(f"postgresql+psycopg2://root:password@database/docker")
        schema = os.getenv('TEST_SCHEMA') if os.getenv('TEST_SCHEMA') else 'public'

        # Return results
        return db.execute(
            f"SELECT id, address, city, price, ST_X(coordinates) AS long, ST_Y(coordinates) AS lat, images "
            f"FROM {schema}.listing "
            f"{where} "
            f"{order_by};")

    @staticmethod
    def next_sequence(sequence: str) -> int:
        """
        Fetch the next sequence number.

        Parameters
        ----------
        sequence : str
            Name of the sequence.

        Returns
        -------
        int
            Next sequence number.
        """
        db = create_engine(f"postgresql+psycopg2://root:password@database/docker")
        schema = os.getenv('TEST_SCHEMA') if os.getenv('TEST_SCHEMA') else 'public'

        # Fetch the next sequence
        result = db.execute(f"SELECT nextval('{schema}.\"{sequence}\"');")
        count = 0
        sequence_number = None
        for row in result:
            sequence_number = row[0]
            count += 1

        # Validate sequence
        if count != 1:
            raise RuntimeError('Sequence must return only a single record')
        if sequence_number is None:
            raise RuntimeError('Sequence not retrieved correctly')

        return sequence_number


class Helper:

    @staticmethod
    def validate_int(value: str, minimum: int = None, maximum: int = None):
        """
        Get a str value and converts it to an int, validating against optional min and max values.

        Parameters
        ----------
        value : str
            Value to test and convert.

        minimum : int (Default: None)
            Minimum acceptable value.

        maximum : int (Default: None)
            Maximum acceptable value.

        Returns
        -------
        value : int
            Input str value converted to int.
        """
        if not value:
            return None
        try:
            if value:
                value = int(value)
                if minimum and value < minimum:
                    abort(400, 'Bad Request')
                if maximum and value > maximum:
                    abort(400, 'Bad Request')
        except ValueError:
            abort(400, 'Bad Request')

        return value

    @staticmethod
    def validate_float(value: str, minimum: float = None, maximum: float = None):
        """
        Get a str value and converts it to a float, validating against optional min and max values.

        Parameters
        ----------
        value : str
            Value to test and convert.

        minimum : float (Default: None)
            Minimum acceptable value.

        maximum : float (Default: None)
            Maximum acceptable value.

        Returns
        -------
        value : float
            Input str value converted to float.
        """
        if not value:
            return None
        try:
            if value:
                value = float(value)
                if minimum and value < minimum:
                    abort(400, 'Bad Request')
                if maximum and value > maximum:
                    abort(400, 'Bad Request')
        except ValueError:
            abort(400, 'Bad Request')

        return value

    @staticmethod
    def is_base64(content: str) -> bool:
        """
        Check if the provided content contains a valid base64 string.

        Parameters
        ----------
        content : str
            Str value to check.

        Returns
        -------
        bool
            True if `content` is a valid base64, otherwise False.
        """
        try:
            return b64encode(b64decode(content)) == bytes(content, 'utf-8')
        except Error:
            return False

    @staticmethod
    def save_image(content: str, server_path: str, host: str, port: int, web_path: str) -> str:
        """
        Save the image to the provided path and return its URL.

        Parameters
        ----------
        content : str
            Base64 value of the image.

        server_path : str
            Server path where the image will be saved.

        host : str
            Hostname of the server.

        port : int
            Port where the server is exposed.

        web_path : str
            Web path used to access the image.

        Returns
        -------
        str
            Unique image URL.
        """
        # Fetch the next sequence
        image_id = Database.next_sequence('image_sequence')

        # Save image to filesystem
        extension = what(None, h=b64decode(content))
        with open(f"{server_path}/{image_id}.{extension}", 'wb') as file:
            file.write(decodebytes(bytes(content, 'utf-8')))

        # Build and return the URL
        host = 'localhost' if host == '0.0.0.0' else host  # Handle development server

        return f"{host}:{port}/{web_path}/{image_id}.{extension}"

    @staticmethod
    def file_size(content: str) -> int:
        """
        Compute the approximate size of the file, given the base64 string.

        Parameters
        ----------
        content : str
            Base64 with file content.

        Returns
        -------
        int
            Estimated file size.
        """
        return int((len(content) * 3) / 4 - content.count('=', -2))

    @staticmethod
    def validate_image(content: str, allowed_extensions: set, maximum: int):
        """
        Validate given image format.

        Parameters
        ----------
        content : str
            Content in base64 of the image.

        allowed_extensions : set
            Set of allowed file extensions.

        maximum : int
            Maximum file size.
        """
        if not Helper.is_base64(content):
            abort(400, 'Bad Request')
        if what(None, h=b64decode(content)) not in allowed_extensions:
            abort(415, 'Unsupported Media Type')
        if Helper.file_size(content) > maximum:
            abort(400, 'Bad Request')
