def get_params(json_response):
    toponym = json_response["response"]["GeoObjectCollection"]["featureMember"][0]["GeoObject"]
    lower_corner = toponym['boundedBy']['Envelope']['lowerCorner'].split()
    upper_corner = toponym['boundedBy']['Envelope']['upperCorner'].split()
    w = float(upper_corner[0]) - float(lower_corner[0])
    h = float(upper_corner[1]) - float(lower_corner[1])
    # Координаты центра топонима:
    toponym_coodrinates = toponym["Point"]["pos"]
    # Долгота и широта:
    toponym_longitude, toponym_lattitude = map(float, toponym_coodrinates.split(" "))
    return [toponym_longitude, toponym_lattitude, w, h]
