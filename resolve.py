#!/usr/bin/env python

import os
import subprocess
import threading
import cmd
import time
import StringIO
import panko.command.recommend
import re
import sys
import unicodedata

import PIL.Image

import spotify
import spotify.manager

_CMD_SEQ_PLAY = ['osascript', 'spotify_play.scpt']

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
            
class Listings(object):
    
    __slots__ = ['seed',
                 'similar_tracks',
                 'album_tracks', 
                 'search_tracks',
                 'artist_albums',
                 'playlist',
                 'current']
                 
    def __init__(self):
        self.seed = None
        self.similar_tracks = []
        self.album_tracks = []
        self.search_tracks = []
        self.artist_albums = []
        self.playlist = []
        self.current = None
        
    def current_item(self, index):
        return self.current[index]
        
    def current_type(self):
        if self.current == None:
            return None
        if self.current is self.similar_tracks \
        or self.current is self.album_tracks \
        or self.current is self.playlist \
        or self.current is self.search_tracks:
            return 'track'
        else:
            return 'album'
        
    def set_current(self, listing):
        self.current = getattr(self, listing)
    
class CommandLine(cmd.Cmd, threading.Thread):
    prompt = 'rspot> '
    
    def __init__(self, session):
        cmd.Cmd.__init__(self)
        threading.Thread.__init__(self)
        self.session = session
        self.listings = Listings()
        
    def run(self):
        self.cmdloop()
        
    def do_add(self, line):
        if line == 'seed' and self.listings.seed:
            track = self.listings.seed
        else:
            track = self._get_track(line)

        if track:
            self.listings.playlist.append( track )

    def do_pop(self, line):
        if self.listings.current is self.listings.playlist:
            if self.listings.playlist:
                try:
                    idx = int(line)
                except:
                    idx = None
                    
                if idx and idx > 0 and idx < len(self.listings.playlist):
                    self.listings.playlist.pop(idx-1)
                else:
                    self.listings.playlist.pop()
                    
                self.do_playlist(None)
     
    def do_pl(self, line):
        self.do_playlist(line)
               
    def do_playlist(self, line):
        self._activate_track_listing('playlist')
        
    def do_p(self, line):
        self.do_play(line)
        
    def do_play(self, line):
        track = self._get_track(line)
        if not track:
            return
        
        uri = spotify.Link.from_track(track, 0)
        print "playing (%s) %s..." % (track.artists()[0], track.name())
        shell_cmd = ['osascript', 'spotify_play.scpt', str(uri)]
        subprocess.call(shell_cmd)
    
    def _activate_track_listing(self, listing):
        self.listings.set_current(listing)
        for i, t in enumerate(self.listings.current):
            if t.popularity() == 0:
                popularity = " " * 10
            else:
                popularity = "|" * (t.popularity() / 10)
                popularity = popularity.ljust(10, '.') 

            print " "*4 + "[ %s ]  %s  %2d. (%s) %s" \
                  % (spotify.Link.from_track(t, 0),
                     popularity,
                     i+1,
                     t.artists()[0],
                     t.name())                                               

    def _activate_album_listing(self, listing):
        self.listings.set_current(listing)
        for i, a in enumerate(self.listings.current):
            print " "*4 + "[ %s ]  %2d. %s" % (spotify.Link.from_album(a),
                                           i+1,
                                           a.name() )                                               

    def _get_track(self, line):
        try:
            rec_num = int(line)
            source = self.listings.current
        except ValueError, ve:
            rec_num = None

        if rec_num != None:    
            if self.listings.current_type() != 'track':
                print "Command only works on tracks"
                return None

            if rec_num < 1 or rec_num > len(source):
                print "Invalid Number"
                return None
            else:
                return source[rec_num - 1]
        else:
            return None
        
    def _get_album(self, line):
        try:
            rec_num = int(line)
            source = self.listings.current
        except ValueError, ve:
            rec_num = None

        if rec_num != None:    
            if self.listings.current_type() != 'album':
                print "Command only works on albums"
                return None

            if rec_num < 1 or rec_num > len(source):
                print "Invalid Number"
                return None
            else:
                return source[rec_num - 1]
        else:
            return None

    def _parse_track_info(self, line):
        try:
            match = re.search('artist:(?:"([^"]+)"|(\\w+))', line)
            artist = match.group(1) or match.group(2)
            match = re.search('title:(?:"([^"]+)"|(\\w+))', line)
            title = match.group(1) or match.group(2)
            return artist, title
        except:
            return None
            
    def do_artist(self, line):
        if not line:
            self._activate_album_listing('artist_albums')            
            return
            
        track = self._get_track(line)
        if not track:
            return
        
        artist = track.artists()[0]
        print "(%s)" % artist
        def search_finished(results, userdata):
            albums = results.albums()
            if not albums:
                print "      No Albums found for %s" % results
            self.waiting = False
            self.listings.artist_albums = albums
                
        self.waiting = True
        spotify_query = "artist:%s" % artist
        self.session.search(spotify_query, search_finished)
        while self.waiting:
            time.sleep(.05)
            pass
        self._activate_album_listing('artist_albums')

    def do_album(self, line):
        if not line:
            self._activate_album_listing('album_tracks')            
            return

        track = self._get_track(line)
        if track:
            alb = track.album()
        else:
            alb = self._get_album(line)

        if not alb:
            return
            
        while not alb.is_loaded():
            time.sleep(.05)
        print "(%s) %s" % (alb.artist(), alb.name())
        tracks = []
        def browse_finished(album_browse):
            tracks.extend(album_browse)
            self.waiting -= 1
        self.waiting = 1

        #FIXME: the callback is never actually called in pyspotify
        browser = self.session.browse_album(alb, browse_finished)
        while not browser.is_loaded():
            time.sleep(.05)
        self.listings.album_tracks = tracks
        self._activate_track_listing('album_tracks')
        


    def _search_for_track(self, line):
        self.waiting = True
        self.tmp_result = []
        def search_finished(results, userdata):
            self.tmp_result = results.tracks()
            if not self.tmp_result:
                print "Track not found"
            self.waiting = False
        self.session.search(line, search_finished)
        while self.waiting:
            time.sleep(.05)
            pass
        return self.tmp_result
        
    def do_track(self, line):
        if not line:
            self._activate_track_listing('search_tracks')
            return
             
        self.listings.search_tracks = self._search_for_track(line)
        self._activate_track_listing('search_tracks')
           
    def do_s(self, line):
        self.do_similar(line)

    def do_similar(self, line):
        if not line:
            self._activate_track_listing('similar_tracks')
            return
        
        track = self._get_track(line)
        if not track:
            tracks = self._search_for_track(line)
            if tracks:
                track = tracks[0]
        if not track:
            return

        self.listings.seed = track
        artist, title = unicode(track.artists()[0]), unicode(track.name())
        artist = unicodedata.normalize('NFKD', artist).encode('ASCII', 'ignore')
        title = unicodedata.normalize('NFKD', title).encode('ASCII', 'ignore')
        print "(%s) %s" % (artist, title)
        recs = panko.command.recommend.recommend(artist, title)
        
        if not recs:
            print "No Recommendations Found"
            return
            
        self.count = 0
        similar = []
        def search_finished(results, userdata):
            tracks = results.tracks()
            if tracks:
                self.count += 1
                t = tracks[0]
                similar.append(t)
            else:
                print "        Track not found                       -  %s" % results
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
        self.listings.similar_tracks = similar
        self._activate_track_listing('similar_tracks')
        

if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("-u", "--username", help="spotify username", default='124903567')
    parser.add_argument("-p", "--password", help="spotify password")
    args = parser.parse_args()
    session_m = SessionManager(args.username, args.password, True)
    time.sleep(.1)
    session_m.connect()
