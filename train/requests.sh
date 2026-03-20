# curl -X POST 'http://localhost:8000/api/predict' \
#   -H "Content-Type: application/json" \
#   -d {
#     "district": "大安區",
#     "building_area": 35,
#     "house_age": 20,
#     "start_floor": 5,
#     "total_floors": 12,
#     "rooms": 2,
#     "halls": 1,
#     "bathrooms": 1,
#     "has_parking": 1}

curl -X 'POST' \
  'http://localhost:8000/api/predict' \
  -H 'accept: application/json' \
  -H 'Content-Type: application/json' \
  -d '{
  "district": "大安區",
  "building_area": 35,
  "house_age": 20,
  "start_floor": 5,
  "total_floors": 12,
  "rooms": 2,
  "halls": 1,
  "bathrooms": 1,
  "has_parking": 1
}'