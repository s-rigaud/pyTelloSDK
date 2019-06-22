"""
This file contains all the possible flight modes you can use to take control of the drone or making it executes missions
"""

import os
from abc import ABC, abstractmethod
from getch import getch
from time import sleep
from math import sqrt, ceil, cos, sin, radians

from toolbox import back_to_base, command_from_key

__all__ = ['OpenPipeMode', 'ReactiveMode', 'ActFromFileMode', 'ActFromActionListMode', 'PictureMission']

class AbstractFlightMode(ABC):
    """ Abstract Base Class of the Strategy Pattern to create other flight modes """
    def __init__(self, swarm):
        super().__init__()
        self.swarm = swarm
        self.all_images = []

    @abstractmethod
    def start(self, **options):
        """Base abstract method which hould be overwritted to implement behaviour"""

class ReactiveMode(AbstractFlightMode):
    """Fast reacting mode with pre-binded keys"""
    def __init__(self, swarm, **options):
        super().__init__(swarm)
        self.start(**options)

    @back_to_base
    def start(self, **options):
        """
        On Windows getch() capture two 'keys' and first one is useless
        On Unix special keys need 3 getch (Even arrows on Linux don't give the same keycode as Windows)
        See : https://en.wikipedia.org/wiki/ANSI_escape_code
        """
        # Ctrl + Z and Ctrl + C
        exit_char = ['\x1a', '\x03']
        while self.swarm.is_connected:
            _input = getch()
            try:
                # Type conversion required on Windows
                _input = _input.decode()
            except AttributeError:
                pass

            if _input in exit_char:
                for index in range(len(self.swarm)):
                    self.swarm.execute_actions([f'{index}-land'])
                self.swarm.end_connection = True
                self.swarm.command_socket.close()
                break
            # Useless escape chars
            elif _input in ['[', '\x1b']:
                continue
            elif _input == 'p':
                picture = self.swarm.take_picture()
                self.all_images.append(picture)
            elif command_from_key(_input) is not None:
                for index in range(len(self.swarm)):
                    self.swarm.execute_actions([f'{index}-{command_from_key(_input)}'])
            else:
                print('Nothing attach to this key ' + _input)

        self.swarm.save_pictures(self.all_images)

class OpenPipeMode(AbstractFlightMode):
    """Constant opened pipto communicate with the drone"""
    def __init__(self, swarm, **options):
        super().__init__(swarm)
        self.start(**options)

    @back_to_base
    def start(self, **options):
        """Allow user to send command specifing drone command and drone id"""
        user_command = ''
        print('You are using open pipe modee, enter exit to leave')
        try :
            #While last command wasn't land / flag isn't raised / at least one drone is connected
            while self.swarm.is_connected:
                try:
                    user_input = input('Enter the the index of the drone followed by command as "0-takeoff" or "1-cw 90" \n')
                except KeyboardInterrupt :
                    # Prevent from socket being still alived at the end of the programm
                    break
                # print(f'user input "{user_input}"')
                if user_input == 'exit':
                    break
                elif user_input == 'p':
                    picture = self.swarm.take_picture()
                    self.all_images.append(picture)
                elif user_input: # user_input != ""
                    self.swarm.execute_actions([user_input])

            self.swarm.save_pictures(self.all_images)
        except EOFError:
            print('User wants to disconnect')

class ActFromFileMode(AbstractFlightMode):
    """Read the whole content of a file an execute all actions contained in it"""
    def __init__(self, swarm, **options):
        super().__init__(swarm)
        self.start(**options)

    @back_to_base
    def start(self, **options):
        """Read file and execute actions"""
        filename = options.get('filename')
        project_path = os.path.dirname(os.path.realpath(__file__))
        dir_path = os.path.sep.join((project_path, 'missions_dir'))
        path = os.path.sep.join((dir_path, filename))
        try:
            with open(path, 'r') as file:
                content = file.read()
                actions = content.split('\n')
                self.swarm.execute_actions(actions)
        except FileNotFoundError:
            print(f'There is no file at {path}')

class ActFromActionListMode(AbstractFlightMode):
    """Excute a list of instructions"""
    def __init__(self, swarm, **options):
        super().__init__(swarm)
        self.start(**options)

    @back_to_base
    def start(self, **options):
        actions = options.get('actions')
        self.swarm.execute_actions(actions)

class PictureMission(AbstractFlightMode):
    """🐧 Mode used for photogrametry purpose"""
    def __init__(self, swarm, **options):
        """
         :params: object_position is a tuple (x,y)
         :params: object_dim is a tuple of the size (length, width, heigth)
        """
        super().__init__(swarm)

        if not self.swarm.video_stream:
            print('You forgot to activate video stream on the drone')
            self.swarm.end_connection = True
        self.start(**options)

    @back_to_base
    def start(self, **options):
        """Need to be tested

        Object coordinates :
                length
              ←────────→
            ↑ ┌────────┐
            │ │        │
    width   │ │        │
            │ │        │
            ↓ └────────┼→ x
                       ↓
                       y
        """
        object_distance = options.get('object_distance')
        object_dim = options.get('object_dim')
        if object_distance is None or object_dim is None:
            print('Please give object distance and dimensions')
            return
        center, pos = self.get_in_front(object_distance, object_dim)
        self.move_around(center, pos, object_dim)

    def get_in_front(self, object_distance: tuple, object_dim: tuple):
        """Move the drone just in front of the object"""
        x, y = object_distance
        length, width, _ = object_dim

        radius = sqrt(length**2 + width**2)/2
        center = (x - ceil(length/2), y + ceil(width/2))
        print(f'center {center}')

        x_pos = center[0] # - half drone width

        # +/- marge
        if center[1] >= 0:
            y_pos = int(center[1] - radius - width)
        else:
            y_pos = int(center[1] + radius + width)
        print(f'In front coords : {x_pos},{y_pos}')

        return (center, (x_pos, y_pos))

    def take_ground_angle_picture(self, hight: int):
        """Set of instructions to land the drone, take a picture and takeoff again"""
        self.swarm.execute_actions(['0-land'])
        sleep(3)
        self.all_images.append(self.swarm.take_picture())
        self.swarm.execute_actions(['0-takeoff'])
        sleep(3)
        if hight > 100:
            self.swarm.execute_actions([f'0-up {hight-100}'])
        else:
            self.swarm.execute_actions([f'0-down {100-hight}'])
        sleep(3)

    def move_around(self, center: tuple, actual_pos: tuple, object_dim: tuple):
        """Navigate in circle around the object (+up/down)"""

        x, y = actual_pos
        heigth = object_dim[2]

        actual_heigth = 10
        circle_radius_coef = 1.2

        number_of_points = 8
        theta = 360/number_of_points

        next_x = int((center[0] + (x - center[0])*cos(radians(theta)) - (y - center[1])*sin(radians(theta))))
        next_y = int((center[1] + (y - center[1])*cos(radians(theta)) - (x - center[0])*sin(radians(theta))))

        x_mvmt = (next_x - x) * circle_radius_coef
        y_mvmt = (next_y - y) * circle_radius_coef

        self.swarm.execute_actions(['0-takeoff'])
        sleep(3)
        self.swarm.execute_actions(['0-down 50'])
        sleep(2)

        # Get in front
        self.swarm.execute_actions([f'0-forward {y}'])
        sleep(3)
        if x > 0:
            self.swarm.execute_actions([f'0-right {x}'])
        else:
            self.swarm.execute_actions([f'0-left {abs(x)}'])
        sleep(5)

        while actual_heigth < heigth:
            for _ in range(number_of_points):
                # Only the first time
                # ERROR
                self.take_ground_angle_picture(actual_heigth)
                self.all_images.append(self.swarm.take_picture())
                self.swarm.execute_actions([f'0-right {x_mvmt}'])
                sleep(3)
                self.swarm.execute_actions([f'0-forward {y_mvmt}'])
                sleep(3)
                self.swarm.execute_actions([f'0-ccw {theta}'])
                sleep(3)
            actual_heigth += 20
            self.swarm.execute_actions([f'0-up {20}'])
            sleep(3)

        self.swarm.execute_actions(['0-land'])
        print(len(self.all_images))
        self.swarm.save_pictures(self.all_images)
