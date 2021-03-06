import random
import select
import socket
import struct
import sys

from scapy.arch import get_if_addr

TIMEOUT = 10

BROADCAST_IP = "127.0.0.255"
BROADCAST_IP_ETH1_NETWORK = "172.1.255.255"
BROADCAST_IP_DEV_NETWORK = "172.18.255.255"  # Dev network
BROADCAST_IP_TEST_NETWORK = "172.99.255.255"  # Test network - only to be used when being graded
UDP_PORT = 13117  # Dedicated broadcast offer port
BROADCAST_ADDR = (BROADCAST_IP, UDP_PORT)
SERVER_IP = "127.0.0.1"  # Acquire local host IP address
SERVER_IP_ETH1_NETWORK = "172.1.0.90"
SERVER_IP_DEV_NETWORK = "172.18.0.92"  # Dev network
SERVER_IP_TEST_NETWORK = "172.99.0.90"  # Test network - only to be used when being graded
TCP_PORT = -1  # Server port, undefined at first
MIN_VALID_PORT = 0
MAX_VALID_PORT = 65535

PORT = random.randint(1024, 65535)  # The port from which the client will send out messages
HOST_IP = socket.gethostbyname(socket.gethostname())  # Acquire local host IP address

IP_INDEX = 0  # In an address tuple, the IP is the first element

MAGIC_COOKIE = 0xabcddcba  # All broadcast offer messages MUST begin with this prefix
MAGIC_COOKIE_START = 0  # The index in the offer announcement where the magic cookie starts
MAGIC_COOKIE_END = 4  # The index in the offer announcement where the magic cookie ends

MESSAGE_TYPE = 0x2  # Specifies broadcast offer, no other message types are supported
MESSAGE_TYPE_INDEX = 4  # The index in the offer announcement where the message type is

SERVER_PORT_START = 5  # The index in the offer announcement where the server port starts
SERVER_PORT_END = 7  # The index in the offer announcement where the server port ends

TEAM_NAME = b"Timeout tERRORs\n"

c_socket = None


# checks if the offer is a valid offer
def handle_offer(offer: bytes):
    global TCP_PORT
    try:
        message = struct.unpack('IBH', offer)
        if not message[0] == MAGIC_COOKIE:
            print(f"Offer doesn't start with magic cookie. Rejecting offer.")
            return False
        if not message[1] == MESSAGE_TYPE:
            print("Message type not support. Rejecting offer.")
            return False
        TCP_PORT = int(message[2])
        if TCP_PORT < MIN_VALID_PORT or TCP_PORT > MAX_VALID_PORT:
            print("Invalid port. Rejecting offer.")
            return False
    except struct.error or OverflowError or OSError as e:
        print(f"Cannot unpack message")
        return False
    return True


# function that handles the game logic and ends it gracefully after the game is over
def start_game(sock):
    terminate_game = False
    while not terminate_game:
        reads, _, _ = select.select([sock, sys.stdin], [], [], TIMEOUT)

        if sock in reads:  # received an answer from server i.e. the game is over, print message, close socket
            message = sock.recv(1024)
            print(message.decode())
            sock.close()
            terminate_game = True
        elif sys.stdin in reads:
            answer = sys.stdin.readline(1)
            sock.send(answer.encode())


def main():
    global c_socket
    global SERVER_IP
    print(f"Client started, listening for offer requests...")

    while True:
        # listen to UDP offers
        offer_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        offer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
        offer_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        offer_socket.bind(BROADCAST_ADDR)
        try:
            offer, server_address = offer_socket.recvfrom(8)
            SERVER_IP = server_address[IP_INDEX]
            offer_socket.close()
            # try to connect to server
            print(f"Received offer from {SERVER_IP}, attempting to connect...")
            result = handle_offer(offer)
            # if the offer is invalid then the client continues to look for other offers
            if not result:
                continue
        except socket.error:
            print("Cannot receive offer")
            continue

        # requesting a socket for tcp connection and setting it to false
        c_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:  # try to connect to server. will get excepted if server refused to establish connection
            c_socket.connect((SERVER_IP, TCP_PORT))
            # sends the server the client name
            c_socket.send(TEAM_NAME)
        except socket.error or OSError:  # handling the exception for not connecting to server
            c_socket.close()
            print("Server disconnected, listening for offer requests...")
            continue
        try:
            print(c_socket.recv(1024).decode())  # Wait until receiving welcome message and math problem and print it
        except socket.error as e:
            continue
        c_socket.setblocking(False)
        start_game(c_socket)
        print("Server disconnected, listening for offer requests...")


# configure to a different server address to try to connect to other servers
def configure_game(server_addr=BROADCAST_IP):
    global BROADCAST_ADDR
    global SERVER_IP
    if server_addr == "eth1":
        BROADCAST_ADDR = (BROADCAST_IP_ETH1_NETWORK, UDP_PORT)
        SERVER_IP = SERVER_IP_ETH1_NETWORK
    if server_addr == "eth0":
        BROADCAST_ADDR = (BROADCAST_IP_DEV_NETWORK, UDP_PORT)
        SERVER_IP = SERVER_IP_DEV_NETWORK
    elif server_addr == "test":
        BROADCAST_ADDR = (BROADCAST_IP_TEST_NETWORK, UDP_PORT)
        SERVER_IP = SERVER_IP_TEST_NETWORK


if __name__ == "__main__":
    if len(sys.argv) > 1:
        print(sys.argv[1])
        configure_game(sys.argv[1])
    try:
        main()
    except KeyboardInterrupt:
        print("Client stopped")
        if c_socket is not None:
            c_socket.close()
