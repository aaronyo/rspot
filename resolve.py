#!/usr/bin/env python

import os
import threading
import cmd
import time
import StringIO
import panko.command.recommend
import re
import sys

import PIL.Image

import spotify
import spotify.manager



class SessionManager(spotify.manager.SpotifySessionManager):

    appkey_file = os.path.join(os.path.dirname(__file__), 'spotify_appkey.key')

    def __init__(self, *a, **kw):
        super(SessionManager, self).__init__(*a, **kw)
        print "Logging in, please wait..."
#        self.session.logout()
        self.cmd_line = None

    def logged_in(self, session, error):
        if error:
            print error
            return
        print "LOGGED IN!"
        self.session = session
        self.cmd_line = CommandLine(self.session)
        self.cmd_line.start()        

def get_cover_art(track, session):
    alb = track.album()
    while not alb.is_loaded():
        time.sleep(.05)
    cov_id = alb.cover()
    print "cov_id: %s" % cov_id
    if cov_id:
        try:
            img = session.image_create(cov_id)
            while not img.is_loaded():
                time.sleep(0.05)
            data = img.data()
            print "img_length: %d" % len(data)
            imgobj = PIL.Image.open( StringIO.StringIO(data) )
            imgobj.show()
        except Exception, e:
            print e
            

class CommandLine(cmd.Cmd, threading.Thread):
    prompt = 'rspot> '
    
    def __init__(self, session):
        cmd.Cmd.__init__(self)
        threading.Thread.__init__(self)
        self.session = session
        self.playlist = []
        
    def run(self):
        self.cmdloop()
        
    def do_add(self, line):
        rec_num = int(line)
        self.playlist.append(self.recs[rec_num-1])
        self.do_list(None)

    def do_pop(self, line):
        if self.playlist:
            popped = self.playlist.pop()
            self.do_list(None)
            
    def do_list(self, line):
        for i, t in enumerate(self.playlist):
            print " "*4 + "%2d: %s  -  (%s) %s" \
                  % (i+1,
                     spotify.Link.from_track(t, 0),
                     t.artists()[0],
                     t.name())                                               
    
    def do_recs(self, line):
        for i, t in enumerate(self.recs):
            print " "*4 + "%2d: %s  -  (%s) %s" \
                  % (i+1,
                     spotify.Link.from_track(t, 0),
                     t.artists()[0],
                     t.name())                                               

    def do_track(self, line):
        self.waiting = True
        def search_finished(results, userdata):
            tracks = results.tracks()
            if tracks:
                t = tracks[0]
                print " "*4, spotify.Link.from_track(t, 0), t.name()
                get_cover_art(t, self.session)
            else:
                print "Track not found"
            self.waiting = False
        self.session.search(line, search_finished)
        while self.waiting:
            time.sleep(.05)
            pass

    
    def _get_track(self, line):
        try:
            rec_num = int(line)
            source = self.recs
        except ValueError, ve:
            rec_num = None
        
        if rec_num == None and line.startswith('p'):
            try:
                rec_num = int(line[1:])
                source = self.playlist
            except ValueError, ve:
                rec_num = None
            
        if rec_num != None:    
            if rec_num < 1 or rec_num > len(source):
                print "Invalid Number"
                return -1
            else:
                return source[rec_num - 1]
        else:
            return None
        
    def _parse_track_info(self, line):
        track = self._get_track(line)
        if track == -1: return
        
        if track:
            return track.artists()[0], track.name()
        else:
            match = re.search('artist:(?:"([^"]+)"|(\\w+))', line)
            artist = match.group(1) or match.group(2)
            match = re.search('title:(?:"([^"]+)"|(\\w+))', line)
            title = match.group(1) or match.group(2)
            return artist, title

    def do_album(self, line):
        track = self._get_track(line)
        if track == -1 or not track: return
        alb = track.album()
        def browse_finished(album_browse):
            for i, t in enumerate(album_browse):
                print " "*4 + "%2d: %s  -  (%s) %s" % (i,
                                                   spotify.Link.from_track(t, 0),
                                                  t.artists()[0],
                                                  t.name())                                               
            sys.stdout.flush
            self.waiting -= 1
        self.waiting = 1

        #FIXME: the callback is never actually called in pyspotify
        browser = self.session.browse_album(alb, browse_finished)
        while not browser.is_loaded():
            time.sleep(.05)
        while not alb.is_loaded():
            time.sleep(.05)
        print alb.name()

    def do_r(self, line):
        self.do_recommend(line)
    
    def do_recommend(self, line):
        artist, title = self._parse_track_info(line)
        print "(%s) %s" % (artist, title)
        recs = panko.command.recommend.recommend(artist, title)
        
        if not recs:
            print "No Recommendations Found"
            return
            
        self.count = 0
        self.recs = []
        def search_finished(results, userdata):
            tracks = results.tracks()
            if tracks:
                self.count += 1
                t = tracks[0]
                self.recs.append(t)
                print " "*4 + "%2d: %s  -  (%s) %s" % (self.count,
                                                   spotify.Link.from_track(t, 0),
                                                  t.artists()[0],
                                                  t.name())                                               
            else:
                print "      Track not found                       -  %s" % results
            sys.stdout.flush
            self.waiting -= 1

        self.waiting = 0
        for i, r in enumerate(recs):
            self.waiting += 1
            spotify_query = "artist:%s title:%s" % (r['artist'], r['title'])
            self.session.search(spotify_query, search_finished)
            
        while self.waiting:
            time.sleep(.05)
            pass


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="spotify username", default='124903567')
    parser.add_argument("-p", "--password", help="spotify password")
    args = parser.parse_args()
    session_m = SessionManager(args.username, args.password, True)
    session_m.connect()
