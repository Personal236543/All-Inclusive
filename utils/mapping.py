def map_hotel(hotels, hotel_name):
    return hotels.get(hotel_name, None)

def map_room(hotels, hotel_name, room_name):
    hotel = map_hotel(hotels, hotel_name)
    if hotel is None:
        return None
    return hotel.get(room_name, None)

def map_pair(hotels, hotel_name, room_name):
    hotel = map_hotel(hotels, hotel_name)
    if hotel is None:
        return (None, None)
    room = hotel.get(room_name, None)
    return (hotel["name"], room)