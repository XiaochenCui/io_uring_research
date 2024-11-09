#!/usr/bin/env python3

import json
import os
import sys
import xiaochen_py
import signal
import matplotlib.pyplot as plt
import numpy as np
import xiaochen_py
import re

CODE_DIR = "/home/xiaochen/code"
IO_URING_RESEARCH_DIR = os.path.join(CODE_DIR, "io_uring_research")


# io_uring vs epoll
def bench_a():
    def setup():
        os.chdir(CODE_DIR)
        target_dir = os.path.join(CODE_DIR, "liburing")
        if not os.path.exists(target_dir):
            xiaochen_py.run_command("git clone https://github.com/axboe/liburing")
            os.chdir(target_dir)
            xiaochen_py.run_command("./configure --prefix=/home/xiaochen/lib/liburing")
            xiaochen_py.run_command("make")
            xiaochen_py.run_command("make install")

        os.chdir(IO_URING_RESEARCH_DIR)

        # compile io_uring echo server
        INCLUDE_DIR = "/home/xiaochen/lib/liburing/include"
        LIB_DIR = "/home/xiaochen/lib/liburing/lib"
        CPP_FILE = "./benchmark/echo_server_io_uring.cpp"
        BIN_FILE = "./build/echo_server_io_uring"
        xiaochen_py.run_command(
            f"c++ {CPP_FILE} -o {BIN_FILE} -Wall -O2 -D_GNU_SOURCE -luring -I{INCLUDE_DIR} -L{LIB_DIR}"
        )

        # compile epoll echo server
        CPP_FILE = "./benchmark/echo_server_epoll.cpp"
        BIN_FILE = "./build/echo_server_epoll"
        xiaochen_py.run_command(f"c++ {CPP_FILE} -o {BIN_FILE} -Wall -O2 -D_GNU_SOURCE")

    PORT = 8080
    ECHO_CLIENT_DIR = os.path.join(CODE_DIR, "rust_echo_bench")

    def run_io_uring(
        client_number: int,
        duration_seconds: int,
        message_length: int,
    ) -> xiaochen_py.BenchmarkRecord:
        io_uring_echo_server = xiaochen_py.run_background(
            f"./build/echo_server_io_uring {PORT}",
            log_path="echo_server_io_uring.log",
            work_dir=IO_URING_RESEARCH_DIR,
        )

        # bind io_uring_echo_server to CPU 0
        xiaochen_py.run_command(
            f"taskset -cp 0 {io_uring_echo_server.pid}",
        )

        output, _ = xiaochen_py.run_command(
            f"cargo run --release -- --address 'localhost:{PORT}' --number {client_number} --duration {duration_seconds} --length {message_length}",
            work_dir=ECHO_CLIENT_DIR,
        )
        io_uring_echo_server.exit()

        # sample output: Speed: 152720 request/sec, 152720 response/sec
        speed = re.search(r"Speed: (\d+) request/sec", output.decode("utf-8")).group(1)
        print(f"Speed: {speed} request/sec")

        r = xiaochen_py.BenchmarkRecord()
        r.target_attributes = {
            "target": "io_uring",
            "client_number": client_number,
            "duration_seconds": duration_seconds,
            "message_length": message_length,
        }
        r.test_result = {
            "request_per_second": int(speed),
        }

        return r

    def run_epoll(
        client_number: int,
        duration_seconds: int,
        message_length: int,
    ) -> xiaochen_py.BenchmarkRecord:
        epoll_echo_server = xiaochen_py.run_background(
            f"./build/echo_server_epoll {PORT}",
            log_path="echo_server_epoll.log",
            work_dir=IO_URING_RESEARCH_DIR,
        )

        # bind epoll_echo_server to CPU 1
        xiaochen_py.run_command(
            f"taskset -cp 1 {epoll_echo_server.pid}",
        )

        output, _ = xiaochen_py.run_command(
            f"cargo run --release -- --address 'localhost:{PORT}' --number {client_number} --duration {duration_seconds} --length {message_length}",
            work_dir=ECHO_CLIENT_DIR,
        )
        epoll_echo_server.exit()

        # sample output: Speed: 152720 request/sec, 152720 response/sec
        speed = re.search(r"Speed: (\d+) request/sec", output.decode("utf-8")).group(1)
        print(f"Speed: {speed} request/sec")

        r = xiaochen_py.BenchmarkRecord()
        r.target_attributes = {
            "target": "epoll",
            "client_number": client_number,
            "duration_seconds": duration_seconds,
            "message_length": message_length,
        }
        r.test_result = {
            "request_per_second": int(speed),
        }

        return r

    setup()

    client_number_list = [1, 200, 400, 600, 800, 1000]
    message_length_list = [1, 128, 1024]
    duration_seconds = 20

    records = []
    for client_number in client_number_list:
        for message_length in message_length_list:
            r = run_io_uring(client_number, duration_seconds, message_length)
            records.append(r)
            r = run_epoll(client_number, duration_seconds, message_length)
            records.append(r)

    xiaochen_py.dump_records(records, "docs/record")


def draw():
    report_path = get_latest_report()

    # parse the json to list(BenchmarkRecord)
    f = open(report_path, "r")
    all_records = json.load(f, object_hook=lambda x: xiaochen_py.json_loader(**x))

    points_list = []

    records = list(all_records)

    # sort by thread_count
    records.sort(key=lambda x: x.target_attributes["thread_count"])

    thread_count_list = [r.target_attributes["thread_count"] for r in records]
    insert_per_second = [r.test_result["insert_per_second"] for r in records]

    plt.plot(thread_count_list, insert_per_second)
    points = plt.scatter(thread_count_list, insert_per_second)
    points_list.append(points)

    plt.xlabel("Concurrent Transactions")
    plt.ylabel("Insertions per Second")

    top = max([r.test_result["insert_per_second"] for r in all_records]) * 1.3
    plt.ylim(bottom=0, top=top)

    plt.legend(handles=points_list, loc="upper right")

    plt.savefig(f"./docs/img/insertions_per_second_{xiaochen_py.timestamp()}.png")


if __name__ == "__main__":
    bench_a()
