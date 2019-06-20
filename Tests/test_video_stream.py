import threading
import socket
from time import sleep

# Create a UDP socket
sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)

local_address_stream = ('', 11111)
tello_address = ('192.168.10.1', 8889)

sock.bind(local_address_stream)

def send(message):
  try:
    sock.sendto(message.encode(), tello_address)
    print("Sending message: " + message)
  except Exception as e:
    print("Error sending: " + str(e))

def recv():
    while True:
        try:
            data, server = sock.recvfrom(1518)
            ### IMAGE PROCESSING
            ## OUTPUT = h264
            ## CONVERT TO RGB or YCbCr
            print(data)

        except IndexError:
            print ('\nExit . . .\n')
            break
        sleep(3)

send("command")
sleep(3)
send("streamon")
sleep(3)

recv()


