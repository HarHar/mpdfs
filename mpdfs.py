#!/usr/bin/env python
# -*- coding: utf-8 -*-
import errno
import fuse
import stat
import time
import os
import mpd
import traceback
from dateutil.relativedelta import relativedelta
import threading

fuse.fuse_python_api = (0, 2)

clientnum = 5
clients = []
for x in xrange(0, clientnum):
    clients.append(mpd.MPDClient())
    clients[x].connect('127.0.0.1', 6600) #changeme

def prettify(d):
    if isinstance(d, dict):
        out = ''
        for key in d:
            out += key + ': ' + d[key] + '\n'
    elif isinstance(d, list):
        out = ''
        for item in d:
            if isinstance(item, basestring):
                out += item + '\n'
            else: out += repr(item) + '\n'
    elif isinstance(d, basestring):
        return d
    else:
        out = repr(d)
    return out + '\n'

def groupFiles(files):
    out = {'files': [], 'dirs': {}}
    for f in files:
        s = f.split('/')
        workingFolder = out
        for folder in s[:-1]:
            if workingFolder['dirs'].get(folder, 0) == 0:
                workingFolder['dirs'][folder] = {'files': [], 'dirs': {}}
            workingFolder = workingFolder['dirs'][folder]
        workingFolder['files'].append(s[-1])
    return out

def di5tuiw(func, *args):
    #di5tuiw stands for "do it five times until it works"
    tries = 0
    loop = True
    while loop:
        tries += 1
        if tries > 5: return
        loop = False
        try:
            ret = func(*args)
            break
        except:
            for x in xrange(0, clientnum):
                clients[x].disconnect()
                clients[x].connect('127.0.0.1', 6600) #changeme
            loop = True
    return ret

###################################################################
# And here comes the biggest and most useful thread on the world: #
###################################################################
def pingThread(client):
    while True: di5tuiw(client.ping); time.sleep(5)
###################################################################

attrs = ['years', 'months', 'days', 'hours', 'minutes', 'seconds']
human_readable = lambda delta: ['%d %s' % (getattr(delta, attr), getattr(delta, attr) > 1 and attr or attr[:-1]) for attr in attrs if getattr(delta, attr)]

class FS(fuse.Fuse):
    # DON'T LOSE YOUR WAAAY
    structure = {'/': {'.': {'type': 'd'}, '..': {'type': 'd'}, \
    'control': {'type': 'f'}, 'help': {'type': 'f'}, \
    'playlist': {'type': 'd'}, 'files': {'type': 'd'}, \
    'debug': {'type': 'f', 'hidden': True}, \
    'status': {'type': 'f'}, 'play': {'type': 'd'},
    'executables': {'type': 'd'}}, \

    '/files': {'.': {'type': 'd'}, '..': {'type': 'd'}, \
    'Malukah - Age of Oppression': {'type': 'f'}},

    '/play': {'.': {'type': 'd'}, '..': {'type': 'd'},
    'readme': {'type': 'f'}},

    '/executables': {'.': {'type': 'd'}, '..': {'type': 'd'},
    'play.sh': {'type': 'f', 'mode': 0777},
    'pause.sh': {'type': 'f', 'mode': 0777},
    'stop.sh': {'type': 'f', 'mode': 0777},
    'clear.sh': {'type': 'f', 'mode': 0777}} \
    }

    fixedcontents = {'/help': """
    Don't let it fool you, this folder is
    an MPD client, explore it a bit.
    """, '/control': """
    Try writing "play" or "pause" to me, using
    either your favorite text editor or
    doing "echo play > control"
    """, '/play/readme': """
    Tip: copy a file from the "files" folder to me
    and the music will start
    """}

    exists = []

    files = None

    def __init__(self, *args, **kw):
        fuse.Fuse.__init__(self, *args, **kw)
        self.files = groupFiles(di5tuiw(clients[0].list, 'file'))

    def fsinit(self, *args, **kwargs):
        for client in clients:
            thread = threading.Thread(target=pingThread, args=(client,))
            thread.setDaemon(True)
            thread.start()

    def getattr(self, path):
        folder = '/'.join((path).split('/')[:-1]) or '/'
        st = fuse.Stat()

        #I CAME FROM THE FUUUUUUUTURE
        st.st_atime = 1528995828
        st.st_mtime = 1528995828
        st.st_ctime = 1528995828

        st.st_mode = stat.S_IFDIR | 0755
        st.st_nlink = 2
        if path == '/': return st

        if path.startswith('/files'):
            filename = path.split('/')[-1]
            path = '/'.join(path.split('/')[2:-1])
            if not path:
                if filename in self.files['files']:
                    st.st_mode = stat.S_IFREG | 0666
                    st.st_nlink = 1
                    st.st_size = 1024**2
            else:
                s = path.split('/')
                workingFolder = self.files
                for f in s:
                    if workingFolder['dirs'].get(f, 0) != 0:
                        workingFolder = workingFolder['dirs'][f]
                    else: return -errno.ENOENT
                if filename in workingFolder['files']:
                    st.st_mode = stat.S_IFREG | 0666
                    st.st_nlink = 1
                    st.st_size = 1024**2
            return st
        elif folder in self.structure:
            if os.path.basename(path) in self.structure[folder]:
                if self.structure[folder][os.path.basename(path)]['type'] == 'f':            
                    mode = self.structure[folder][os.path.basename(path)].get('mode', 0666)
                    st.st_mode = stat.S_IFREG | mode
                    st.st_nlink = 1
                    st.st_size = 1024**2
                return st

        if path in self.exists:
            st.st_mode = stat.S_IFREG | 0777
            st.st_nlink = 1
            st.st_size = 1024**3
            self.exists.remove(path)
            return st
        return -errno.ENOENT
    def fgetattr(self, path):
        return self.getattr(path)
    def readdir(self, path, offset):
        if path.startswith('/files'):
            path = '/'.join(path.split('/')[2:])
            if not path:
                for f in self.files['files']:
                    yield fuse.Direntry(f)
                for d in self.files['dirs']:
                    yield fuse.Direntry(d)
            else:
                s = path.split('/')
                workingFolder = self.files
                for f in s:
                    if workingFolder['dirs'].get(f, 0) != 0:
                        workingFolder = workingFolder['dirs'][f]
                    else: raise -errno.ENOENT
                for f in workingFolder['files']:
                    yield fuse.Direntry(f)
                for d in workingFolder['dirs']:
                    yield fuse.Direntry(d)
        elif path in self.structure:
            for e in sorted(self.structure[path], key=lambda x: self.structure[path][x]['type']):
                if self.structure[path][e].get('hidden'): continue
                yield fuse.Direntry(e)
    def mkdir(self, path, mode):
        return -errno.ENOSYS
    def open(self, path, offset):
        return 0
    def read(self, path, size, offset):
        out = ''
        if path in self.fixedcontents:
            out = self.fixedcontents[path] + '\n'
        elif path.startswith('/files/'):
            folder = '/'.join(path.split('/')[2:-1])
            folderinfo = di5tuiw(clients[1].lsinfo, folder)
            for entry in folderinfo:
                if entry.get('directory', 0) != 0: continue
                if entry['file'].split('/')[-1] == path.split('/')[-1]:
                    out += 'filename: ' + entry['file'] + '\n'
                    out += 'length: ' + (', '.join(human_readable(relativedelta(seconds=int(entry['time']))))) + '\n'
                    out += '\n'
                    out += ('title: ' + entry.get('title', 'not available') + '\n') if entry.get('title', 0) != 0 else ''
                    out += ('artist: ' + entry.get('artist', 'not available') + '\n') if entry.get('artist', 0) != 0 else ''
                    out += ('track: ' + entry.get('track', 'not available') + '\n') if entry.get('track', 0) != 0 else ''
                    out += ('album: ' + entry.get('album', 'not available') + '\n') if entry.get('album', 0) != 0 else ''
                    out += ('year: ' + entry.get('year', 'not available') + '\n') if entry.get('year', 0) != 0 else ''
                    break
        elif path == '/debug':
            out += repr(clients) + '\n'
        elif path == '/status':
            out += prettify(di5tuiw(clients[0].status)) + '--------------\n\n' + prettify(di5tuiw(clients[0].stats))

        if path.startswith('/executables'):
            out = '#!/bin/true\n'
            if path.endswith('/play.sh'):
                di5tuiw(clients[2].play)
            elif path.endswith('/pause.sh'):
                di5tuiw(clients[2].pause)
            elif path.endswith('/stop.sh'):
                di5tuiw(clients[2].stop)
            elif path.endswith('/clear.sh'):
                di5tuiw(clients[2].clear)

        if out:
            slen = len(out)
            if offset < slen:
                if offset + size > slen:
                    size = slen - offset
                buf = out[offset:offset+size]
            else: buf = ''
            if isinstance(buf, unicode):
                return buf.encode('utf8')
            else:
                return buf
        else: return 'Could not read anything, sorry\n'
    def write(self, path, buf, offset):
        #we ignore offset
        slen = len(buf)
        if buf == '': return 0
        if path == '/control':
            buf = buf.strip().replace('\n', '')
            args = buf.split(' ')[1:]
            try:
                ret = di5tuiw(getattr(clients[0], buf.split(' ')[0], *args))
                ret = prettify(ret or 'Successfully executed \'' + buf.split(' ')[0] + '\'')
                self.fixedcontents[path] = ret
            except AttributeError, e:
                self.fixedcontents[path] = 'No command "' + buf.split(' ')[0] + '"'
            except Exception, e:
                self.fixedcontents[path] = 'Error...\n ' + traceback.format_exc()
                if str(e).find('Connection lost') != -1:
                    self.fixedcontents[path] += '\nConnection lost, restoring connection on all channels...'
                    for x in xrange(0, clientnum):
                        clients[x].disconnect()
                        clients[x].connect('127.0.0.1', 6600) #changeme
                    self.fixedcontents[path] += ' done!\n'
        elif path.startswith('/play/'):
            if buf.startswith('filename:'):
                buf = buf.split('\n')[0]
                buf = buf.split(':')[1]
                buf = buf.strip()
                di5tuiw(clients[3].clear)
                di5tuiw(clients[3].add, buf)
                di5tuiw(clients[3].play)
        return slen

    def unlink(self, path):
        if path.startswith('/files/'):
            fullpath = path.replace('/files/', '')
            di5tuiw(clients[4].clear)
            di5tuiw(clients[4].add, fullpath)
            di5tuiw(clients[4].play)

    def getxattr(self, path, name, size):
        return -errno.ENOTSUP

    def setxattr(self, path, name, value, options, position=0):
        return -errno.ENOTSUP

    def flush(self, *args, **kwargs):
        return 0

    def chmod(self, path, mode):
        pass

    def chown(self, path, uid, gid):
        pass

    def fsync(self, path, isFsyncFile):
        pass

    def symlink(self, targetPath, linkPath):
        pass

    def mkdir(self, path, mode):
        pass

    def create(self, path, mode, info):
        self.exists.append(path)

    def mknod(self, path, mode, dev):
        pass

    def truncate(self, path, size):
        pass

    def ftruncate(self, path, size):
        pass

    def utime(self, path, times):
        return 0

    def utimens(self, path, times, dummy=None):
        return 0

    def access(self, path, mode):
        pass

    def release(self, path, fh=None):
        pass

if __name__ == '__main__':
    fs = FS()
    fs.parse(errex=1)
    fs.multithreaded = 0
    fs.main()
