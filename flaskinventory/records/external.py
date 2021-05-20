import geocoder
import time

def get_geocoords(address):
    time.sleep(5)
    r = geocoder.osm(address)
    if r.status_code != 200:
        return False
    return r.geojson.get('features')[0].get('geometry')
    