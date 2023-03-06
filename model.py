from mesa import Model
from mesa.time import SimultaneousActivation
from mesa.space import SingleGrid
from mesa.datacollection import DataCollector

from agents import Car, TrafficLight, Field

import numpy as np
import random


def get_grid(model):
    grid = np.zeros((model.grid.width, model.grid.height))

    # Por todas las celdas del grid
    for cell in model.grid.coord_iter():
        agent, x, y = cell

        if isinstance(agent, Car):
            if agent.colour == 'orange':
                grid[x][y] = 6
            elif agent.colour == 'blue':
                grid[x][y] = 7
            elif agent.colour == 'purple':
                grid[x][y] = 8
            else:  # black
                grid[x][y] = 9

        elif isinstance(agent, Field):
            if agent.colour == 'brown':
                grid[x][y] = 3
            elif agent.colour == 'olive':
                grid[x][y] = 4
            else:  # dark green
                grid[x][y] = 5

        elif isinstance(agent, TrafficLight):
            if agent.colour == 'green':
                grid[x][y] = 2
            else:  # red
                grid[x][y] = 1

        else:  # Street
            grid[x][y] = 0
 
    return grid


def get_waiting(model):
    total_waiting_time = 0

    # Por todas las celdas del grid
    for cell in model.grid.coord_iter():
        agent, x, y = cell
        if isinstance(agent, Car):
            total_waiting_time += agent.waiting

    return total_waiting_time


def get_running(model):
    return model.num_agents - get_waiting(model)


class CrossRoad(Model):
    """A model with some number of agents."""

    def __init__(self, num_agents=10, half_length=10, traffic_time=10, car_turning_rate=0.1):
        self.num_agents = num_agents
        self.running = True

        # Dimensions are double of given values
        self.centre_bounds = (half_length - 1, half_length + 1)
        self.width = half_length * 2
        self.height = half_length * 2

        self.grid = SingleGrid(self.width, self.height, True)
        self.schedule = SimultaneousActivation(self)
        self.traffic_counter = 0
        self.traffic_time = traffic_time

        # Define cross road centre
        no_car_zone = half_length + np.arange(-2, 2)

        # Define traffic light positions according to street direction
        traffic_light_positions = {
            'right': (half_length + 2, half_length + 2),
            'left': (half_length - 2, half_length - 2),
            'up': (half_length - 2, half_length + 2),
            'down': (half_length + 2, half_length - 2),
        }

        # Possible turns
        self.centre = [(half_length + x, half_length + y) for x in [-1, 1] for y in [-1, 1]]
        self.possible_turns = {
            'right': {self.centre[2]: 'down', self.centre[3]: 'up'},
            'left': {self.centre[1]: 'up', self.centre[0]: 'down'},
            'up': {self.centre[3]: 'right', self.centre[1]: 'left'},
            'down': {self.centre[0]: 'left', self.centre[2]: 'right'}
        }

        # Define streets
        streets = {
            'left': [(half_length - 1, y) for y in range(self.height)
                     if y not in no_car_zone],
            'right': [(half_length + 1, y) for y in range(self.height)
                      if y not in no_car_zone],
            'up': [(x, half_length + 1) for x in range(self.width)
                   if x not in no_car_zone],
            'down': [(x, half_length - 1) for x in range(self.width)
                     if x not in no_car_zone]
        }

        traffic_light_count = 100
        self.traffic_lights = {}
        # Create traffic light agents
        for direction, pos in traffic_light_positions.items():
            col = 'green' if traffic_light_count == 100 else 'red'
            a = TrafficLight(traffic_light_count, col, self)

            self.traffic_lights[direction] = a
            traffic_light_count += 1
            self.grid.place_agent(a, pos)

        field_count = 1000
        for cell in self.grid.coord_iter():
            _, x, y = cell
            # Create field agents
            if np.abs(x - half_length) > 1 and np.abs(y - half_length) > 1 and self.grid.is_cell_empty((x, y)):
                a = Field(field_count, self)
                self.schedule.add(a)
                field_count += 1
                self.grid.place_agent(a, (x, y))

        # Create Car agents
        car_colours = random.choices(Car.COLOURS, k=self.num_agents)
        car_directions = random.choices(Car.DIRECTIONS, k=self.num_agents)

        for i, (col, direction) in enumerate(zip(car_colours, car_directions)):
            a = Car(i, self, col, direction, car_turning_rate)
            self.schedule.add(a)

            # Picks a position and remove it from the availables
            position = random.choices(streets[direction], k=1)[0]
            streets[direction].remove(position)

            self.grid.place_agent(a, position)

        self.datacollector = DataCollector(
            model_reporters={"Grid": get_grid, "Waiting": get_waiting, "Running": get_running}
        )

    def step(self):
        self.datacollector.collect(self)
        self.schedule.step()

        if self.traffic_counter < self.traffic_time:
            self.traffic_counter += 1
        else:
            for i, direction in enumerate(Car.DIRECTIONS):
                # print(self.traffic_lights)
                if self.traffic_lights[direction].colour == 'green':
                    self.traffic_counter = 0
                    self.traffic_lights[direction].colour = 'red'

                    next_i = i + 1 if i < len(Car.DIRECTIONS) - 1 else 0
                    self.traffic_lights[Car.DIRECTIONS[next_i]].colour = 'green'
                    break
