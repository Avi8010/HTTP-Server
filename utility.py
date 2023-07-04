import hashlib            # hash tables to store key-value pair
import platform           # provides current platform information
import gzip               # provides data compression function
import random
import shutil             # provides interface for performing various operations on files and directories
import sys
import zlib               # provides data compression function
import brotli             # provides data compression function
import mimetypes          # provides function to determine the MIME type of a file based on extension or path
import os                 
import time
import math
from datetime import datetime
from config import *

# removes the extra spaces
def stripList(listObj):
    for i in range(len(listObj)):
        listObj[i] = listObj[i].strip()
    return listObj

def handleEncodingPriority(val):
    if val == "":
        return "identity"
    
    # available encoding options.
    availableEncodings=["br", "deflate", "gzip", "x-gzip"]
    processedEncodings={}
    accValues=stripList(val.split(","))

    for value in accValues:
        tmpArr = value.split(";", 1) # splitting followed by : with maxx 1 occurence
        if(len(tmpArr) == 2): # priority is provided
            priority = float((tmpArr[1].split("="))[1].strip())
        else:
            priority = 1.0
        if(tmpArr[0] == "*"): # applies to all available encodings.
            for enc in availableEncodings:
                if enc not in processedEncodings:
                    processedEncodings[enc] = priority
        elif tmpArr[0] in availableEncodings:
            processedEncodings[tmpArr[0]] = priority
    
    if not len(processedEncodings): # if empty that is no encoding is available
        return None
    result = max(processedEncodings, key = processedEncodings.get) # finding highest priority
    if processedEncodings[result] > 0: # for valid encoding
        return result
    return None

# function to returns all extensions
def getExtension(mimeType):
    return mimetypes.guess_all_extensions(mimeType)

# processes the accept content priorities
def handleAcceptContentPriority(filePath, val):
    acceptList = stripList(val.split(","))
    acceptDict = {} # to store the processed sccept content types and pririties
    fileExt = ""   # to store file extension
    if len(filePath.rsplit(".", 1)) == 2:
        fileExt = "." + filePath.rsplit(".", 1)[1]

    filePath = filePath.rsplit(".", 1)[0]
    for accept in acceptList:
        tmpArr = accept.split(";", 1)
        if accept == "*/*":  # applies to any content type 
            if(len(tmpArr) == 1):  # no priority is provided
                acceptDict[fileExt] = 1
            else:
                acceptDict[fileExt] = tmpArr[1]

        extensionArr = getExtension(tmpArr[0])
        for extension in extensionArr:
            tmpPath = filePath + extension
            if os.path.isfile(tmpPath): # if path exists
                if(len(tmpArr) == 1):
                    acceptDict[extension] = 1
                else:
                    acceptDict[extension] = tmpArr[1]
                break

    if len(acceptDict) == 0: # no valid file extension is available
        return None 
    return max(acceptDict, key = acceptDict.get) # returns file extension with highest priority

# processes the accept charset priorities
def handleAcceptCharsetPriority(acceptCharset):
    availableEncodings = ["utf-8", "ISO-8859-1"] # available option for character encoding
    processedEncodings = {}

    accValues = stripList(acceptCharset.split(","))
    for value in accValues:
        tmpArr = value.split(";", 1)
        if(len(tmpArr) == 2):
            priority = float((tmpArr[1].split("="))[1].strip())
        else:
            priority = 1.0
        if(tmpArr[0] == "*"):
            for enc in availableEncodings:
                if enc not in processedEncodings:
                    processedEncodings[enc] = priority
        elif tmpArr[0] in availableEncodings:
            processedEncodings[tmpArr[0]] = priority

    if not len(processedEncodings):
        return None        
    result = max(processedEncodings, key = processedEncodings.get)
    if processedEncodings[result] > 0:
        return result
    return None
    
# parses the cookies string and returns the key-vaue pair with cookie names
def parseCookies(cookies):
    if not cookies:
        return {}
    cookies = cookies.split(";")
    result = {}
    for cookie in cookies:
        [name, value] = stripList(cookie.split("="))
        result[name] = value
    return result

# returns the information about the server
def serverInfo():
    name = "HTTP-SERVER"
    version = "1.1"
    operatingSys = platform.platform()
    return name + "/" + version + " " + operatingSys

# returns the date and timestamp in RFC format
def toRFC_Date(date):
    weekdayDict = { 0: "Mon", 1: "Tue", 2: "Wed", 3: "Thu", 4: "Fri", 5: "Sat", 6: "Sun"}
    monthDict = { 1:"Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"} 
    return "%s, %02d %s %04d %02d:%02d:%02d GMT" % (weekdayDict[date.weekday()], date.day, monthDict[date.month], date.year, date.hour, date.minute, date.second)


# generate response body for the respDict
def generateResponse(respDict):
    if not respDict["isError"] and respDict["headers"].get("Content-Length"):
        del respDict["headers"]["Content-Length"]
    firstLine = respDict["Version"] + " " + respDict["Status-Code"] + " " + respDict["Status-Phrase"] + "\r\n"

    body = respDict.get("body", None)
    if body and not respDict["isError"]:
        body = chunkGenerator(body)
        respDict["headers"]["Transfer-Encoding"] = "chunked"
    elif not respDict["headers"].get("Content-Length"):
        respDict["headers"]["Content-Length"] = "0"
    result = firstLine
    for key in respDict["headers"]:
        result += key + ": " + str(respDict["headers"][key]) + "\r\n"
    result += "\r\n"
    if body:
        result = result.encode() + body # encode result to bytes
    else:
        result = result.encode()
    return result

# deletes the data at path
def deleteData(path, isFile):
    if isFile:
        os.remove(path)
    else:
        shutil.rmtree(path, ignore_errors=True) # removes the directory

# returns the compressed data
def encodeData(data, encodeFormat):
    if encodeFormat == "gzip" or encodeFormat == "x-gzip":
        return gzip.compress(data)
    elif encodeFormat == "deflate":
        return zlib.compress(data)
    elif encodeFormat == "br":
        return brotli.compress(data)
    return data


def logTime():
    timezone = time.timezone/3600  # convert to hours

    timezoneHour = math.floor(timezone) # extracts whole number part of timezone

    timezoneMin = int((timezone-timezoneHour)*60) # calculates minutes

    date = datetime.now() # retrieves current date and time

    # maps the month numbers to names
    monthDict = { 1:"Jan", 2: "Feb", 3: "Mar", 4: "Apr", 5: "May", 6: "Jun", 7: "Jul", 8: "Aug", 9: "Sep", 10: "Oct", 11: "Nov", 12: "Dec"} 
    
    # formats the string for desired format
    date = "%02d/%s/%04d:%02d:%02d:%02d +" % (
        date.day, monthDict[date.month], date.year, date.hour, date.minute, date.second)
    
    # append the hour and min to date string
    date += str(timezoneHour)
    date += str(timezoneMin)
    return date

# writing access log entries.
def writeAccessLog(reqDict, respDict, clientAddr, logFilePath):
    logDict = {
        'laddr': clientAddr[0],
        'identity':'-',
        'userid':'-',
        'time': logTime(),
        'requestLine':'"-"',
        'statusCode':'-',
        'dataSize':0,
        'referer':'"-"',
        'userAgent':'"-"',
        'cookie':'"-"',
        'set-cookie':'"-"'
    }
    logDict["requestLine"] = "'" + reqDict["First-Line"] + "'"
    logDict["statusCode"] = respDict["Status-Code"]
    logDict["dataSize"] = respDict["headers"]["Content-Length"]
    logDict["referer"] = "'" + reqDict["headers"].get("Referer", "-") + "'"
    logDict["userAgent"] = "'" + reqDict["headers"].get("User-Agent", "-") + "'"
    logDict["cookie"] = "'" + reqDict["headers"].get("Cookie", "-") + "'"
    logDict["set-cookie"] = "'" + respDict["headers"].get("Set-Cookie", "-") + "'"

    # store the log entry
    log = ""
    for logKey in logDict:
        log+=str(logDict[logKey]) + " "
    log += "\n"
    with open(logFilePath, "a") as fd:
        fd.write(log)
        fd.close()

# removes the expired cookies
def removeExpiredCookies(globalCookiesDict):
    expiredCookies = []
    for key in globalCookiesDict.keys():
        currentTime = math.floor(time.time())
        if globalCookiesDict[key]["expireTime"] < currentTime:
            expiredCookies.append(key)
    
    for key in expiredCookies:
        del globalCookiesDict[key]

    return globalCookiesDict


def handleCookie(cookieHeader, clientAddr, method, globalCookieDict):
    cookiesDict = parseCookies(cookieHeader) # extract key-value pair
    cookie = cookiesDict.get(MY_COOKIE_NAME, None) # retrieve cookie otherwise none 
    newCookie = None
    if not cookie:
        tmpStr = str(time.time()) + str(random.randint(10000, 99999)) 
        newCookie = hashlib.md5(tmpStr.encode()).hexdigest() # 128 bit hash value in hexadecimal
        globalCookieDict[newCookie] = {
            "host": clientAddr,
            "expireTime": math.floor(time.time()) + COOKIE_EXPIRE_TIME,
            "tot_get_requests": 0,
            "tot_head_requests": 0,
            "tot_post_requests": 0,
            "tot_put_requests": 0,
            "tot_delete_requests": 0
        }
        globalCookieDict[newCookie]["tot_" + method.lower() + "_requests"] = 1

    else:
        # check for expire, check if available
        globalCookieDict = removeExpiredCookies(globalCookieDict)
        checkCookie = globalCookieDict.get(cookie, None)
        if not checkCookie:
            # set cookie
            tmpStr = str(time.time()) + str(random.randint(10000, 99999)) 
            newCookie = hashlib.md5(tmpStr.encode()).hexdigest()
            globalCookieDict[newCookie] = {
                "host": clientAddr,
                "expireTime": math.floor(time.time()) + COOKIE_EXPIRE_TIME,
                "tot_get_requests": 0,
                "tot_head_requests": 0,
                "tot_post_requests": 0,
                "tot_put_requests": 0,
                "tot_delete_requests": 0
            }
            globalCookieDict[newCookie]["tot_" + method.lower() + "_requests"] = 1
        else:
            globalCookieDict[cookie]["tot_" + method.lower() + "_requests"] += 1
    
    return newCookie, globalCookieDict

# generate chunk response body 
def chunkGenerator(data):
    arr = []
    tot_len = len(data)
    prev = 0
    while(tot_len > 0):
        val = random.randint(10,30)
        if prev + val > len(data): # remaining data is less than the val
            arr.append(data[prev:])
        else:
            arr.append(data[prev: prev + val])
        prev = prev + val
        tot_len -= val

    result = b"" # bytes object
    for chunk in arr:
        result += b"%x\r\n" % len(chunk) #hexadecimal format
        result += (chunk + b"\r\n")
    result += b"0\r\n\r\n" # add final chunk marker
    return result

def isError(data, errorType):
    if (errorType == "max_simlt_conn_exceed"):
        if (data < MAX_CONN):
            return False
        return True
    elif errorType == "uri_too_long":
        if data < MAX_URI_LENGTH:
            return False
        return True
    elif errorType == "method_not_implemented":
        if (data in SUPPORTED_METHODS):
            return False
        return True
    elif errorType == "header_too_long":
        if (data < MAX_HEADER_LENGTH):
            return False
        return True
    elif errorType == "version_not_supported":
        http_version = data.split("/", 1)
        if (len(http_version) == 2 and http_version[0] == "HTTP" and (http_version[1].lstrip())[0] == "1"):
            return False
        return True
    elif errorType == "host_not_available":
        if ("Host" not in data):
            return True
        return False

# function to parse the request
def parse_request(request):
    request = request.split("\r\n\r\n", 1) # seperates header and body
    header = request[0]
    body = ""
    if (len(request) > 1):
        body = request[1]

    header_lines = header.split("\r\n")
    reqLine = header_lines[0].strip()
    first_line = header_lines[0].split()

    # incorrect request format 400
    if (len(first_line) != 3):
        return {"isError": True, "method": "", "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "request format is not supported."}

    [req_method, req_uri, http_version] = first_line

    # length of uri exceeds 414
    if (isError(len(req_uri), "uri_too_long")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 414, "Status-Phrase": "URI Too Long", "Msg": "Requested uri is too long to handle to server."}

    # method not supported 405
    if (isError(req_method, "method_not_implemented")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 405, "Status-Phrase": "Method Not Implemented", "Msg": "Requested method is not implemented at server side or server could not support requested method."}

    # version not suported 505
    if (isError(http_version, "version_not_supported")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 505, "Status-Phrase": "HTTP Version Not Supported", "Msg": "HTTP Version Not Supported, either requested wrong version format or requested http version is not supported by server."}

    headers = header_lines[1:]
    header_dict = {}
    for single_header in headers:
        single_header = single_header.split(":", 1)

        # incorrect request format 400
        if len(single_header) != 2:
            return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Header format is incorrect."}
        
        # if header length exceeds 431
        if (isError(len(single_header[1]), "header_too_long")):
            return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 431, "Status-Phrase": "Request header fields too large", "Msg": "Requested header field is too large to handle to server."}
        single_header[0] = single_header[0].strip()
        single_header[1] = single_header[1].strip()

        # store header field and its value.
        header_dict[single_header[0]] = single_header[1]

    # host is unavailable
    if (isError(header_dict, "host_not_available")):
        return {"isError": True, "method": req_method, "First-Line": reqLine, "Status-Code": 400, "Status-Phrase": "Bad Request", "Msg": "Header format is incorrect."}
    
    # if error occure in parsing the request
    return {"isError": False, "method": req_method, "First-Line": reqLine, "headers": header_dict, "uri": req_uri, "method": req_method, "Version": http_version, "body": body}

# recieving data from the socket connection and constructing the request format
def receiveSocketData(connection, timeout):
    partialReq = b"" # byte object
    connection.settimeout(timeout)
    count = 0
    while True:
        try:
            partialReq += connection.recv(8096) # buffer size=8096 to recieve data at a time
            if count > TOT_COUNT:
                connection.close()
                return None
            if (not partialReq):
                time.sleep(timeout/TOT_COUNT)
                count += 1
        except Exception as e: # if exception occurs while recieving the data, connection closes and logs an error.
            connection.close()
            writeErrorLog("debug", str(os.getpid()), "-", "connection timeout")
            return None
        
        if "\r\n\r\n".encode() in partialReq: # loop breaks when complete requests data is recieved.
            break

    partialReqDict = parse_request(partialReq.decode("ISO_8859-1")) # chracter encoding standard - single byte
    if partialReqDict["isError"]: # header data as parial request
        return partialReq
    contentLength = int(partialReqDict["headers"].get("Content-Length", 0))
    contentLength -= int(partialReq.split("\r\n\r\n".encode(), 1)[1])
    body = b""

    while len(body) < contentLength: # body as remaining data
        try:
            body += connection.recv(8096)
        except Exception as e:
            connection.close()
            writeErrorLog("debug", str(os.getpid()),"-", "connection timeout.")
            return None
    return (partialReq+body).strip()

# generate error response
def generate_error_response(errorCode, errorPhrase, errorMsg):
    resp = """
<!DOCTYPE html>
<html>
    <head>
        <title>{} {}</title>
        </head>
        <body>
            <h1>{}</h1>
            <p1>{}</p>
        </body>
</html>
    """.format(errorCode, errorPhrase, errorPhrase, errorMsg)
    return resp


# generate error message
def gen_503_response():
    response = "HTTP/1.1 503 Service Unavailable\r\nDate: Mon, 04 Jun 2023 20:10:45 GMT\r\nServer: MY_HTTP-SERVER/1.1\r\nConnection:close\r\nContent-Length: 195\r\nContent-Type: text/html\r\n\r\n"
    response = generate_error_response(503, "Service Unavailable", "Service temporarily not available, please try again later.")
    return response

def generateBoundary():
    arr = "0123456789abcdef"
    res = ""
    for i in range(15):
        res += arr[random.randint(0, 15)]
    return res

def writeErrorLog(logLevel, pid, clientIp, msg):

    if LOG_LEVEL == logLevel or LOG_LEVEL == "all":
        timestamp = logTime() # gives the timestamp 
        fd = open(ERROR_LOG_PATH, "a") # file open in append mode
        if clientIp != "-":
            # modifies the clients Ip in ip:port format
            clientIp = clientIp[0]+":"+str(clientIp[1])
        errorLog = "[{}] [{}] [{}] [{}] [{}]\n".format(timestamp, logLevel, pid, clientIp, msg)
        fd.write(errorLog)
        fd.close() # file closed

    # critical error occured and program should terminate
    if logLevel == "critical":
        sys.exit(0)
