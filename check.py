import requests
import sqlite3
import time

class App:

    def __init__(self):
        self.local_db_connection_string = 'site-checker.db'
        self.sqlite_conn = None
        self.test_sites = (
            ('classic_catalog', 'https://classic.cincinnatilibrary.org/'),
            ('encore', 'https://catalog.cincinnatilibrary.org/iii/encore/')
            # ,
            # here are some other test sites we can use
            # ('status_500', 'https://httpstat.us/500'),
            # ('status_200', 'https://httpstat.us/200'),
            # ('site_not_exists', 'https://blakdjfkjdkajfdklfjkdsjfghghadkjklerjerjekfjdfkjd.com'),
            # ('expired_ssl', 'https://expired.badssl.com/')
        )

        # open the local database, and create tables if we need to
        # sets self.sqlite_conn
        self.open_db_connections()

        for site in self.test_sites:
            try:
                r = None
                message = None
                # this previous method of getting the site will not follow redirects (302 for example, which encore uses)
                # r = requests.head(site[1])

                r = requests.get(site[1])

                self.send_status(site[0], site[1], r.status_code, message)

            except requests.exceptions.SSLError:
                message = 'SSL error'
                self.send_status(site[0], site[1], None, message)

            except requests.exceptions.ConnectionError:
                message = 'failed to connect'
                self.send_status(site[0], site[1], None, message)
                
            except requests.exceptions.RequestException as e:
                message = 'other failure: {}'.format(e)
                self.send_status(site[0], site[1], None, message)


    #~ the destructor
    def __del__(self):
        if self.sqlite_conn:
            if hasattr(self.sqlite_conn, 'commit'):
                self.sqlite_conn.commit()

        if hasattr(self.sqlite_conn, 'close'):
            print("closing sqlite_conn")
            self.sqlite_conn.close()

        self.sqlite_conn = None
		
        print("done.")
                

    def send_status(self, site_name=None, site_url=None, status_code=None, message=None):
        # create a new cursor to use
        cursor = self.sqlite_conn.cursor()

        # if status code is not set, or it's set and is above 200, consider check a failure
        if (status_code == None) or (status_code > 200):
            success = False
        else:
            success = True

        timestamp = int(time.time())

        values = (timestamp, site_name, site_url, status_code, message, success)
        
        # print(values)
        # print('timestamep : {}'.format(timestamp))
        # print('site_name  : {}'.format(site_name))
        # print('site_url   : {}'.format(site_url))
        # print('status_code: {}'.format(status_code))
        # print('message    : {}'.format(message))
        # print('success    : {}'.format(success))
        # print('---')

        sql = """
        INSERT INTO
        status (
            'checked_date', 'site_name', 'site_url', 'status_code', 'message', 'success'
        )

        VALUES 
        (?, ?, ?, ?, ?, ?)
        """

        cursor.execute(sql, values)
        self.sqlite_conn.commit()
        cursor.close()
        cursor = None


    def open_db_connections(self):
        try:
            self.sqlite_conn = sqlite3.connect(self.local_db_connection_string)
        except sqlite3.Error as e:
            print("unable to connect to local database: %s" % e)

        # create a new cursor to use
        cursor = self.sqlite_conn.cursor()

        sql = """
        CREATE TABLE IF NOT EXISTS 'status' ( 
            'checked_date' INTEGER, -- stored as unix epoch time
            'site_name' TEXT,
            'site_url' TEXT,
            'status_code' INTEGER,
            'message' TEXT,
            'success' INTEGER -- true on success, false on fail or bad status)
        )
        """

        cursor.execute(sql)

        self.sqlite_conn.commit()
        cursor.close()
        cursor = None


# run the app
app = App()
