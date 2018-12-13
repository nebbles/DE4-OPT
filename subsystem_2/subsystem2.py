import copy
import math
from pprint import pprint
from timeit import default_timer as timer

import numpy as np


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
        self.loc_history = [(0,0)]

        self.history = {
            'queue_length':[]
        }

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
            div = total // self.capacity # calculate remainder
            # relevant passengers to caller
            relevant_ps = running_order[div*self.capacity:]
            if len(relevant_ps) == 0:
                return 0  # avg floor is irrelevant to the caller
            else:
                return sum([p['destination'] for p in relevant_ps])/len(relevant_ps) # average

    def get_ett(self, passenger):
        running_order = self.passengers + self.queue
        total = len(running_order)
        if total == 0:
            flrs = [0, passenger['destination']]
            return self.comp_travel(flrs)[-1]
        
        div = total // self.capacity  # calculate remainder
        relevant_ps = running_order[div*self.capacity:]  # relevant passengers to caller

        if len(relevant_ps) > 0:
            ds = [p['destination'] for p in relevant_ps if p['destination'] < passenger['destination']]
            flrs = [0]+ds+[passenger['destination']]
            return self.comp_travel(flrs)[-1]
        
        else:
            flrs = [0, passenger['destination']]
            return self.comp_travel(flrs)[-1]

    def get_ewt(self):
        running_order = self.passengers + self.queue
        total = len(running_order)
        if total == 0:
            return 0

        div = total // self.capacity  # calculate remainder
        # relevant passengers to caller
        relevant_ps = running_order[:div*self.capacity]

        if len(relevant_ps) > 0:
            # print("relevant p ")
            # pprint(relevant_ps)
            total_wt = 0
            # split into capacity size chunks and compute waiting time via rtt
            for i in range(0, len(relevant_ps), self.capacity):
                subgroup = relevant_ps[i:i + self.capacity]
                sgds = [p['destination'] for p in subgroup] # subgroup destinations
                wt = self.comp_travel([0]+sgds+[0])[-1]
                total_wt += wt

            return total_wt

        else:
            return 0

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

        floors.sort()
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

        self.loc_history.append((clock, 0))

        # move to each floor
        for p in self.passengers:
            n = p['destination']
            time += self.travel_time(n-prev_n)
            p['time.travelling'] = time
            self.passenger_travel_times.append(time)
            self.loc_history.append((time+clock, n))
            prev_n = n
        
        # return to ground
        n = 0
        time += self.travel_time(abs(0-prev_n))
        self.loc_history.append((time+clock, n))
        
        return time # RTT

    def update(self):
        self.history['queue_length'].append(len(self.queue))
    
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
        passenger['lift.id'] = self.id
        self.queue.append(passenger)
        self.log("A passenger is waiting to get into Lift {}".format(self.id))
        if len(self.queue) > 10:
            self.log("  ALERT > There are more than 10 people waiting to get in the lift")


class Simulation:
    def __init__(self, id_n, iterations=60*60):
        self.id = id_n
        self.iterations = iterations
        self.clock = 0
        self.number_of_lifts = 8
        self.lift_capacity = 10
        self.departure_capacity_threshold = 0.8

        self.traffic = None
        self.assignment_func = None
        self.arrivals = []
        self.q = []
        self.lifts = []
        self.assignment_times = []
        for i in range(self.number_of_lifts):
            self.lifts.append(Lift(id=i,
                                   capacity=self.lift_capacity,
                                   capacity_threshold=self.departure_capacity_threshold))

        for lift in self.lifts:
            lift.set_print(False)

    def set_traffic(self, t):
        self.total_traffic = len(t)
        self.traffic = copy.deepcopy(t)

    def set_assignment_func(self, name):
        self.func_name = name
        if name == 'greedy':
            self.assignment_func = self.assign_greedy
        elif name == 'nearest':
            self.assignment_func = self.assign_nearest_lift
        elif name == 'grouping':
            self.assignment_func = self.assign_grouping
        elif name == 'random':
            self.assignment_func = self.assign_random
        elif name == 'journey':
            self.assignment_func = self.assign_journeytime
        elif name == 'adv grp':
            self.assignment_func = self.assign_grouping_advanced
        else:
            raise ValueError(
                'The assignment func name \'{}\' is not recognised.'.format(name))

    def assign_greedy(self, passenger):
        # assign to the shortest lift queue
        lifts_by_queue_length = sorted(
            self.lifts, key=lambda lift: lift.get_queue_length())
        lifts_by_queue_length[0].queue_passenger(passenger, self.clock)

    def assign_nearest_lift(self, passenger):
        # assign to the queue of nearest lift unless the queue has reached capacity
        lifts_by_proximity = sorted(
            self.lifts, key=lambda lift: lift.get_arrival_time())
        for lift in lifts_by_proximity:
            if lift.get_queue_length() < lift.capacity:
                lift.queue_passenger(passenger, self.clock)
                return

        # all lift queues are at least as long as lift capacity
        self.assign_greedy(passenger)

    def assign_grouping(self, passenger):
        # order lifts by the average destination floor of each lift

        # establish lifts that will have no other passengers yet
        empty_lifts = [l for l in self.lifts if l.get_avg_floor() == 0]

        # order lifts by the distance between passenger destination floor
        # and average destination floor of each lift
        lbnaf = sorted(self.lifts, key=lambda lift: abs(
            lift.get_avg_floor()-passenger['destination']))

        # best case, there is empty lift to fall back on
        if len(empty_lifts) > 0:
            if abs(lbnaf[0].get_avg_floor()-passenger['destination']) < 5:
                # if best lift is within a 5 floor threshold, then add the passenger
                lbnaf[0].queue_passenger(passenger, self.clock)
                return
            else:
                # revert to just assigning them to their own lift
                empty_lifts[0].queue_passenger(passenger, self.clock)
                return

        # no free lifts, so we put them in the most suitable one
        else:
            lbnaf[0].queue_passenger(passenger, self.clock)
            return

    def assign_random(self, passenger):
        # assign to a random lift
        r = np.random.randint(0, self.number_of_lifts)
        self.lifts[r].queue_passenger(passenger, self.clock)

    def assign_journeytime(self, passenger):
        # for each lift
        # for lift in self.lifts:
            # lift.get_eet(passenger)
            # print(lift.get_ewt())
        # calculate the expected travel time
        # calculate the expected wait time

        lifts_ett = sorted(self.lifts, key=lambda l: l.get_ett(passenger)+l.get_ewt())
        lifts_ett[0].queue_passenger(passenger, self.clock)

        # print(self.lifts[0].get_ett(passenger))
        # self.assign_grouping(passenger)
        
    def assign_grouping_advanced(self, passenger):
        # order lifts by the average destination floor of each lift

        t1 = [l for l in self.lifts if len(l.passengers) < l.capacity]
        t2 = [l for l in self.lifts if len(l.passengers)+len(l.queue) < 2*l.capacity]

        for lift in t1:
            avg = lift.get_avg_floor()
            if abs(avg-passenger['destination']) < 5:
                lift.queue_passenger(passenger, self.clock)
                return
            if  avg == 0:
                lift.queue_passenger(passenger, self.clock)
                return

        for l in t2:
            avg = l.get_avg_floor()
            if abs(avg-passenger['destination']) < 5:
                l.queue_passenger(passenger, self.clock)
                return
            if len(l.passengers)+len(l.queue) <= l.capacity:
                l.queue_passenger(passenger, self.clock)
                return
        
        # fallback
        shortest_queue = sorted(self.lifts, key=lambda l: len(l.passengers)+len(l.queue))[0]
        shortest_queue.queue_passenger(passenger, self.clock)

    def test(self):
        print("test func")

    def run(self):
        if self.traffic is None:
            raise TypeError(
                'Traffic variable has not been set for the simulation.')
        if self.assignment_func is None:
            raise TypeError(
                'Assignment function has not been set for the simulation.')

        while self.clock < self.iterations:
            self.step()

            if len(self.arrivals) == self.total_traffic:
                print("All traffic has arrived. Ending simulation early.")
                break

        message = []
        message.append("SIMULATION COMPLETE")
        message.append("Assignment function:      {}".format(self.func_name))
        message.append("Duration of simulation:   {}".format(self.clock))
        message.append("Maximum duration allowed: {}".format(self.iterations))
        message.append("Total passengers arrived: {}".format(len(self.arrivals)))
        message.append("Total traffic:            {} (+{})".format(self.total_traffic,
                                                                   self.total_traffic-len(self.arrivals)))
        message.append("Percentage processed:     {:2.0f}%".format(
            len(self.arrivals)/self.total_traffic*100))

        lline = len(max(message, key=lambda l: len(l)))
        print("┌"+"─" * (lline+2) + "┐")
        for line in message:
            print("│ "+line.ljust(lline)+" │")
        print("└"+"─" * (lline+2) + "┘")

    def step(self):
        # NEW ARRIVALS
        # move new arrivals from traffic into the queue
        while len(self.traffic) > 0:
            user = self.traffic[0]
            if user['time.start'] > self.clock:
                break  # user has not arrived at building yet
            else:
                # user has arrived at the building
                self.q.append(self.traffic.pop(0))

        # ASSIGNMENT ALGORITHM
        # Assign each person in the queue according to limits
        # 2 to 4 people per second can be allocated a lift
        for _ in range(np.random.randint(2, 5)):
            if len(self.q) > 0:
                waiting_passenger = self.q.pop(0)  # remove from the queue
                start = timer()
                self.assignment_func(waiting_passenger)  # assign passenger
                end = timer()
                self.assignment_times.append(end-start)
            else:
                break

        # UPDATE THE LIFT STATES
        # Check departure/arrival for all lifts

        for lift in self.lifts:
            lift.update()
            if lift.is_available():
                lift.check_departure(self.clock)
            else:
                self.arrivals += lift.check_arrival(self.clock)

        # ITERATE THE CLOCK
        self.clock += 1

        # LIVE GRAPH
        # ax1.clear()
        # ax1.bar(range(5), [lift.get_total_passengers() for lift in lifts])
        # ax1.set_title('Passenger count')
        # ax1.set_ylim(0,10)
        # fig.canvas.draw()
        # time.sleep(0.01)
