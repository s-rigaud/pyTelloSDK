"""
This module tends to allow user to take control of a TelloEDU drone

The _end_connection flag is raised when the ack is bad or when the drone is unreachable
"""

import sys
import socket
from time import sleep
from PIL import Image

from abstract_drone import *

class TelloEDU(AbstractDrone):
    """Class created to interact with the drone"""
    def __init__(self, tello_address=None, **kwargs):
        #Init the Abstract base class
        super().__init__(**kwargs)

        #If address isn't given
        if tello_address is None:
            connected_drones = self.get_all_drones()
            print(connected_drones)
            if connected_drones == []:
                sys.tracebacklimit = 0
                raise InterruptedError('You are not connected to any drone')
            tello_address = connected_drones[0]
            print('The connected Tello is the Tello with IP : ' + tello_address)

        self.tello_address = (tello_address, 8889)
        self._end_connection = self.test_drone_connection()
        if self.is_connected:
            print(self)
            self.init_drone_sockets()
            self.init_commands()

    def __repr__(self):
        return 'I am a Tello EDU drone, my IP@ is {}'.format(self.tello_address[0])

    def __len__(self):
        return int(self.is_connected)

    def init_commands(self):
        """"""
        self.send('command')
        #Enable front recognition for Mission Pads
        if self.front_mp:
            self.send('mon')
        #Enable video streaming
        if self.video_stream:
            self.send('streamon')

    def test_drone_connection(self):
        """
        Test if the drone is still connected
        Return True if the connection should end
        """
        connected = self.still_connected(self.tello_address[0])
        if not connected:
            print('Drone is not reachable')
        return not connected

    def send(self, message, index: int = 0):
        """Send message to drone using UDP Socket"""
        try:
            self.command_socket.sendto(message.encode(), self.tello_address)
        except (OSError, IndexError):
            self._end_connection = True
            print(f'{index}-Socket has already been closed')
        else:
            print(f'Drone {index} - Sending message: {message}')
            self.all_instructions.append(str(index) + '-' + message)
        finally:
            self._end_connection = self.test_drone_connection()

    def receive_ack(self):
        """Use UDP socket to receive ack from each command we sended"""
        while self.is_connected:
            try:
                response, _ = self.command_socket.recvfrom(2048)
                print(f'Received message : {response.decode("utf-8", "ignore")}')
            except (socket.timeout, ConnectionResetError, OSError):
                self._end_connection = True
                print('Drone is not reachable anymore')
        print('ack thread done')

    def receive_state(self, parameters):
        """Use UDP socket to receive all infos from the state channel"""
        sleep(2)
        while self.is_connected:
            try:
                last_state, _ = self.state_socket.recvfrom(2048)
                parameters = last_state.decode().split(';')[:-1]
                print(f'0-parameters : {parameters}')
                sleep(3)
            except Exception as exc:
                print(f'Error receiving: {exc}')
                print('Drone is not reachable anymore')

    def receive_frame(self):
        """
        Use UDP socket to receive the video stream
        The video stream can only be used when you are directly connected to the drone WIFI (manufacturer restrictions)
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

            except KeyboardInterrupt as exc:
                print(exc)
            except OSError:
                pass
        print('frame thread done')

if __name__ == '__main__':
    my_tello = TelloEDU('192.168.10.1', video_stream=True, state_listener=False, back_to_base=False)
    # my_tello.init_flight_mode('act from file', filename='mission_file_idle.txt')
    # my_tello.init_flight_mode('picture mission', object_distance=(0, 100), object_dim=(40, 40, 20))
    my_tello.init_flight_mode('open pipe')
    # my_tello.init_flight_mode('reactive')
    my_tello.start_mission()
