from city_render.city import City
from city_render.render import render_city

seed = 123456
start_population = 5000

city = City(seed, start_population)

render_city(city)
