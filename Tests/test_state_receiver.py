import socket
from time import sleep

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

local_address_state = ('', 8890)
tello_address = ('192.168.10.1', 8889)

sock.bind(local_address_state)

def send(message):
    """ Send bytes to tello drone using udp"""
    try:
        sock.sendto(message.encode(), tello_address)
        print(f"Sending message: {message}")
    except Exception as exc:
        print(f"Error sending: {str(exc)}")

def recv():
    """ Receive the ack of each command sended """
    while True:
        try:
            data, _ = sock.recvfrom(1518)
            print(data.decode())
        except IndexError:
            print('\nExit . . .\n')
            break
        sleep(3)

send("command")
sleep(3)

recv()
