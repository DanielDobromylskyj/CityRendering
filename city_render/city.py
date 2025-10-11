import random
import pickle
from io import BufferedWriter, BufferedReader


def round_to_base(x, base):
    return base * round(x/base)


# todo - Add City / Saving / Loading using random.getstate() / random.setstate()


class City:
    BUILDING_BLOCK_SIZE: int = 50  # Thr amount of people that can fit inside of 1 building segment
    MAX_BUILDING_HEIGHT: int = 10  # I think this is obvious
    SPRAWL_AMOUNT: float = 0.5     # 0 -> 1 depending on how far outwards you want them to travel compared to going up

    def __init__(self, seed, population, is_loading=False):
        self.seed = seed
        self.__population = population

        self.random_state = random.getstate()
        self.building_order = [(1, 0), (0, 1), (-1, 0), (0, -1)]
        self.population_remaining = 0
        self.steps = 0

        self.city: list[dict] = []  # {"x": 0, "y": 0, "height": 1}
        self.available_buildings = []

        if not is_loading:
            self.__generate()

    def __generate(self):
        random.seed(self.seed)
        random.shuffle(self.building_order)
        self.random_state = random.getstate()

        self.city = []
        self.available_buildings = []
        self.steps = 0

        self.population_remaining = round_to_base(self.__population, 50)  # Round to closest 50
        self.__update_city()

    def __update_city(self):
        while self.population_remaining >= 0:
            random.setstate(self.random_state)
            self.population_remaining = self.__step(self.population_remaining)
            self.random_state = random.getstate()

    def get_building_population(self, index):
        return self.city[index]["height"] * self.BUILDING_BLOCK_SIZE

    def __get_free_location(self):
        if len(self.city) == 0:
            return 0, 0

        occupied = {(b["x"], b["y"]) for b in self.city}

        for building in self.city:
            x, y = building["x"], building["y"]

            for dx, dy in self.building_order:
                if (x + dx, y + dy) not in occupied:
                    return x + dx, y + dy

        return None  # Failed

    def __new_building(self):
        pos = self.__get_free_location()

        if pos:
            building = {
                "x": pos[0], "y": pos[1], "height": 1
            }

            self.city.append(building)

            if building["height"] < self.MAX_BUILDING_HEIGHT:
                self.available_buildings.append(len(self.city) - 1)  # Index into city

        else:
            print("[WARNING] Failed to generate new building position!")

    def __expand_building(self):
        building_index = random.choice(self.available_buildings)  # todo - make this more natural
        self.city[building_index]["height"] += 1

        if self.city[building_index]["height"] >= self.MAX_BUILDING_HEIGHT:
            self.available_buildings.remove(building_index)

    def __step(self, population_remaining: int) -> int:
        created_new_building = random.random() < self.SPRAWL_AMOUNT

        if created_new_building or len(self.available_buildings) == 0:
            self.__new_building()

        else:
            self.__expand_building()

        self.steps += 1
        return population_remaining - self.BUILDING_BLOCK_SIZE

    def set_population(self, new_population):
        if self.__population > new_population:
            self.__population = new_population
            self.__generate()  # Re-generate from scratch...

        else:
            self.population_remaining += (new_population - self.__population)
            self.__population = new_population
            self.__update_city()

    def store(self, file: BufferedWriter):
        # Binary mode required:
        if "b" not in file.mode:
            raise ValueError("File must be in binary mode!")

        # City Metadata
        file.write(int(self.__population).to_bytes(8, byteorder="big"))
        file.write(int(self.seed).to_bytes(8, byteorder="big", signed=True))
        file.write(int(self.steps).to_bytes(8, byteorder="big"))
        file.write(int(self.population_remaining).to_bytes(8, byteorder="big", signed=True))

        # Random state
        state_bytes = pickle.dumps(self.random_state)

        file.write(len(state_bytes).to_bytes(8, byteorder="big"))
        file.write(state_bytes)

        # City data
        file.write(len(self.city).to_bytes(8, byteorder="big"))
        for building in self.city:
            file.write(building["x"].to_bytes(8, byteorder="big", signed=True))
            file.write(building["y"].to_bytes(8, byteorder="big", signed=True))
            file.write(building["height"].to_bytes(8, byteorder="big"))

        # Available Buildings
        file.write(len(self.available_buildings).to_bytes(8, byteorder="big"))
        for building_index in self.available_buildings:
            file.write(building_index.to_bytes(8, byteorder="big"))

        # Build Order
        file.write(len(self.building_order).to_bytes(1, byteorder="big"))
        for x, y in self.building_order:
            file.write(x.to_bytes(1, byteorder="big", signed=True))
            file.write(y.to_bytes(1, byteorder="big", signed=True))

    @staticmethod
    def load(file: BufferedReader):
        # Binary mode required:
        if "b" not in file.mode:
            raise ValueError("File must be in binary mode!")

        # City Meta
        population = int.from_bytes(file.read(8), byteorder="big")
        seed = int.from_bytes(file.read(8), byteorder="big", signed=True)
        steps = int.from_bytes(file.read(8), byteorder="big")
        population_remaining = int.from_bytes(file.read(8), byteorder="big", signed=True)

        # Create city
        city = City(seed, population, is_loading=True)

        city.steps = steps
        city.population_remaining = population_remaining

        # Random state
        state_length = int.from_bytes(file.read(8), byteorder="big")
        state_bytes = file.read(state_length)
        city.random_state = pickle.loads(state_bytes)

        # City data
        building_count = int.from_bytes(file.read(8), byteorder="big")
        for _ in range(building_count):
            x = int.from_bytes(file.read(8), byteorder="big", signed=True)
            y = int.from_bytes(file.read(8), byteorder="big", signed=True)
            height = int.from_bytes(file.read(8), byteorder="big")

            building = {
                "x": x, "y": y, "height": height,
            }

            city.city.append(building)

        # Available buildings
        available_building_count = int.from_bytes(file.read(8), byteorder="big")
        for _ in range(available_building_count):
            index = int.from_bytes(file.read(8), byteorder="big")
            city.available_buildings.append(index)

        # Build Order
        city.building_order = []
        move_count = int.from_bytes(file.read(1), byteorder="big")
        for _ in range(move_count):
            x = int.from_bytes(file.read(1), byteorder="big", signed=True)
            y = int.from_bytes(file.read(1), byteorder="big", signed=True)
            city.building_order.append((x, y))

        return city

