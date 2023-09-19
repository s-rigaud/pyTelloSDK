"""
This module tends to all ow user to take control of several TelloEDU drones
I want my two classes to be totally independant, as Swarm class can do all that TelloEDU
can do, the TelloEDU could be removed but just the name of 'swarm' for only one drone doesn't take sense so I don't want any links between them to prevent from deleting TelloEDU in the future
"""

import sys
import socket
from time import sleep
from PIL import Image

from abstract_drone import AbstractDrone, AV_AVAILABLE, LIB_AVAILABLE

class Swarm(AbstractDrone):
    """Class created to interact with the drone"""
    def __init__(self, tello_addresses=None, **kwargs: dict):
        #Init the Abstract base class
        super().__init__(**kwargs)

        #If address isn't given
        if tello_addresses is None:
            connected_drones = self.get_all_drones()
            if not connected_drones:
                sys.tracebacklimit = 0
                raise InterruptedError('You are not connected to any drone')
            tello_addresses = connected_drones
            print(f'The connected drones are tellos with IP : {tello_addresses}')

        # Easier to store adresses to iterate over
        self.tello_ip_addresses = tello_addresses
        #Store the last state for each drone
        self.last_parameters = [[] for _ in range(len(self))]

        self._end_connection = self.test_drone_connection()
        if self.is_connected:
            print(self)
            self.init_drone_sockets()
            self.init_commands()

    def __repr__(self):
        #Test for drones before displaying them
        if not self.tello_ip_addresses or self._end_connection:
            return 'I have currently 0 drone connected'

        result_string = '\nI am a Swarm of Tello EDU drone\n'
        for index, address in enumerate(self.tello_ip_addresses):
            result_string += f'\t{index} - Tello IP : ( {address} )\n'
        return result_string

    def __len__(self):
        return len(self.tello_ip_addresses)

    def init_commands(self):
        """Init drones' SDK """
        for index in range(len(self)):
            #Init connexion (SDK Mode)
            self.send('command', index)
            #Enable video streaming
            if self.video_stream:
                self.send('streamon', index)

    def test_drone_connection(self):
        """
        Test if the drones are still connected
        """
        for index, drone_ip in enumerate(self.tello_ip_addresses):
            if not self.still_connected(drone_ip):
                print(f'{drone_ip} is not reachable')
                del self.tello_ip_addresses[index]
                del self.last_parameters[index]
        return not self.tello_ip_addresses

    def send(self, message, index: int):
        """Send message to drone using UDP Socket"""
        try:
            self.command_socket.sendto(message.encode(), (self.tello_ip_addresses[index], 8889))
        except (OSError, IndexError):
            self._end_connection = True
            print(f'{index}-Socket has already been closed')
        else:
            print(f'Drone {index} - Sending message: {message}')
            self.all_instructions.append(f'{index}-{message}')
        finally:
            self.end_connection = self.test_drone_connection()

    def receive_ack(self):
        """Use UDP socket to receive ack from each command we sended"""
        while self.is_connected:
            try:
                response, ip_address = self.command_socket.recvfrom(2048)
                print(f'{self.tello_ip_addresses.index(ip_address[0])}-Received message : {response.decode("utf-8", "ignore")}')
            except (socket.timeout, OSError):
                self._end_connection = True
                self.test_drone_connection()
                print('Drone is not reachable anymore')
        # print('ack thread done')

    def receive_state(self, parameters: list):
        """Use UDP socket to receive all infos from the state channel"""
        sleep(2)
        while self.is_connected:
            try:
                last_state, ip_address = self.state_socket.recvfrom(2048)
                drone_index = self.tello_ip_addresses.index(ip_address[0])
                parameters[drone_index] = last_state.decode().split(';')[:-1]
                print(f'{drone_index}-parameters : {parameters[drone_index]}')
                sleep(3)
            except Exception as exc:
                print(f'Error receiving: {exc}')
                print('Drone is not reachable anymore')

    def receive_frame(self):
        """
        Use UDP socket to receive the video stream
        The video stream can only be used when you are directly connected to the drone WIFI (manufacturer restrictions)
        (Not really its place in swarm because you can only be connected to one drone WIFI at the same time so it makes
         swarm of only one drone)
        """
        print('If you are not directly connected to drone Wifi, Video Stream is impossible')
        all_data = b''
        sleep(4)
        while self.is_connected:
            try:
                rcv_bytes, _ = self.videostream_socket.recvfrom(2048)

                all_data += rcv_bytes
                self.video_frames.add_data(rcv_bytes)

                # If it's the ending frame of a picture
                if len(rcv_bytes) != 1460:
                    if LIB_AVAILABLE:
                        ## IMAGE PROCESSING | Input = h264
                        for frame in self.process_frame(all_data):
                            picture = Image.fromarray(frame)
                            self.last_frame = picture
                    if AV_AVAILABLE:
                        ## IMAGE PROCESSING | Input = h264
                        for frame in self.process_frame():
                            picture = Image.fromarray(frame)
                            self.last_frame = picture

                    all_data = b''
            except IndexError as exc:
                print(exc)
        print('frame thread done')

if __name__ == '__main__':
    my_swarm = Swarm(video_stream=True, state_listener=False, back_to_base=False)
    # my_swarm.init_flight_mode('act from file', filename='mission_file_idle.txt')
    # my_swarm.init_flight_mode('picture mission', object_distance=(0, 100), object_dim=(40, 40, 20))
    # my_swarm.init_flight_mode('open pipe')
    # my_swarm.init_flight_mode('act from list', actions=["0-takeoff", "1-takeoff", "0-ccw 50", "0-ccw 50", "0-land", "1-land"])
    my_swarm.init_flight_mode('reactive')
    my_swarm.start_mission()
