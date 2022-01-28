#!/usr/bin/python
from PyQt5.QtWidgets import *
from PyQt5 import uic
from datetime import datetime
import sys
import os
import threading
from time import sleep
from struct import *
from random import *
import socket

# Globals
INTERVAL_TIME = 3  # Send packet every INTERVAL_TIME seconds
# Buffer Size
BUFFER_SIZE = 4096

PORT = 50000
BOARD_ADDRESS = '192.168.1.111'

s_socket = ""

# Protocol ID
ID_UART = 1
ID_I2C = 2
ID_SPI = 3
# 4 Bytes of data (integer)
SIZE_OF_DATA = 4

# For storing data (that we send to the board)
mem_dict = {}


class MyGUI(QMainWindow):
    is_pause = False
    user_protocol = ""

    def __init__(self):
        super(MyGUI, self).__init__()
        uic.loadUi("myGUI.ui", self)
        self.show()
        self.btn_pause.clicked.connect(self.run_state)
        self.uart_btn.clicked.connect(self.set_uart)
        self.i2c_btn.clicked.connect(self.set_i2c)
        self.spi_btn.clicked.connect(self.set_spi)
        self.manage_threads()

    def run_state(self):
        btn_current_state = self.btn_pause.text()
        if btn_current_state == "Pause":
            self.btn_pause.setText("Resume")
        else:
            self.btn_pause.setText("Pause")
        self.is_pause = not self.is_pause

    def set_uart(self):
        self.user_protocol = 1

    def set_i2c(self):
        self.user_protocol = 2

    def set_spi(self):
        self.user_protocol = 3

    def as_server_thread(self):
        try:
            # Messages counter
            message_counter = 0
            while True:
                if not self.is_pause:
                    # Generate random number
                    rand_num = randint(1000, 9999)
                    make_str = str(rand_num)
                    make_bytes_stream = bytes(make_str, 'utf-8')

                    if self.user_protocol == "":
                        # Generate random protocol
                        #rand_protocol = randint(1, 3)
                        rand_protocol = 1
                        sending_protocol = ID_SPI
                        protocol_name = " SPI "
                        if rand_protocol == 1:
                            sending_protocol = ID_UART
                            protocol_name = " UART "
                        elif rand_protocol == 2:
                            sending_protocol = ID_I2C
                            protocol_name = " I2C "
                    else:
                        # Generate user protocol
                        if self.user_protocol == 2:
                            sending_protocol = ID_UART
                            protocol_name = " UART "
                        elif self.user_protocol == 2:
                            sending_protocol = ID_I2C
                            protocol_name = " I2C "
                        else:
                            sending_protocol = ID_SPI
                            protocol_name = " SPI "

                    # Get current time
                    now = datetime.now()
                    current_time = now.strftime("%H:%M:%S")

                    # H-(data size)2 bytes of data, B-(data id)1 byte of data,
                    # B-(unused-spare) 1 byte of data => i used it as a reference index to list, I-(data)4 bytes of data
                    packed_data = pack('H2B4s', SIZE_OF_DATA, sending_protocol, message_counter,
                                       make_bytes_stream)  # Packed data

                    # Saving packet reference
                    mem_dict[message_counter] = rand_num

                    # Send the packet
                    s_socket.sendto(packed_data, (BOARD_ADDRESS, PORT))
                    message = ": UDP packet sent: ID:%d, Protocol-type:%s, Data content: %s\n" \
                              % (message_counter, protocol_name, rand_num)

                    message_counter = message_counter + 1

                    self.text_area.insertPlainText("[" + current_time + "]" + message)
                    self.update()

                    self.user_protocol = ""
                    sleep(INTERVAL_TIME)  # Sleep INTERVAL_TIME between each sending
        except:
            print("Unexpected error while sending UDP packet to Board: ", sys.exc_info()[0])
            s_socket.close()
            sys.exit()

    def as_client_thread(self):
        try:
            while True:
                # Getting data from board
                data = s_socket.recvfrom(BUFFER_SIZE)
                if data:
                    now = datetime.now()
                    current_time = now.strftime("%H:%M:%S")
                    print(data)
                    unpacked_data = unpack('H2B4s', data[0])

                    # Convert data back from bytes to integer
                    make_string_from_byte_stream = unpacked_data[3].decode('utf-8')
                    extract_num = int(make_string_from_byte_stream)

                    get_dict_value = mem_dict[unpacked_data[2]]

                    protocol_name = " SPI "
                    if unpacked_data[1] == 1:
                        protocol_name = " UART "
                    elif unpacked_data[1] == 2:
                        protocol_name = " I2C "

                    # Check if data contents are ok
                    message = ""
                    if get_dict_value == extract_num:
                        message = ": UDP packet received: ID:%d, Protocol-type:%s, Data content: %d\n" \
                                  "Data successfully received\n" \
                                  % (unpacked_data[2], protocol_name, extract_num)
                    else:
                        message = ": UDP packet received: ID:%d, Protocol-type:%s, Data content: %d\n" \
                                  "Data unsuccessfully received\n" \
                                  % (unpacked_data[2], protocol_name, extract_num)

                    self.text_area_rev.insertPlainText("[" + current_time + "]" + message)
                    self.update()


        except:
            print("Unexpected error while receiving UDP packet to PC: ", sys.exc_info()[0])
            s_socket.close()
            sys.exit()

    def manage_threads(self):
        s_thread = threading.Thread(name="as_server_thread", target=self.as_server_thread, args=())
        s_thread.start()
        c_thread = threading.Thread(name="as_client_thread", target=self.as_client_thread, args=())
        c_thread.start()


def main():
    app = QApplication([])
    window = MyGUI()
    app.exec_()


if __name__ == "__main__":
    s_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s_socket.bind(('', PORT))
    main()
