import threading
import socket
from time import sleep
from subprocess import Popen, PIPE

local_address_state = ('', 9000)
tello_address = ('192.168.10.1', 8889)

sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(local_address_state)

def drone_is_connected(address):
    """
    Use ping and arp functions from OS to find if the device is accessible
    @IP and @Mac are tested
    """
    # 1 request / 2 jumps / 500 ms to respond
    toping = Popen(['ping', '-n', '1', '-w', '500', address], stdout=PIPE)
    output = toping.communicate()[0]
    #Reverse 1 to 0 and 0 to 1    (exit(0) needs to represent True)
    if not 1 - toping.returncode:
        return False
    # If a device is connected with the corresponding IP ...
    arp_request = Popen(['arp', '-a'], stdout=PIPE)
    output = arp_request.communicate()[0].decode("utf-8", "ignore")

    for line in output.split('\n'):
        if address in line:
            arp = line.split('     ')[2]
            # @Mac builder address of Tello
            return arp.startswith('60-60-1f')
    return False

def send(message):
    """ Send bytes to tello drone using udp"""
    try:
        sock.sendto(message.encode(), tello_address)
        print(f"Sending message: {message}")
    except Exception as exc:
        print(f"Error sending: {str(exc)}")

def recv(drone_connected: bool):
    """ Receive the ack of each command sended """
    while drone_connected:
        try:
            data, _ = sock.recvfrom(1518)
            print(data.decode())
        except IndexError:
            print('\nExit . . .\n')
            break
        sleep(3)
    sock.close()

drone_isalive = drone_is_connected(tello_address[0])

ack_thread = threading.Thread(target=recv, args=(drone_isalive,))
ack_thread.start()

send("command")
sleep(1)

while drone_isalive:
    user_command = input('Enter the command  : \n')
    send(user_command)
    sleep(2)
    drone_isalive = drone_is_connected(tello_address[0])
print('Drone is disconnected')
