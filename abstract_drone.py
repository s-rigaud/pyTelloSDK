"""Base Abstract Class for every other class of the API which allow user to connect to the drone"""

import os
import re
import socket
import platform
import ipaddress
from time import sleep
from threading import Thread
from abc import ABC, abstractmethod
from subprocess import Popen, PIPE
import numpy as np

from video_stream import VideoStream
from flight_modes import AbstractFlightMode, ActFromFileMode, ActFromActionListMode, ReactiveMode, OpenPipeMode, PictureMission

# All av related thing is just test compatibility for Windows

class NoVideoDecoderError(Exception):
    """Error when no decoder was found for h264 format"""
    def __init__(self, msg):
        super().__init__()
        self.msg = msg

    def __str__(self):
        return f'{self.__class__.__name__} :  {self.msg}'

    def __repr__(self):
        return self.__str__()

# By default use compiled library else py-av
try:
    import libh264decoder
    print('You have compiled the h264 library')
except ImportError:
    LIB_AVAILABLE = False
else:
    # Runtime optimisation variables
    DECODER = libh264decoder.H264Decoder()
    LIB_AVAILABLE = True

try:
    import av
    print('You have access to py-av library')
except ImportError:
    AV_AVAILABLE = False
else:
    AV_AVAILABLE = True

NO_VIDEO_DECODER = not LIB_AVAILABLE and not AV_AVAILABLE

class AbstractDrone(ABC):
    """
    Abstract base skeleton class for every other class interacting with the Tello
    """
    def __init__(self, **kwargs: dict):
        super().__init__()
        # Required variables in __del__
        self.command_socket = self.state_socket = self.videostream_socket = None
        self.state_thread = self.ack_thread = self.video_thread = None
        #Store all moves done by the drone to reverse them and allow drones to return to base
        self.all_instructions = []
        #Store the last state from the drone
        self.last_parameters = []

        self._end_connection = False

        self.local_address_command = ('', 9010)
        self.local_address_state = ('', 8890)
        self.local_address_video = ('', 11111)

        self.video_stream = kwargs.get('video_stream', False)
        self.state_listener = kwargs.get('state_listener', False)
        self.back_to_base = kwargs.get('back_to_base', False)

        self.flight_mode: AbstractFlightMode = None

        self.last_frame: bytes = None
        self.video_frames = VideoStream()
        self.av_target_opened = False

    def __del__(self):
        """Try to close all the sockets"""
        # print('Drone deletion')
        if self.all_instructions:
            print('Mission completed successfully!')

    @property
    def status(self):
        """Simple check of the state of the drone"""
        return f"({self.__class__.__name__}) : connected={self.is_connected}"


    @property
    def is_connected(self):
        """simple name convenience"""
        return not self._end_connection

    @property
    def end_connection(self):
        """Layer for protected member"""
        return self._end_connection

    @end_connection.setter
    def end_connection(self, value):
        """If the flag is raised, all sockets are being closed"""
        self._end_connection = value
        if value:
            if self.command_socket is not None:
                self.command_socket.close()
            if self.state_socket is not None:
                self.state_socket.close()
            if self.videostream_socket is not None:
                self.videostream_socket.close()

    @property
    def threads_alive(self):
        """Determine if some parallel threads are running"""
        existing_threads = [thread for thread in (self.video_thread, self.ack_thread, self.state_thread) if thread is not None]
        return len([thread for thread in existing_threads if thread.isAlive()])

    def init_drone_sockets(self):
        """Forced the drone to use SDK mode and enable its modules"""
        self.command_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.command_socket.bind(self.local_address_command)

        self.ack_thread = Thread(target=self.receive_ack)
        self.ack_thread.start()

        if self.state_listener:
            self.state_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.state_socket.bind(self.local_address_state)

            self.state_thread = Thread(target=self.receive_state, args=(self.last_parameters,))
            self.state_thread.start()

        if self.video_stream and (LIB_AVAILABLE or AV_AVAILABLE):
            self.videostream_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.videostream_socket.bind(self.local_address_video)
            self.videostream_socket.settimeout(6)

            self.video_thread = Thread(target=self.receive_frame)
            self.video_thread.start()

    @classmethod
    def still_connected(cls, device_ip: str):
        """
        Use ping and arp functions from OS to find if the device is accessible
        @IP and @Mac are tested
        """
        # 1 request / 2 jumps / 150 ms to respond
        if platform.system() == 'Windows':
            mac_adress_format = re.compile(r'((\d|([a-f]|[A-F])){2}-){5}(\d|([a-f]|[A-F])){2}')
            tello_builder_sign = '60-60-1f'
            toping = Popen(['ping', '-n', '1', '-w', '150', device_ip], stdout=PIPE)
        else:
            # Unix base systems
            mac_adress_format = re.compile(r'((\d|([a-f]|[A-F])){2}:){5}(\d|([a-f]|[A-F])){2}')
            tello_builder_sign = '60:60:1f'
            toping = Popen(['ping', '-c', '1', '-W', '1', device_ip], stdout=PIPE)

        output = toping.communicate()[0]
        #Reverse 1 to 0 and 0 to 1    (exit(0) needs to represent True)
        if not 1 - toping.returncode:
            return False

        # If a device is connected with the corresponding IP ...
        arp_request = Popen(['arp', '-a'], stdout=PIPE)
        output = arp_request.communicate()[0].decode("utf-8", "ignore")
        for line in output.split('\n'):
            if device_ip in line:
                match = re.search(mac_adress_format, line)
                if not match:
                    continue
                arp = str(match.group())
                # @Mac builder address of Tello
                return arp.startswith(tello_builder_sign)
        return False

    @classmethod
    def get_all_drones(cls):
        """
        Return the IP of drones connected to the routers connected to the computer
        Pinging refresh the ARP table for each connection tested
        """
        print("You didn't give any IP address")
        ip_adress_format = re.compile(r'\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3}')
        all_interfaces = set()

        if platform.system() == 'Windows':
            mac_adress_format = re.compile(r'((\d|([a-f]|[A-F])){2}-){5}(\d|([a-f]|[A-F])){2}')
            tello_builder_sign = '60-60-1f'
            #Get all interfaces
            arp_request = Popen(['arp', '-a'], stdout=PIPE)
            output = arp_request.communicate()[0].decode('utf-8', 'ignore')
            for line in output.split('\n'):
                if '---' in line:
                    all_interfaces.add(line.split(' ')[1])
        else:
            # Unix based system
            mac_adress_format = re.compile(r'((\d|([a-f]|[A-F])){2}:){5}(\d|([a-f]|[A-F])){2}')
            tello_builder_sign = '60:60:1f'
            #Get all interfaces
            ipconfig_request = Popen(['/sbin/ifconfig', '-a'], stdout=PIPE)
            output = ipconfig_request.communicate()[0].decode('utf-8', 'ignore')
            for line in output.split('\n'):
                match = re.search(ip_adress_format, line)
                if match:
                    network_adr = ipaddress.ip_interface(str(match.group()))
                    all_interfaces.add(str(network_adr.network).split('/')[0])
        print(f'All interfaces detected are : {list(all_interfaces)}')

        def test_ip(ip_list: list):
            """ Ping a range of IP / Refresh ARP """
            # print(ip_list[0], ip_list[-1])
            if platform.system() == 'Windows':
                for ip in ip_list:
                    # Only 1 ping / Wait 200ms for response
                    toping = Popen(['ping', '-n', '1', '-w', '200', str(ip)], stdout=PIPE)
                    _ = toping.communicate()[0]
                    # print(ip)
            else:
                for ip in ip_list:
                    toping = Popen(['ping', '-c', '1', '-W', '1', str(ip)], stdout=PIPE)
                    _ = toping.communicate()[0]
                    # print(ip)

        print('Automatically searching for drones .....')
        #Ping everything
        thread_list = []
        for interface in all_interfaces:
            ip_net = ipaddress.ip_network(f'{interface}/24', strict=False)
            all_ip = list(ip_net.hosts())
            # Creating 16 threads
            ip_range = 16
            for i in range(ip_range):
                #Using Multi-Threading to complete a 80s task in only 15s
                thread_list.append(Thread(target=test_ip, args=(all_ip[ip_range*i: ip_range*(i+1)],)))
                thread_list[i].start()
        for thread in thread_list:
            thread.join()

        #Get all drone ips
        list_ip_drones = []
        arp_request = Popen(['arp', '-a'], stdout=PIPE)
        output = arp_request.communicate()[0].decode('utf-8', 'ignore')
        for line in output.split('\n'):
            #Continue if there is no Mac@ in the line
            match = re.search(mac_adress_format, line)
            if not match:
                continue
            arp = str(match.group())
            if arp.startswith(tello_builder_sign):
                list_ip_drones.append(str(re.search(ip_adress_format, line).group()))
        return list_ip_drones


    def init_flight_mode(self, flight_mode: str, **options: dict):
        """Main method implementing the strategy pattern"""
        if not self.is_connected:
            return
        flight_mode = flight_mode.lower().strip()
        if flight_mode == 'act from file':
            if options.get('filename') is None:
                self.end_connection = True
                raise TypeError("You forgot filename argument. \nSee : https://github.com/s-rigaud/dev-pyTelloSDK#flightmodes for help")
            else:
                self.flight_mode = ActFromFileMode(self, **options)

        elif flight_mode == 'act from list':
            if options.get('actions') is None:
                self.end_connection = True
                raise TypeError("You forgot actions argument. \nSee : https://github.com/s-rigaud/dev-pyTelloSDK#flightmodes for help")
            self.flight_mode = ActFromActionListMode(self, **options)

        elif flight_mode == 'open pipe':
            self.flight_mode = OpenPipeMode(self)

        elif flight_mode == 'picture mission':
            if NO_VIDEO_DECODER:
                raise NoVideoDecoderError("Be sure you have access to either av library or libh264decoder")
            self.flight_mode = PictureMission(self, **options)
        elif flight_mode == 'reactive':
            self.flight_mode = ReactiveMode(self)

        else:
            print('You enter an unrecognize flight mode')
            self.end_connection = True

    def start_mission(self):
        """Launch function for the strategy (flight mode)"""
        if self.is_connected:
            if self.flight_mode is not None:
                self.flight_mode.start()
            else:
                print('flight mode was not initialised')

    def take_picture(self):
        """Add a picture to the attribute"""
        return self.last_frame

    @classmethod
    def save_pictures(cls, picture_list: list):
        """Saved all given pictures to the dedicated folder"""
        dir_path = os.path.dirname(os.path.realpath(__file__))
        dir_picture = os.path.sep.join((dir_path, 'pictures'))
        if not os.path.exists(dir_picture):
            os.makedirs(dir_picture)
            print(picture_list)

        for index, image in enumerate(picture_list):
            if image is not None:
                picture_path = os.path.sep.join((dir_picture, f'test-{index}.jpg'))
                image.save(picture_path)
            else:
                print('One of the saved picture was empty')

    def execute_actions(self, actions: list):
        """ Execute all actions """
        action_index = 0
        # While the drone is connected
        while self.is_connected and action_index < len(actions):
            action_to_do = actions[action_index]
            #Test if there is no drone index in the command
            try:
                index = int(action_to_do.split('-')[0])
                if index < len(self):
                    action_to_do = action_to_do[len(str(index))+1:]
                else:
                    print(f'index : {index} is too big.')
            except ValueError:
                # If no index is specified
                index = 0

            self.send(action_to_do, index)
            action_index += 1
            # Don't wait if there is no actions left
            if action_index < len(actions):
                sleep(3)

    def process_frame(self, data: bytes = None):
        """Tranform h264 Images to RGB """
        res_frame_list = []
        if not LIB_AVAILABLE and not AV_AVAILABLE:
            print('Libh264decoder unavailable')
            # Throw explicit error

        else:
            if LIB_AVAILABLE:
                frames = DECODER.decode(data)
            else:
                if not self.av_target_opened:
                    print('\nquarter\n')
                    container = av.open(self.video_frames, mode='r', format='h264')
                    self.av_target_opened = True
                frames = container.decode(video=0)
                print(len(frames))
            for framedata in frames:
                (frame, width, height, row_size) = framedata
                if frame is not None:
                    frame = np.fromstring(frame, dtype=np.ubyte, count=len(frame), sep='')
                    frame = (frame.reshape((height, int(row_size / 3), 3)))
                    frame = frame[:, :width, :]
                    res_frame_list.append(frame)
        return res_frame_list

    @abstractmethod
    def test_drone_connection(self):
        """Abstract method which should be used to test if the drone is still connected"""

    @abstractmethod
    def send(self, message, index: int):
        """Abstract method which should be used to send command to the drone"""

    @abstractmethod
    def receive_ack(self):
        """Abstract method which should be used to 'ack' response for every command sended to the drone"""

    @abstractmethod
    def receive_state(self, parameters):
        """Abstract method which should be used to receive state sended by the drone"""

    @abstractmethod
    def receive_frame(self):
        """Abstract method which should be used to receive frames sended by the drone"""
