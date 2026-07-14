from parser import Parser
from graph import Graph
from simulationstats import Drone, SimulationState


def main() -> None:
    parser = Parser("map.txt").parse()
    graph = Graph(parser)
    drone = Drone()