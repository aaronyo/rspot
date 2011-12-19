#!/usr/bin/env python

import os

import spotify
import spotify.manager



class SessionManager(spotify.manager.SpotifySessionManager):

    appkey_file = os.path.join(os.path.dirname(__file__), 'spotify_appkey.key')

    def __init__(self, *a, **kw):
        super(SessionManager, self).__init__(*a, **kw)
        print "Logging in, please wait..."
#        self.session.logout()

    def logged_in(self, session, error):
        if error:
            print error
            return
        print "LOGGED IN!"
        self.session = session


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="spotify username")
    parser.add_argument("-p", "--password", help="spotify password")
    args = parser.parse_args()
    session_m = SessionManager(args.username, args.password, True)
    session_m.connect()
