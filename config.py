import configparser

# creating instance of ConfigParser
config = configparser.ConfigParser()
# Read the configuration file
config.read("conf/server.conf")


SERVER_PORT = 7000             # server port   
MAX_CONN = 100                 # maxx simultaneous connections
MAX_REQ = 50                   # maxx requests
MAX_URI_LENGTH = 500           # maxx length of uri
MAX_HEADER_LENGTH = 500        # maxx header length
TIME_DIFF = 19800
SUPPORTED_METHODS = {"GET", "HEAD", "POST", "PUT", "DELETE"} # supported methods
DEFAULT_DIR_PATH = "/home/avi/RequestHandler/test"          # directory path for requests
EXPIRE_TIME = 86400            # cache expire time
MAX_KEEP_ALIVE_TIME = 3 # in seconds
TOT_COUNT = 20
ACCESS_LOG_PATH = DEFAULT_DIR_PATH + "log/access.log"
COOKIE_EXPIRE_TIME = 60
MY_COOKIE_NAME = "MyHttpCookie"
MAX_REQ_ON_PERSISTENT_CONN = 100  # maxx requests on persistent connection
LOG_LEVEL = "all" # {debug, warning, info, error, critical}

if "SERVER" in config.sections():
    DEFAULT_DIR_PATH = config["SERVER"]["DocumentRoot"]
    SERVER_PORT = int(config["SERVER"]["ServerPort"])
    MAX_CONN = int(config["SERVER"]["MaxSimultaneousConnections"])
    MAX_URI_LENGTH = int(config["SERVER"]["MaxUriLength"])
    MAX_HEADER_LENGTH = int(config["SERVER"]["MaxHeaderLength"])
    EXPIRE_TIME = int(config["SERVER"]["CacheExpireTime"])
    MAX_REQ_ON_PERSISTENT_CONN = int(config["SERVER"]["MaxReqOnPersistentConn"])
    MAX_KEEP_ALIVE_TIME = int(config["SERVER"]["MaxKeepAliveTime"])

if "COOKIE" in config.sections():
    MY_COOKIE_NAME = config["COOKIE"]["CookieName"]
    COOKIE_EXPIRE_TIME = int(config["COOKIE"]["CookieExpireTime"])

if "LOG" in config.sections():
    ACCESS_LOG_PATH = config["LOG"]["AccessLogPath"]
    ERROR_LOG_PATH = config["LOG"]["ErrorLogPath"]
    LOG_LEVEL = config["LOG"]["LogLevel"]
