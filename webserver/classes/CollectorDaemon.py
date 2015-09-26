import time
import signal
import syslog
import threading
from Queue import Queue
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Text
# from sqlalchemy.ext.hybrid import hybrid_property
# from sqlalchemy.orm import relationship, backref
from classes import DatabaseThread as dt
from classes import EngineThread as et

Base = declarative_base()

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class Engine(Base):
    __tablename__ = 'engines'
    id        = Column(Integer, primary_key=True)
    name      = Column(String(32), unique=True)
    address   = Column(String(255), unique=True)
    port      = Column(Integer)
    secret    = Column(String(128))
    active    = Column(Integer)
    owner     = Column(String(32))

# -----------------------------------------------------------------------------
#
# -----------------------------------------------------------------------------

class CollectorDaemon():

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __init__(self, root, config):
        """
        Initialize daemon.

        @type  root:     String
        @param root:     Full path to the root directory
        @type  config:   Dictionary
        @param config:   The complete configuration as a dictionary
        """

        self.root            = root
        self.config          = config
        self.modules         = None
        self.thread_queue    = []
        self.stdin_path      = self.config['daemon']['stdin']
        self.stdout_path     = self.config['daemon']['stdout']
        self.stderr_path     = self.config['daemon']['stderr']
        self.pidfile_path    = self.config['daemon']['pidfile']
        self.pidfile_timeout = self.config['daemon']['pidfile_timeout']
        self.running         = True
        syslog.openlog(logoption=syslog.LOG_PID, facility=syslog.LOG_DAEMON)

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def __sigterm_handler(self, signum, frame):
        """
        Handle SIGTERM signal and abort execution.
        """

        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs collector is stopping')
        for r_thread in self.thread_queue:
            syslog.syslog(syslog.LOG_INFO, 'collector: stopping engine handler thread')
            r_thread["instance"].stop()
        self.running = False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def has_thread(self, engine):
        for t in self.thread_queue:
            if t["engine"].address == engine.address:
                return True
        return False

    # -------------------------------------------------------------------------
    #
    # -------------------------------------------------------------------------

    def run(self):
        syslog.syslog(syslog.LOG_INFO, 'FuzzLabs collector is running')
        engine = create_engine('sqlite:///' + self.root +\
                               '/etc/database/webserver.db', echo=False)
        Session = sessionmaker(bind = engine)
        db = Session()
        db_queue = Queue(self.config["general"]["database_queue_size"])

        dt.DatabaseThread(self.root, self.config, db_queue).start()

        while self.running:
            engines = db.query(Engine).filter(Engine.active == 1)
            for engine in engines:
                if self.has_thread(engine):
                    continue

                e_thread = et.EngineThread(self.thread_queue, 
                                           self.root,
                                           self.config,
                                           db_queue,
                                           engine)
                self.thread_queue.append({
                    "engine": engine,
                    "instance": e_thread
                })
                e_thread.start()
            time.sleep(self.config["general"]["engine_check_interval"])

