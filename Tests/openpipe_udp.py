import threading
import socket
from time import sleep

local_address_state = ('', 9000)
tello_address = ('192.168.10.1', 8889)

class Embedded_bool:
    def __init__(self, value):
        self.value = value
    def swap(self):
        self.value = not self.value

end_pg = Embedded_bool(False)


sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
sock.bind(local_address_state)

def send(message):
    """ Send bytes to tello drone using udp"""
    try:
        sock.sendto(message.encode(), tello_address)
        print(f"Sending message: {message}")
    except Exception as exc:
        print(f"Error sending: {str(exc)}")

def recv(end_pg):
    """ Receive the ack of each command sended """
    while not end_pg.value:
        try:
            data, _ = sock.recvfrom(1518)
            print(data.decode())
        except IndexError:
            print('\nExit . . .\n')
            break
        sleep(3)

ack_thread = threading.Thread(target=recv, args=(end_pg,))
ack_thread.start()

send("command")
sleep(1)
print('Enter exit to leave')
try:
    while True:
        user_command = input('Enter the command  : \n')
        if user_command == 'exit':
            sock.close()
            end_pg.swap()
            break
        send(user_command)
        sleep(2)
    print(end_pg.value)
except KeyboardInterrupt:
    end_pg.swap()

