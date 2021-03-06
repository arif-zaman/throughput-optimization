import socket
import numpy as np
import multiprocessing as mp
import logging
import time
from config import configurations

chunk_size = mp.Value("i", 0)
root = configurations["data_dir"]["receiver"]
HOST, PORT = configurations["receiver"]["host"], configurations["receiver"]["port"]

if configurations["loglevel"] == "debug":
    logger = mp.log_to_stderr(logging.DEBUG)
else:
    logger = mp.log_to_stderr(logging.INFO)
    
file_transfer = True
if "file_transfer" in configurations and configurations["file_transfer"] is not None:
    file_transfer = configurations["file_transfer"]


def get_chunk_size(unit):
    unit = max(unit, 0)
    return (2 ** unit) * 1024


def worker(sock):
    while True:
        try:
            client, address = sock.accept()
            logger.debug("{u} connected".format(u=address))
            
            total = 0
            d = client.recv(1).decode()
            while d:
                header = ""
                while d != '\n':
                    header += str(d)
                    d = client.recv(1).decode()
                    
                if file_transfer:
                    file_stats = header.split(",")
                    filename, offset, to_rcv = str(file_stats[0]), int(file_stats[1]), int(file_stats[2])
                    file = open(root + filename, "wb+")
                    file.seek(offset)
                    logger.debug("Receiving file: {0}".format(filename))
                    
                    chunk = client.recv(chunk_size.value)
                    while chunk:
                        file.write(chunk)
                        to_rcv -= len(chunk)
                        total += len(chunk)
                        
                        if to_rcv > 0: 
                            chunk = client.recv(min(chunk_size.value, to_rcv))
                        else:
                            file.close()
                            logger.debug("Successfully received file: {0}".format(filename))
                            break
                else:
                    chunk = client.recv(chunk_size.value)
                    while chunk:
                        chunk = client.recv(chunk_size.value)
                
                d = client.recv(1).decode()
                    
            total = np.round(total/(1024*1024))
            logger.debug("{u} exited. total received {d} MB".format(u=address, d=total))
            client.close()
        except Exception as e:
            logger.error(str(e))


if __name__ == '__main__':
    num_workers = configurations['limits']["thread"]
    chunk_size.value = get_chunk_size(configurations['limits']["bsize"])
    if num_workers == -1:
        num_workers = mp.cpu_count()
        
    sock = socket.socket()
    sock.bind((HOST, PORT))
    sock.listen(num_workers)

    workers = [mp.Process(target=worker, args=(sock,)) for i in range(num_workers)]
    for p in workers:
        p.daemon = True
        p.start()

    while True:
        try:
            time.sleep(1)
        except:
            break
        