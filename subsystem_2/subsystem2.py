import math

class Lift:
    """The Lift class helps to define mechanical characteristics of a single lift unit.
    The helper methods allow travel times and other characterstics to be computed."""

    def __init__(self, vmax, acc, door_time, floor_height):
        self.vmax = vmax
        self.acc = acc
        self.td = door_time
        self.df = floor_height

        self.smv = self.vmax**2 / (2*self.acc)  # distance to reach max v
        self.tmv = self.vmax / self.acc         # time to reach max v

    def travel_time(self, n):
        """travel_time(n) calculates total time taken (seconds) to travel n integer floors this included closing of the doors and opening at the destination.
        
        """
        dist = self.df*n

        # travel distance is sufficient to reach max v
        if dist > 2*self.smv:
            return 2*self.tmv + (dist - 2*self.smv)/self.vmax + 2*self.td

        # travel distance is not sufficient to reach max v
        elif dist <= 2*self.smv:
            return 2*self.td + 2*math.sqrt(dist/self.acc)

        else:
            raise ValueError()
    
    def comp_travel(self, floors):
        """Calculates travel times taken to reach each target floor. List must include starting floor. Corresponding travel time for that floor will be 0. The floors must be in correct order."""
        
        time = 0
        times = [time]
        prev_n = floors[0]
        for n in floors[1:]:
            time += self.travel_time(n-prev_n)
            times.append(time)
            prev_n = n
        return times
        
