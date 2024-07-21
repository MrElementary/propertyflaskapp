from flask import Flask, jsonify, request
import json
import os
import psycopg2
from flask_cors import CORS
import cloudinary
import cloudinary.uploader
from cloudinary.utils import cloudinary_url


#################################################
# Flask Setup
#################################################
app = Flask(__name__)
CORS(app)
app.url_map.strict_slashes = False

#################################################
# Cloudinary Connection details
#################################################
cloudinary.config( 
    cloud_name = os.getenv('CLOUDINARY_CLOUD_NAME'),
    api_key = os.getenv('CLOUDINARY_API_KEY'),
    api_secret = os.getenv('CLOUDINARY_API_SECRET'), 
    secure=True
)


#################################################
# DB Connection details
#################################################

def connection_func():
    try:
        db_url= os.getenv('DATABASE_URL')
        conn = psycopg2.connect(db_url)
        print("connection successful")
    except psycopg2.OperationalError as e:
        print(f"Error: {e}")

    if not conn.closed:
        print("Connection is OK!")
        return conn
    else:
        print("Connection is not OK!")




#################################################
# Flask Routes
#################################################

# SQL Queries
@app.route("/api/v1/storepost", methods=["POST"])
def post_data():
    form_data = request.form
    #print("step 1")
    json_string = form_data['data']
    #print("step 2")
    data = json.loads(json_string)
    #print(data)

    person_name = data['person_name']
    property_name = data['property_name']
    address = data['address']
    price = data['price']
    house_type = data['type']
    bedroom = data['bedroom']
    bathroom = data['bathroom']
    total_floors = data['total_floors']
    garden = data['garden']
    power = data['power']
    description = data['description']

    image_urls = []
    for img in request.files.getlist('images'):
        upload_result = cloudinary.uploader.upload(img)
        image_urls.append(upload_result["secure_url"])
        print(upload_result["secure_url"])
    #print(image_urls)

    while len(image_urls) < 5:
        image_urls.append(None)
        

    insert_string = """INSERT INTO property (user_id, property_name, address,
                        price, type, bedroom, bathroom, total_floors, garden,
                        power_backup, description)
                        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)"""

    insert_images_url = """INSERT INTO property_images (property_name, image1,
                            image2, image3, image4, image5) VALUES
                            (%s, %s, %s, %s, %s, %s)"""

    conn = connection_func()
    cur = conn.cursor()
    
    try:
        cur.execute(insert_images_url, (property_name, image_urls[0], image_urls[1], image_urls[2], image_urls[3], image_urls[4]))
        cur.execute(insert_string, (person_name, property_name, address, price, house_type, bedroom, bathroom, total_floors, garden, power, description))
        conn.commit()
        print("Property inserted successfully!")
        cur.close()
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error inserting property: {e}")
    finally:
        cur.close()
        conn.close()
        
    print("success!")
    return jsonify({
            'message': 'Data received!',
            'property_name': property_name,
            'image_urls': image_urls
        })

# Route for retrieving data from the database
@app.route("/api/v1/retrievedata", methods=["GET"])
def retrieve_data():
    try:
        conn = connection_func()
        cur = conn.cursor()
        
        # Fetch the property data
        cur.execute("SELECT * FROM property")
        properties = cur.fetchall()


        # Fetch the property image URLs
        cur.execute("SELECT * FROM property_images")
        property_images = cur.fetchall()


        # Create a dictionary to store combined data
        combined_data = {}
        index = 1
        
        for prop in properties:

            property_name = prop[2]
            images = next((img for img in property_images if img[0] == property_name), None)
            if images:
                image_list = [images[1], images[2], images[3], images[4], images[5]]
                image_list = [image for image in image_list if image]
            else:
                image_list = []

            combined_data[f'property_{index}'] = {
                'property_name': prop[2],
                'address': prop[3],
                'price': prop[4],
                'type': prop[5],
                'bedroom': prop[6],
                'bathroom': prop[7],
                'total_floors': prop[8],
                'garden': prop[9],
                'power': prop[10],
                'description': prop[11],
                'images': image_list,
            }
            index += 1

        cur.close()
        conn.close()

        print(combined_data)

        return jsonify(combined_data), 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500


@app.route("/api/v1/addtowishlist", methods=["POST"])
def add_to_wishlist():
    data = request.get_json()
    user_name = data['user_name']
    wishlist_property = data['wishlist_property']

    insert_wishlist = """INSERT INTO wishlist (user_name, wishlist_property)
                         VALUES (%s, %s)"""

    conn = connection_func()
    cur = conn.cursor()
    
    try:
        cur.execute(insert_wishlist, (user_name, wishlist_property))
        conn.commit()
        print("Wishlist entry inserted successfully!")
        cur.close()
    except psycopg2.Error as e:
        conn.rollback()
        print(f"Error inserting wishlist entry: {e}")
    finally:
        cur.close()
        conn.close()
        
    return jsonify({'message': 'Wishlist entry added successfully!'})

@app.route("/api/v1/retrievefavorites", methods=["GET"])
def retrieve_favorites():
    user_name = request.args.get('username')  # Get the username from query parameters
    
    if not user_name:
        return jsonify({"error": "Username not provided"}), 400
    
    try:
        conn = connection_func()
        cur = conn.cursor()
        
        # Fetch the favorited property data
        cur.execute("""
            SELECT p.*, pi.image1, pi.image2, pi.image3, pi.image4, pi.image5 
            FROM property p
            JOIN wishlist w ON p.property_name = w.wishlist_property
            LEFT JOIN property_images pi ON p.property_name = pi.property_name
            WHERE w.user_name = %s
        """, (user_name,))
        
        favorites = cur.fetchall()

        # Create a dictionary to store combined data
        combined_data = {}
        index = 1
        
        for fav in favorites:
            property_name = fav[2]
            image_list = [fav[12], fav[13], fav[14], fav[15], fav[16]]
            image_list = [image for image in image_list if image]

            combined_data[f'property_{index}'] = {
                'property_name': fav[2],
                'address': fav[3],
                'price': fav[4],
                'type': fav[5],
                'bedroom': fav[6],
                'bathroom': fav[7],
                'total_floors': fav[8],
                'garden': fav[9],
                'power': fav[10],
                'description': fav[11],
                'images': image_list,
            }
            index += 1

        print(combined_data)

        cur.close()
        conn.close()

        return jsonify(combined_data), 200

    except Exception as e:
        print(e)
        return jsonify({"error": str(e)}), 500

@app.route("/api/v1/removefromwishlist", methods=["DELETE"])
def remove_from_wishlist():
    user_name = request.args.get('username')
    property_name = request.args.get('property_name')

    if not user_name or not property_name:
        return jsonify({"error": "Invalid input"}), 400

    try:
        conn = connection_func()
        cur = conn.cursor()

        delete_query = "DELETE FROM wishlist WHERE user_name = %s AND wishlist_property = %s"
        cur.execute(delete_query, (user_name, property_name))
        conn.commit()

        cur.close()
        conn.close()

        return jsonify({"message": "Wishlist item removed successfully!"}), 200
    except psycopg2.Error as e:
        return jsonify({"error": str(e)}), 500

    
# Run the App
if __name__ == '__main__':
    app.run()
