import folium
import pandas as pd
from os.path import join, abspath, dirname
import webbrowser
import json
import ast
import io
from PIL import Image


geojson = abspath(join(dirname(abspath(__file__)),
                       'wohnviertel_stadt-stgallen.geojson'))

csv_clusters = abspath(join(dirname(abspath(__file__)),
                            '..', '..',
                            'glasscontainer_cluster.csv'))
cluster_df = pd.read_csv(csv_clusters)

fuellraten_by_cluster = abspath(join(dirname(abspath(__file__)),
                                     '..', '..', "data",
                                     'fuellraten_by_cluster.csv'))
fuellraten_df = pd.read_csv(fuellraten_by_cluster)

for color_de, color_en, col_en_de in zip(["Grün", "Weiss", "Braun"],
                                         ["green", "white", "brown"],
                                         ["gruen", "weiss", "braun"]):

    # Create a map centered around the general area of St. Gallen
    map_center = [47.424482, 9.376717]  # Latitude and Longitude of St. Gallen
    folium_map = folium.Map(location=map_center, zoom_start=13)

    # Background area of the city
    with open(geojson, 'r') as file:
        geojson_data = json.load(file)

        # Define a style function to remove border lines
        def style_function(feature):
            return {
                'fillColor': color_en,  # Set the fill color
                'fillOpacity': 0.2,  # Set the fill opacity
                'color': 'none'  # Set the border color to 'none' to remove border lines
            }

        # Add the GeoJSON data to the Folium map with the specified style function
        folium.GeoJson(
            geojson_data,
            style_function=style_function
        ).add_to(folium_map)

    # Adding each point from the GeoDataFrame
    cluster_nrs: list = cluster_df.cluster_nr.unique()
    for cluster_id in cluster_nrs:
        row = cluster_df[cluster_df['cluster_nr'] == cluster_id].iloc[0]
        lat = row['cluster_center'][0]
        lon = row['cluster_center'][1]
        coordinates_tuple = ast.literal_eval(row["cluster_center"])

        # Extract fill rate in % per day for each container cluster and color
        fill_row = fuellraten_df[(fuellraten_df['cluster_nr'] == cluster_id)
                                 & (fuellraten_df['glass_color'] == col_en_de)]
        fill_speed = fill_row["fuellrate_percentage_per_day"].values
        if len(fill_speed) == 1:
            fill_speed = fill_speed[0]
        else:
            fill_speed = 0.  # Missing data point

        # Create a RegularPolygonMarker (square in this case)
        # Adjust size according to fill ratio
        folium.RegularPolygonMarker(
            location=[coordinates_tuple[0], coordinates_tuple[1]],
            color="black",
            fill_color=color_en,
            fill_opacity=1,
            number_of_sides=4,  # Number of sides for a square
            radius=300 * fill_speed,  # Adjust the size as needed
            rotation=45,  # Rotation angle for the square (45 degrees for a diamond shape)
            popup=f"{cluster_id}"
        ).add_to(folium_map)

    # Rendering of map as png for power point
    # Requires Firefox browser and 'pip install SELENIUM' to work
    img_data = folium_map._to_png(3)  # second rendering time max
    img = Image.open(io.BytesIO(img_data))
    fname = f'{color_de} Map Fill Speed'
    img.save(fname + ".png")

    # Save map as html and open in default browser
    fname_html_map = fname+".html"
    folium_map.save(fname_html_map)
    webbrowser.open(fname_html_map, new=2)  # Use new=2 to open in a new tab