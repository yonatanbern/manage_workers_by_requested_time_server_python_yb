from http.server import BaseHTTPRequestHandler, HTTPServer
import logging
from urllib.parse import parse_qs
from urllib.parse import urlparse
import io
from threading import *
import time
import json
import cgi
import random
import socket
import struct

print('Start the script ..... ')

# ds - holds all workers (10 in total)
worker_dic_by_ip = {}
# ds - holds all busy (requested by user) workers & manages their time
busy_workers_list_by_rem_time = []
# var - current number of available workers
num_of_available_workers = [10]


# Class which represent a single worker(slave), recognize by unique ip
class Worker:
    def __init__(self, ip_addr, busy_bit, duration, time_stamp):
        self.ip = ip_addr
        self.busy_bit = busy_bit
        self.duration = duration
        self.time_stamp_start = time_stamp

    def to_string(self):
        return f'worker[ip:{self.ip}, busy_bit:{self.busy_bit}, duration:{self.duration}, time_stamp_start:' \
            f'{self.time_stamp_start}]'


# Auxiliary functions for the programme:

def print_workers_list():
    print('WORKERS LIST:')
    for key, val in worker_dic_by_ip.items():
        print(key, val.to_string())


def init_worker_list():
    workers_list = []
    ip = '192.168.0.10'

    for i in range(1, 10):
        workers_list.append(Worker(ip + str(i), 0, 0, 0))
    workers_list.append(Worker('192.168.0.110', 0, 0, 0))

    for itm in workers_list:
        worker_dic_by_ip[itm.ip] = itm


def update_num_of_available_workers():
    n_avlb_num = 0
    for w in worker_dic_by_ip.values():
        if w.busy_bit == 0:
            n_avlb_num += 1

    num_of_available_workers[0] = n_avlb_num


def select_N_workers(w_num):
    ans_ips = []

    for w in worker_dic_by_ip.values():
        if len(ans_ips) == w_num:
            return ans_ips
        if w.busy_bit == 0:
            ans_ips.append(w.ip)
        if len(ans_ips) == w_num:
            return ans_ips

    return -1


def url_parser(url_path):
    parsed_path = urlparse(url_path)
    n_query = parse_qs(parsed_path.query)

    if len(n_query.keys()) != 2 or list(n_query.keys())[0] != 'amount' or list(n_query.keys())[1] != 'duration':
        return -2

    if len(n_query) > 0:
        print('User req->', n_query)
        try:
            u_amount = int(n_query['amount'][0])
            u_duration = int(n_query['duration'][0])
            ans = (u_amount, u_duration)
        except ValueError:
            ans = -1
        return ans


def update_worker_dic_by_IP(l_ips: list, dur: int, curr_time):
    for ip in l_ips:
        worker_dic_by_ip[ip].busy_bit = 1
        worker_dic_by_ip[ip].duration = dur
        worker_dic_by_ip[ip].time_stamp_start = curr_time


def free_worker(ip):
    print('******freeee******', ip)
    worker_dic_by_ip[ip].busy_bit = 0
    worker_dic_by_ip[ip].duration = 0
    worker_dic_by_ip[ip].time_stamp_start = 0


def update_existing_busy_workers_list(curr_time):

    for worker_group in list(busy_workers_list_by_rem_time):
        worker_group[0] = worker_dic_by_ip[worker_group[1][0]].duration - (curr_time - worker_dic_by_ip[worker_group[1][0]].time_stamp_start)
        if worker_group[0] <= 0:
            for w_ip in worker_group[1]:
                free_worker(w_ip)
            busy_workers_list_by_rem_time.remove(worker_group)

    if len(busy_workers_list_by_rem_time) > 0:
        busy_workers_list_by_rem_time.sort(key=lambda x: x[0])


def update_busy_workers_list_by_rem_time(ips_selected: list, amount_and_duration_tuple: tuple, curr_time):

    if len(busy_workers_list_by_rem_time) == 0:
        busy_workers_list_by_rem_time.append([amount_and_duration_tuple[1], ips_selected])

    else:
        # update time of existing list
        update_existing_busy_workers_list(curr_time)

        if len(busy_workers_list_by_rem_time) == 0:
            busy_workers_list_by_rem_time.append([amount_and_duration_tuple[1], ips_selected])

        else:
            new_time_wgroup = True
            nw_duration = amount_and_duration_tuple[1]
            for wgroup in busy_workers_list_by_rem_time:
                if wgroup[0] == nw_duration:
                    wgroup[1] = wgroup[1] + ips_selected
                    new_time_wgroup = False

            if new_time_wgroup:
                busy_workers_list_by_rem_time.append([amount_and_duration_tuple[1], ips_selected])

    # sort the list in order that the shortest time remain will be first, follow by the second shortest and so on
    busy_workers_list_by_rem_time.sort(key=lambda x: x[0])
    print('waiting time list:', busy_workers_list_by_rem_time)


def calculate_time_to_wait(req_amount):
    curr_amount = num_of_available_workers[0]
    # search for the number of workers which satisfy the req amount from user - return time to wait for them
    for w_group in busy_workers_list_by_rem_time:
        curr_amount += len(w_group[1])
        if curr_amount >= req_amount:
            return w_group[0]


def handle_user_bad_input_non_int(self):
    self._set_response_json_bad_input()

    msg = {'message from server': 'Invalid Input - programme receives only integers number as input to fields'}
    json_string = json.dumps(msg)
    self.wfile.write(json_string.encode('utf-8'))
    print('Invalid input by User.')


def handle_user_bad_input_out_of_bounds_int(self, amount_and_duration_tuple):
    self._set_response_json_bad_input()

    msg = {'message from server': f'Invalid Input by User:: amount[1-10]:{amount_and_duration_tuple[0]}'
    f' duration[>0]:{amount_and_duration_tuple[1]}. please Try again.'}
    json_string = json.dumps(msg)
    self.wfile.write(json_string.encode('utf-8'))
    print('Invalid input by User.')


def handle_user_time_to_wait(self, amount_and_duration_tuple):
    update_num_of_available_workers()
    print('waiting time list:', busy_workers_list_by_rem_time)
    req_amount_by_user = amount_and_duration_tuple[0]
    time_to_wait = calculate_time_to_wait(req_amount_by_user)
    self._set_response_json()
    msg = {'slaves': [], 'come back': str(time_to_wait) + ' seconds'}
    json_string = json.dumps(msg)
    self.wfile.write(json_string.encode('utf-8'))

    print_workers_list()
    print('Avlbls workers: ', num_of_available_workers)


def handle_msg_to_user(self, ips_selected):
    self._set_response_json()
    msg = {'slaves': ips_selected}
    json_string = json.dumps(msg)
    self.wfile.write(json_string.encode('utf-8'))


def handle_favicon_req(self):
    icon = io.open("fav.jpg", "rb").read()
    self._set_response_fav(icon)
    self.wfile.write(icon)

def handle_user_bad_route(self):
    self._set_response_json_bad_input()

    msg = {'message from server': 'Invalid Input - Server no handle this url route'}
    json_string = json.dumps(msg)
    self.wfile.write(json_string.encode('utf-8'))
    print('Invalid input by User.')
# End of Auxiliary functions for the programme


# Python SERVER implementation:
class S(BaseHTTPRequestHandler):

    def _set_response_fav(self, icon):
        self.send_response_only(200)
        self.send_header('Content-type', 'mage/x-icon')
        self.send_header('Content-length', len(icon))
        self.end_headers()

    def _set_response(self):
        self.send_response_only(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def _set_response_json(self):
        self.send_response_only(200)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def _set_response_json_bad_input(self):
        self.send_response_only(400)
        self.send_header('Content-type', 'application/json')
        self.end_headers()

    def do_GET(self):
        print('\n-Get Request Received-')
        curr_time = time.time()
        print('Time(unix): ', curr_time)

        # request to favicon
        if self.path.endswith('favicon.ico'):
            handle_favicon_req(self)
            return

        # parsing the sent data from user, extract 2 nums of amount & duration
        if self.path[:12] == '/get_slaves?':

            amount_and_duration_tuple = url_parser(self.path)

            # check for an Invalid input by user
            if amount_and_duration_tuple == -1:
                handle_user_bad_input_non_int(self)
                return

            if amount_and_duration_tuple == -2:
                handle_user_bad_route(self)
                return

            if amount_and_duration_tuple[0] > 10 or amount_and_duration_tuple[0] < 0 or amount_and_duration_tuple[1] < 0:
                handle_user_bad_input_out_of_bounds_int(self, amount_and_duration_tuple)
                return

            # updating busy workers time from previous get requests
            if len(busy_workers_list_by_rem_time) > 0:
                update_existing_busy_workers_list(curr_time)

            # select N workers available by user request
            ips_selected = select_N_workers(amount_and_duration_tuple[0])

            # enough workers available case - update ds - return ips
            if ips_selected != -1:
                update_worker_dic_by_IP(ips_selected, amount_and_duration_tuple[1], curr_time)
                update_busy_workers_list_by_rem_time(ips_selected, amount_and_duration_tuple, curr_time)
                update_num_of_available_workers()

            else:
                # All workers are busy case - return time to wait
                handle_user_time_to_wait(self, amount_and_duration_tuple)
                return

            print_workers_list()
            print('Avlbls workers: ', num_of_available_workers)

            # send response to user (json format)
            handle_msg_to_user(self, ips_selected)

        else:
            handle_user_bad_route(self)
            return


def run(server_class=HTTPServer, handler_class=S, port=8080):
    logging.basicConfig(level=logging.INFO)
    server_address = ('', port)
    httpd = server_class(server_address, handler_class)
    logging.info(f'Starting httpd on port {port}...\n')
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        pass
    httpd.server_close()
    logging.info('Stopping httpd...\n')


if __name__ == '__main__':
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:

        init_worker_list()
        update_num_of_available_workers()
        print_workers_list()
        print('Avlbls workers: ', num_of_available_workers)
        print('\nSTART Server')

        # start the server by main thread
        run()

        print('END? Server')


print('*********END OF SCRIPT*********')
