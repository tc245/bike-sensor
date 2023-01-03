#!/usr/bin/env python
import time
import serial
import concurrent.futures
import logging
import queue
import threading

# parser = argparse.ArgumentParser()
# parser.add_argument('--action', action='store', type=str, required=True)
# args = parser.parse_args()

##variables
INTERVAL = 0.5

#Define thread functions
def serial_reader(queue, event, serial_object):
    while not event.is_set():
        serial_object.write(bytes('{"action": "read"}', 'UTF-8'))
        message = serial_object.read_until()
        logging.info("Producer got message: %s", message)
        queue.put(message)
        time.sleep(INTERVAL)

    logging.info("Producer received event. Exiting")

def consumer(queue, event):
    """Pretend we're saving a number in the database."""
    while not event.is_set() or not queue.empty():
        message = queue.get()
        logging.info(
            "Consumer storing message: %s (size=%d)", message, queue.qsize()
        )

    logging.info("Consumer received event. Exiting")

##Create serial object
ser = serial.Serial(
        port='/dev/ttyS0',
        baudrate = 9600,
        parity=serial.PARITY_NONE,
        stopbits=serial.STOPBITS_ONE,
        bytesize=serial.EIGHTBITS,
        timeout=20
)

if __name__ == "__main__":
    format = "%(asctime)s: %(message)s"
    logging.basicConfig(format=format, level=logging.INFO,
                        datefmt="%H:%M:%S")

    pipeline = queue.Queue(maxsize=10)
    event = threading.Event()
    with concurrent.futures.ThreadPoolExecutor(max_workers=2) as executor:
        executor.submit(serial_reader, pipeline, event, ser)
        executor.submit(consumer, pipeline, event)

        time.sleep(20)
        logging.info("Main: about to set event")
        event.set()


