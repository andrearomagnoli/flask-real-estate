import json
import os

from flasgger import Swagger, swag_from
from flask import Flask, request, jsonify
from werkzeug.exceptions import abort, HTTPException

from utility import Database, Helper

# Initialization

app = Flask(__name__, static_folder='static')
swagger = Swagger(app)

HOST = '0.0.0.0'
PORT = 8080
MAX_IMAGE_SIZE = 4 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}


# Error handler

@app.errorhandler(HTTPException)
def handle_exception(e):
    """
    Return JSON instead of HTML for HTTP errors.
    """
    # Customize the error response
    response = e.get_response()
    response.data = json.dumps({
        "error": e.description,
    })
    response.content_type = "application/json"

    # Return the response as a JSON with an error string
    return response


# REST APIs

@app.route('/listing', methods=['POST'])
@swag_from('specifications/post_listing.yml', methods=['POST'])
def post_listing():
    """
    Post real estate property listing, including geoip coordinates and images base64.
    """
    # Read arguments
    address = request.json.get('address')
    city = request.json.get('city')
    price = Helper.validate_float(request.json.get('price'))
    coordinates = request.json.get('coordinates')
    images = request.json.get('images')

    # Validate geoip coordinates
    if len(coordinates) != 2:
        abort(400, 'Bad Request')
    Helper.validate_float(coordinates[0], minimum=-90.0, maximum=90.0)
    Helper.validate_float(coordinates[1], minimum=-180.0, maximum=180.0)

    # Validate images
    [Helper.validate_image(image, allowed_extensions=ALLOWED_EXTENSIONS, maximum=MAX_IMAGE_SIZE) for image in
     images]

    # Save images and return URLs
    upload_folder = app.static_folder if not os.getenv('TEST_FOLDER') else os.getenv('TEST_FOLDER')
    image_urls = [Helper.save_image(image, upload_folder, HOST, PORT, 'image') for image in images]

    # Add validated data to database
    listing_id = None
    try:
        listing_id = Database.add_listing(address, city, price, coordinates, image_urls)
    except RuntimeError:
        abort(500)
    if listing_id is None:
        abort(500)

    # Return inserted data
    return jsonify({
        'id': listing_id,
        'address': address,
        'city': city,
        'price': price,
        'coordinates': coordinates,
        'images': image_urls
    })


@app.route('/listings', methods=['GET'])
@swag_from('specifications/get_listings.yml', methods=['GET'])
def get_listings():
    """
    Get real estate property listings, performing optional pagination and filtering by city or geoip range.
    """
    # Read lookup mode
    lookup_mode = request.args.get('lookup_mode')

    # Read paging arguments
    limit = Helper.validate_int(request.args.get('limit'), minimum=0)
    page = Helper.validate_int(request.args.get('page'), minimum=1)

    # Read range arguments
    km_range = Helper.validate_float(request.args.get('range'))
    latitude = Helper.validate_float(request.args.get('lat_from'), minimum=-90.0, maximum=90.0)
    longitude = Helper.validate_float(request.args.get('long_from'), minimum=-180.0, maximum=180.0)

    # Read city arguments
    city = request.args.get('city') if request.args.get('city') else None

    # Validate paging arguments
    if page and not limit:
        abort(400, 'Bad Request')
        # limit = 100  # instead of throwing an error you can choose a default limit value

    # Validate lookup consistency: city, range, null
    if lookup_mode == 'city':
        if not city:
            abort(400, 'Bad Request')
        if km_range or latitude or longitude:
            abort(400, 'Bad Request')
    elif lookup_mode == 'range':
        if not km_range or not latitude or not longitude:
            abort(400, 'Bad Request')
        if city:
            abort(400, 'Bad Request')
    else:
        if city or km_range or latitude or longitude:
            abort(400, 'Bad Request')

    # Radius search with geospatial coordinates (with optional paging)
    if lookup_mode == 'range':
        listings = Database.get_listings(limit=limit, page=page, km_range=km_range, gps=(latitude, longitude))

    # Filter by city (with optional paging)
    elif lookup_mode == 'city':
        listings = Database.get_listings(limit=limit, page=page, city=city)

    # Return all results (with optional paging)
    else:
        listings = Database.get_listings(limit=limit, page=page)

    # Construct response array
    result = []
    for listing in listings:
        result.append({
            'id': listing[0],
            'address': listing[1],
            'city': listing[2],
            'price': float(listing[3]),
            'coordinates': [listing[4], listing[5]],
            'images': listing[6]
        })

    # Return response
    return jsonify(result)


@app.route('/image/<string:image>', methods=['GET'])
@swag_from('specifications/get_image.yml', methods=['GET'])
def get_image(image):
    """
    Get image flask function.

    Parameters
    ----------
    image : str
        Name of the requested image.
    """
    return app.send_static_file(image)


if __name__ == '__main__':
    app.run(debug=True, host=HOST, port=PORT)
