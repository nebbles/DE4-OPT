import math

class Lift:
    """The Lift class helps to define mechanical characteristics of a single lift unit.
    The helper methods allow travel times and other characterstics to be computed."""

    def __init__(self, id=None, capacity=8, vmax=5.0, acc=1.0, door_time=0.0, floor_height=4.0, capacity_threshold = 1.0):
        self.id = id
        self.capacity = capacity
        self.vmax = vmax
        self.acc = acc
        self.td = door_time
        self.df = floor_height

        self.smv = self.vmax**2 / (2*self.acc)  # distance to reach max v
        self.tmv = self.vmax / self.acc         # time to reach max v

        self.available = True
        self.arrival_time = 0
        self.passengers = []
        self.passenger_travel_times = []
        self.rtt = None
        self.queue = []
        self.history = [(0,0)]

        self.printing = False

        # percentage of passengers required before automatic departure
        self.capacity_threshold = capacity_threshold

    def log(self, msg):
        if self.printing:
            print(msg)

    def is_available(self):
        return self.available

    def set_print(self, setting:bool):
        self.printing = setting

    def set_capacity_threshold(self, ct):
        if ct is not float:
            raise TypeError('Capacity threshold value must be a float.')
        if ct >= 0 and ct <= 1.0:
            self.capacity_threshold = ct
        else:
            raise ValueError('Value of capacity threshold must be between 0 and 1 inclusive.')

    def get_arrival_time(self):
        return self.arrival_time

    def get_queue_length(self):
        return len(self.queue)

    def get_total_passengers(self):
        return len(self.passengers)

    def get_avg_floor(self):
        """Calculates average destination floor for relevant subset of passengers that the next added passenger will travel with."""
        running_order = self.passengers + self.queue
        total = len(running_order)

        if total == 0:
            return 0

        if total < self.capacity:
            return sum([p['destination'] for p in running_order])/total # average destination
        
        else:
            rem = total % self.capacity # calculate remainder
            if rem == 0:
                return 0  # avg floor is irrelevant to the caller
            else:
                relevant_ps = running_order[-rem:] # relevant passengers to caller
                return sum([p['destination'] for p in relevant_ps])/len(relevant_ps) # average


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

    def update_trip_times(self, clock):
        # sort the passengers in order of requested floor
        self.passengers = sorted(self.passengers, key=lambda p: p['destination'])

        time = 0
        prev_n = 0 # start at ground floor

        self.history.append((clock, 0))

        # move to each floor
        for p in self.passengers:
            n = p['destination']
            time += self.travel_time(n-prev_n)
            p['time.travelling'] = time
            self.passenger_travel_times.append(time)
            self.history.append((time+clock, n))
            prev_n = n
        
        # return to ground
        n = 0
        time += self.travel_time(abs(0-prev_n))
        self.history.append((time+clock, n))
        
        return time # RTT

    def check_departure(self, clock):
        """Will load any waiting passengers into the lift until full. Will depart when at full capacity, or when reached the departure threshold and there are no waiting passengers."""
        if len(self.queue) > 0:
            if len(self.passengers) < self.capacity:
                passenger = self.queue.pop(0)
                passenger['time.enter_lift'] = clock
                self.add_passenger(passenger)
            else:
                # lift must depart
                self.depart(clock)
                return

        if len(self.passengers) >= self.capacity_threshold*self.capacity:
            self.depart(clock)
            return

        # depart if waiting for too long
        if len(self.passengers) > 0:
            recent_p = max(self.passengers, key=lambda p: p['time.enter_lift'])
            waiting_time = clock - recent_p['time.enter_lift']
            if waiting_time > 10: # depart after 10 seconds of waiting
                self.depart(clock)

    def depart(self, clock):
        """Handles the departure of the lift."""
        # leaving lobby so cannot accept passengers
        self.available = False
        # inform onboard passengers of departure time
        for p in self.passengers:
            p['time.departure'] = clock
        # update trip times for all passengers and return RTT for lift
        self.rtt = self.update_trip_times(clock)
        # set when lift will next be available in the lobby
        self.arrival_time = math.ceil(clock + self.rtt)
        self.log("Lift {} is departing. RTT = {} ETA: {}".format(
                self.id, self.rtt, self.arrival_time))

    def check_arrival(self, current_time):
        if current_time == self.arrival_time:
            for p in self.passengers:
                p['time.arrival'] = current_time 
            completed_passengers = self.passengers.copy()
            self.passengers = [] # clear the passenger list
            self.available = True
            self.log("Lift {} has arrived back at lobby and available to use.".format(self.id))
            return completed_passengers
        else:
            return []
    
    def add_passenger(self, passenger):
        if len(self.passengers) < self.capacity and self.available:
            self.passengers.append(passenger)
            self.log("Lift {} just added passenger going to floor {}".format(self.id, passenger['destination']))
            return True
        else:
            return False

    def queue_passenger(self, passenger, clock):
        passenger['time.lobby'] = clock
        self.queue.append(passenger)
        self.log("A passenger is waiting to get into Lift {}".format(self.id))
        if len(self.queue) > 10:
            self.log("  ALERT > There are more than 10 people waiting to get in the lift")
