import socket
import sys
import threading
import os

MAXLINE = 1000
SERVER_PORT = 12346
LISTENNQ = 5
MAX_THREAD = 5
HTTP_HEADER_LAST_CHAR_NUM = 4
BUFFER_SIZE = 4096

BLOCKED_URL = [b'sing.cse.ust.hk', b'google.com', b'www.google.com', b'https://www.google.com']

#The class of the server
class Server:
    channel = {}
    conn = 0
    address = 0
    cache = {}
    cache_no = 0

    #initialise the server
    def __init__(self):
        self.server = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.server.bind(('', SERVER_PORT))
        self.server.listen(5)
        self.thread_count = 0
        self.threads = []
    
    #check if the url is on the blocked list, return true if it is, else return false
    def url_is_blocked(self, url):
        return url in BLOCKED_URL

    def absolute_to_relative_path(self, data, host):
        return data.split()[0] + b' ' + data.split(host, 1)[1]

    def get_url(self, data):
        return data.split()[1]

    def get_host(self, data):
        host = data.split(b'Host:')[1]
        host = host.split()[0]
        return host

    def forward_Function(self, conn, outgoing, isHTTPS, url):
        if not outgoing and not isHTTPS:
            packets = []
            self.cache[url] = packets 
        while 1:
            data = conn.recv(BUFFER_SIZE)

            if len(data) == 0:
                print("Connection close:", end=" ")
                print(conn.getpeername())
                del self.channel[conn]
                conn.close()
                return

            if outgoing and not isHTTPS:
                data = self.absolute_to_relative_path(data, self.get_host(data))

            self.channel[conn].sendall(data)

            if not outgoing and not isHTTPS:
                self.cache[url].append(self.cache_no)
                fp = open(str(self.cache_no), "wb")
                fp.write(data)
                self.cache_no += 1

    def thread_function(self, conn):
        
        data = conn.recv(BUFFER_SIZE)

        host = self.get_host(data)

        if self.url_is_blocked(host): #if the url is blocked, return 404 msg and close socket
            conn.sendall(b'HTTP/1.1 404 Not Found\r\n\r\n')
            conn.close
            print("Request of", end=" ")
            print(host, end=" ")
            print("is blocked")
            return

        forward = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        print(host) #print host for debugging
        
        #distinglish between http and https
        if data.startswith(b'CONNECT'): #run this if it is https
             
            try:
                forward.connect((host, 443))
            except:
                print("HTTPS connection failure")

            self.channel[conn] = forward
            self.channel[forward] = conn

            forward_thread = threading.Thread(target = Server.forward_Function, args=(self, conn, True, True, 0, ))
            return_thread = threading.Thread(target = Server.forward_Function, args=(self, forward, False, True, 0, ))

            forward_thread.start()
            return_thread.start()
            
            conn.sendall(b'HTTP/1.1 200 Connection Established\r\n\r\n')

            forward_thread.join()

            return

        #run the following part if it is http
        url = self.get_url(data)
        
        if url in self.cache:
            print("BreakPoint1")
            for i in self.cache[url]:
                fp = open(str(i), "rb")
                cache_data = fp.read()
                conn.sendall(cache_data)
            conn.close()
            print("Opened from cache: ", end = "")
            print(url)
            return

        try:
            forward.connect((host, 80))
        except:
            print("connection failure")

        self.channel[conn] = forward
        self.channel[forward] = conn

        data = self.absolute_to_relative_path(data, host)

        forward_thread = threading.Thread(target = Server.forward_Function, args=(self, conn, True, False, url,))
        return_thread = threading.Thread(target = Server.forward_Function, args=(self, forward, False, False, url, ))

        forward_thread.start()
        return_thread.start()

        forward.sendall(data)

        forward_thread.join()

    #the loop that is run to handle requestes
    def loop(self):
        while 1:
            #accepting incoming connection
            try:
                (conn, address) = self.server.accept()
            except:
                print("Error: accept\n")
                return 0
            
            #print out information of incoming connection
            print("Incoming connection from", end = " ")
            print(conn.getpeername())

            #create and start the thread to handle the connection
            try:
                newThread = threading.Thread(target = Server.thread_function, args=(self, conn, ))
                self.threads.append(newThread)
                newThread.start()
            except Exception as e:
                print("Error: threading")
                print(e)
                return 0
            
            # self.thread_count = self.thread_count + 1
            # if self.thread_count >= MAX_THREAD:
            #     break
        
        
        # print("Max thread number reached, wait for all threads to finish and exit...")
        # for i in self.threads:
        #     i.join()
        
        return 0

#the main function to start up the proxy server
if __name__ == '__main__': 
    server = Server()
    server.loop()
    sys.exit(1)


