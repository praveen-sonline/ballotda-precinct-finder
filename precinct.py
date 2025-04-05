import streamlit as st
import requests
import folium
import pandas as pd
from folium.plugins import PolyLineTextPath
from streamlit_folium import folium_static
from io import BytesIO

# Define the API key (replace with your actual key)
api_key = st.secrets["api_keys"]["google_maps"]

# County and Precinct Data
greenville_precincts = {
    "262": {"name": "Furman", "address": "871 N Highway 25 Byp, Greenville SC 29617", "coords": [34.8882, -82.4534]},
    "271": {"name": "Laurel Ridge", "address": "911 Saint Mark Rd, Taylors SC 29687", "coords": [34.9040, -82.2960]},
    "298": {"name": "Raintree", "address": "257 Harrison Bridge Rd, Simpsonville SC 29680", "coords": [34.7033, -82.3123]},
    "303": {"name": "Rocky Creek", "address": "1801 Woodruff Rd, Greenville SC 29607", "coords": [34.8293, -82.2855]},
    "336": {"name": "Wade Hampton", "address": "500 W Lee Rd, Taylors SC 29687", "coords": [34.8848, -82.3384]},
    "359": {"name": "Moore Creek", "address": "1800 W Georgia Rd, Simpsonville SC 29680", "coords": [34.6934, -82.3054]},
    "368": {"name": "Verdmont", "address": "1420 Neely Ferry Rd, Simpsonville SC 29680", "coords": [34.7277, -82.3219]},
}

gwinnett_precincts = {
    "001": {"name": "Harbins A", "address": "3550 New Hope Road, Dacula, GA 30019", "coords": [34.0310, -83.9008]},
    "002": {"name": "Rockbridge A", "address": "3150 Spain Road, Snellville, GA 30039", "coords": [33.8090, -84.0382]},
    "003": {"name": "Dacula", "address": "202 Hebron Church Road NE, Dacula, GA 30019", "coords": [33.9925, -83.8974]},
    "004": {"name": "Suwanee A", "address": "361 Main Street, Suwanee, GA 30024", "coords": [34.0515, -84.0713]},
    "005": {"name": "Baycreek A", "address": "555 Grayson Parkway, Grayson, GA 30017", "coords": [33.8945, -83.9630]},
    "006": {"name": "Goodwins A", "address": "1570 Lawrenceville Suwanee Road, Lawrenceville, GA 30043", "coords": [33.9876, -84.0769]},
    "007": {"name": "Duluth A", "address": "3167 Main Street NW, Duluth, GA 30096", "coords": [34.0020, -84.1446]},
    "008": {"name": "Duncans A", "address": "4404 Braselton Highway, Hoschton, GA 30548", "coords": [34.0992, -83.7854]},
    "009": {"name": "Picketts A", "address": "2723 N Bogan Road, Buford, GA 30519", "coords": [34.1275, -83.9833]},
    "010": {"name": "Cates A", "address": "2428 Main Street East, Snellville, GA 30078", "coords": [33.8573, -84.0199]},
}

counties = {
    "SC Greenville County": greenville_precincts,
    "Gwinnett County": gwinnett_precincts,
}

# Function to fetch data from Google Places API
def fetch_places_data(api_key, location, radius, place_types):
    if not place_types:
        return None
    endpoint = "https://maps.googleapis.com/maps/api/place/nearbysearch/json"
    params = {
        "location": location,
        "radius": radius,
        "types": "|".join(place_types),
        "key": api_key
    }
    response = requests.get(endpoint, params=params)
    return response.json() if response.status_code == 200 else None

# Function to get driving distance using Google Directions API
def get_driving_distance(api_key, origin, destination):
    endpoint = "https://maps.googleapis.com/maps/api/directions/json"
    params = {
        "origin": origin,
        "destination": destination,
        "key": api_key
    }
    response = requests.get(endpoint, params=params)
    if response.status_code == 200:
        routes = response.json().get('routes', [])
        if routes:
            legs = routes[0].get('legs', [])
            if legs:
                distance_text = legs[0]['distance']['text']
                duration_text = legs[0]['duration']['text']
                return distance_text, duration_text
    return None, None

# Function to create map with precinct markers
def create_precinct_map(precincts):
    coords = list(precincts.values())[0]["coords"]
    precinct_map = folium.Map(location=coords, zoom_start=10)
    for number, data in precincts.items():
        folium.Marker(
            location=data["coords"],
            popup=f"<strong style='color:black;'>Precinct {number} - {data['name']}</strong><br>{data['address']}",
            icon=folium.Icon(color='red', icon='flag')
        ).add_to(precinct_map)
    return precinct_map

# Function to map nearby places
def create_places_map(places_data, center_location, precinct_name):
    map_ = folium.Map(location=center_location, zoom_start=12)
    folium.Marker(location=center_location, popup=f"<strong>{precinct_name}</strong> - Precinct Location", icon=folium.Icon(color='red', icon='flag')).add_to(map_)

    distances = []
    if places_data and 'results' in places_data:
        for place in places_data['results']:
            lat = place['geometry']['location']['lat']
            lng = place['geometry']['location']['lng']
            driving_distance, driving_time = get_driving_distance(api_key, f"{center_location[0]},{center_location[1]}", f"{lat},{lng}")

            distances.append({
                'name': place['name'],
                'driving_distance': driving_distance,
                'driving_time': driving_time,
                'address': place.get('vicinity', 'Address not available'),
                'location': (lat, lng)
            })

        distances = [d for d in distances if d['driving_distance'] is not None]
        distances.sort(key=lambda x: float(x['driving_distance'].split()[0].replace(',', '')))

        for place in distances:
            folium.Marker(
                location=place['location'],
                popup=f"<strong style='color:black;'>{place['name']}</strong><br><strong style='color:black;'>Driving:</strong> {place['driving_distance']} ({place['driving_time']})<br><strong style='color:black;'>Address:</strong> {place['address']}",
                icon=folium.Icon(color='blue', icon='info-sign')
            ).add_to(map_)

        for place in distances[:5]:
            folium.PolyLine(locations=[center_location, place['location']], color="blue", weight=2.5, opacity=1).add_to(map_)

    return map_, distances

# Streamlit app
def main():
    st.markdown("<h2>BallotDA - Discovering Nearby Places Around Precinct Locations</h2>", unsafe_allow_html=True)

    county = st.selectbox("Select County", list(counties.keys()), index=0)
    precincts = counties[county]

    st.markdown("<h3 style='font-size:20px;'>Precinct Locations Marked on the Map</h3>", unsafe_allow_html=True)
    precinct_map = create_precinct_map(precincts)
    folium_static(precinct_map)

    st.markdown("---")
    st.markdown("<h3>Discover Nearby Places</h3>", unsafe_allow_html=True)

    selected_precinct = st.selectbox("Select a Precinct Number", list(precincts.keys()))
    selected_place_type = st.selectbox("Select a Place Type", options=["church", "school", "library", "community_center"], index=0)

    if selected_precinct:
        data = precincts[selected_precinct]
        location = f"{data['coords'][0]},{data['coords'][1]}"
        places_data = fetch_places_data(api_key, location, 32186, [selected_place_type])

        if places_data:
            st.success(f"\U0001F4CD Showing results near {data['name']} - {data['address']}")
            places_map, distances = create_places_map(places_data, data['coords'], data['name'])
            folium_static(places_map)

            df = pd.DataFrame([{ "Name": d['name'], "Address": d['address'], "Driving Distance": d['driving_distance'], "Driving Time": d['driving_time'] } for d in distances])
            st.dataframe(df, use_container_width=True)

            # Export to Excel
            output = BytesIO()
            with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                df.to_excel(writer, index=False, sheet_name='Nearby Places')
            output.seek(0)

            st.download_button(label="\U0001F4E5 Download Excel", data=output, file_name='nearby_places.xlsx', mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')

if __name__ == "__main__":
    main()