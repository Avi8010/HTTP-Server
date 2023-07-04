import json                    # provides functions for working with json data.
import os                      # provides functions to interact with os.
import socket                  # provides way of communication
from _thread import *          # threads of execution
import utility                 # provides functions in utility
import Requests                # provides methods in Requests
import signal                  # provides os signal
import sys
from datetime import datetime
from threading import Lock
from config import *

# function to handle the termination of server
def exit_handler(*args):
    # open cookies.json in write mode.
    fd = open(DEFAULT_DIR_PATH + "/cookies.json", "w")

    # write the contents of cookieDict  to the file in JSON format
    json.dump(cookieDict, fd, indent="\t")
    fd.close()

    # logs the message that server has terminated/stopped
    utility.writeErrorLog("debug", str(os.getpid()), "-", "Server stopped")
    
    # exits the program.
    sys.exit(0)

# if SIGINT->Interrupt or SIGTERM->Termination signals recieved the exit_handler function is called.
signal.signal(signal.SIGINT, exit_handler)
signal.signal(signal.SIGTERM, exit_handler)

TOT_COUNT = 20

# initializing the simultaneousConn
simultaneousConn = 0

# initializes Lock object
lock = Lock()

# initializes the cookieDict
cookieDict = {}


def buildResponse(reqDict):
    global cookieDict

    # retrives the method from reqDict
    method = reqDict.get("method")

    # calles the requests according to the method
    if method == "GET":
        response = Requests.get_or_head(reqDict, "GET")
    elif method == "HEAD":
        response = Requests.get_or_head(reqDict, "HEAD")
    elif method == "POST":
        response = Requests.post(reqDict)
    elif method == "PUT":
        response = Requests.put(reqDict)
    elif method == "DELETE":
        response = Requests.delete(reqDict)

    # lock the shared resources
    lock.acquire()

    # handle the cookie present in the request
    newCookie, cookieDict = utility.handleCookie(reqDict["headers"].get("Cookie", {}), reqDict["Client-Address"], method, cookieDict)
    
    # if newcookie is generated and no errors
    if newCookie and not response["isError"]:
        response["headers"]["Set-Cookie"] = MY_COOKIE_NAME + "=" + newCookie + ";" + " Max-Age=" + str(COOKIE_EXPIRE_TIME)
        
    # releases the resourses
    lock.release()

    # returns the response
    return response

# handles the each incoming client connection by creating new thread for each connection
def new_thread(client_conn, client_addr, newSocket):
    global simultaneousConn

    # keeping the coonection alive for maximum time
    timeoutDuration = MAX_KEEP_ALIVE_TIME

    # maximum number of requests on the persistent connction
    maxReqCount = MAX_REQ_ON_PERSISTENT_CONN

    try:
        # until maxReqCount becomes 0
        while maxReqCount:
            req = b''

            # reads the data from the client connection and returns the recieved request
            req = utility.receiveSocketData(client_conn, timeoutDuration)

            # if request is none means connection is closed and loop should break
            if req == None:
                break

            # parse the recieved requests to extracts the components of request
            reqDict = utility.parse_request(req.decode("ISO-8859-1"))

            # if requests is valid logs the  first line of request
            if reqDict.get("First-Line"):
                utility.writeErrorLog("debug", str(os.getpid()), client_addr, reqDict["First-Line"])

            # client address is added to reqDict as value for Client-Address
            reqDict["Client-Address"] = client_addr

            # if reqDict has error, generate the error response and response to the client
            if reqDict["isError"]:
                content = utility.generate_error_response(reqDict["Status-Code"], reqDict["Status-Phrase"], reqDict["Msg"])
                
                # stores the details of error response
                responseDict = { "Version": "HTTP/1.1", "Status-Code": str(reqDict["Status-Code"]), "Status-Phrase": reqDict["Status-Phrase"], "isError": True, "headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "close" , "Content-Length": str(len(content.encode())), "Content-Type": "text/html" }}
                
                # to decide if the response body should included in error response
                if reqDict.get("method") and reqDict["method"] != "HEAD":
                    responseDict["body"] = content.encode()

                # 405 -> method not allowed
                # Allow header is added to responseDict 
                if str(reqDict["Status-Code"]) == "405":
                    responseDict["headers"]["Allow"] = "GET, HEAD, PUT, POST, DELETE"
                
                # to ensure consistent connection handling
                if reqDict.get("headers") and reqDict["headers"].get("Connection", None):
                    responseDict["headers"]["Connection"] = reqDict["headers"]["Connection"]

                # send the error response to the client
                client_conn.send(utility.generateResponse(responseDict))

                # logs a message that error response sent
                utility.writeErrorLog("debug", str(os.getpid()), "-", reqDict("First-Line")+" - response sent.")

            else:
                # to generate the response for the request 
                response = buildResponse(reqDict)
                resp = { "Version": "HTTP/1.1", "Status-Code": str(response["Status-Code"]), "Status-Phrase": response["Status-Phrase"], "isError": False,"headers": {"Date": utility.toRFC_Date(datetime.utcnow()), "Server": utility.serverInfo(), "Connection": "close"  }}

                # if error in buildResponse
                if response["isError"]:
                    content = utility.generate_error_response(response["Status-Code"], response["Status-Phrase"], response["Msg"])
                    resp["isError"] = True
                    resp["headers"]["Content-Length"] = str(len(content.encode()))
                    resp["headers"]["Content-Type"] = "text/html"
                    if reqDict["method"] != "HEAD":
                        resp["body"] = content.encode()
                else:
                    if response.get("body", None):
                        resp["body"] = response["body"]
                        resp["headers"]["Content-Length"] = response["headers"].get("Content-Length", "0")
                    resp["headers"].update(response["headers"])

                if reqDict["headers"].get("Connection", None):
                    resp["headers"]["Connection"] = reqDict["headers"]["Connection"]
                
                # logs the request and response information in to the acces log file
                utility.writeAccessLog(reqDict, resp, client_addr, ACCESS_LOG_PATH)
                
                # send response to the client
                client_conn.send(utility.generateResponse(resp))

                # logs the message that response has sent
                utility.writeErrorLog("debug", str(os.getpid()), "-",reqDict.get("First-Line") + " - response sent.")

            if reqDict.get("headers"):
                # close the connection and break the loop
                if reqDict["headers"].get("Connection", "close") == "close":
                    client_conn.close()
                    break
                else:
                    # persistent connection
                    keepAlive = reqDict["headers"].get("Keep-Alive")
                    if keepAlive:
                        keepAliveArr = keepAlive.split(",")
                        keepAliveArr = utility.stripList(keepAliveArr)
                        timeoutDuration = int(keepAliveArr[0].split("=")[1].strip())
                        maxReqCount = int(keepAliveArr[1].split("=")[1].strip())
            else:
                client_conn.close()
                break
            maxReqCount -= 1
        simultaneousConn -= 1
    except:
        utility.writeErrorLog("warn", str(os.getpid()), "-", "internal server error.")


def main():
    global cookieDict, simultaneousConn
    fd = open(DEFAULT_DIR_PATH + "/cookies.json", "r") # open cookies.json in read mode
    cookieDict = json.load(fd)  # load contents of cookies.json in to the cookieDict
    fd.close()

    try:
        # create socket object
        # AF_INET for IPv4
        # SOCK_STREAM for TCP socket
        s_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # server address
        #listening on server port
        server_addr = ("localhost", SERVER_PORT)

        # sets the socket options level
        #socket address can be reused
        #1 for enabling the option
        s_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)

        # binds the serevr address to recieve incoming connections on that address and port
        s_socket.bind(server_addr)

        # set the server socket to listening mode with maxx connections
        s_socket.listen(MAX_CONN)

        # logs the debug message indicating that the server has started
        utility.writeErrorLog("debug", str(os.getpid()), "-","Server started on port: " + str(SERVER_PORT))
    except:
        # if exception occurs, logs the critical message.
        utility.writeErrorLog("critical", str(os.getpid()), "-", "Socket error.")

    while True:
        client_conn, client_addr = s_socket.accept() # waitts for an incoming connection
        
        # logs the debug message that connection is accepted.
        utility.writeErrorLog("debug", str(os.getpid()), client_addr, "Accepted new connection")
        
        # keeps track of number of simultaneous connections
        simultaneousConn += 1 
        
        # if maxx_conn condition reached
        if (not utility.isError(simultaneousConn, "max_simult_conn_exceed")):
            # simultaneous thread execution for each connection
            start_new_thread(new_thread, (client_conn, client_addr, s_socket))
        
        # if maxx_conn reached close the connection, generate 503 response 
        else:
            # temporarily server could not serve the request
            response = utility.gen_503_response()
            client_conn.send(response.encode("ISO-8859-1"))
            client_conn.close()
            utility.writeErrorLog("warn", str(os.getpid()), "-","max connection reached.")

# ensures that "main" function is only calles when script is executed directy, not when imported as module
if __name__ == '__main__':
    main()
