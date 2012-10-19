#!/usr/bin/python
import os
import re
import pprint
import sys
from urlparse import urlparse

def parse_entry(entry):
  """Parse a line from the Apache log

  Log entries are of this format:
  127.0.0.1 - - [23/Dec/2010:13:10:30 -0500] "GET /favicon.ico HTTP/1.1" 200 1406
  127.0.0.1 - - [23/Dec/2010:13:10:30 -0500] "GET /jw/jw-trial-config.xml HTTP/1.1" 200 762

  Args:
    entry: a string representing a single line from a log file

  Returns:
    A dict mapping the elements of a request to their string values
  """
  fields = {}

  raw = entry.split()
  if len(raw) != 10:
    return fields
  else:
    fields['ip'] = raw[0]
    fields['datetime'] = {
        'date': raw[3][1:12],
        'time': raw[3][13:],
        'offset':   raw[4][:-1]
        }
    fields['request'] = {
        'method': raw[5][1:],
        'path': raw[6],
        'protocol': raw[7][:-1]
        }
    fields['response'] = {
        'status': raw[8],
        'size': raw[9]
        }
    return fields


def parse_log(logfile):
  root = {}
  dirpattern = re.compile('/([^/]*)')
  phppattern = re.compile('\.php$')

  '''
   open log file
  '''
  try:
    fh = open(logfile, 'r')
  except IOError, e:
    if e[0] == 2:
      msg = 'Log file \'' + logfile  + '\' does not exist'
    else:
      msg = 'There was an error opening \'' + logfile + '\':\n  "Error %d,%s"\n' % (e[0], e[1])
    finish_job(msg, 1)


  for entry in fh:
    fields = parse_entry(entry)
    # should have 10 fields, if not just move on
    if not len(fields):
      continue

    rmethod = fields['request']['method']
    rpath   = fields['request']['path']
    rstatus = fields['response']['status']
    rsize   = fields['response']['size']

    # if the response size is non-zero and the response code is a number
    if rsize.isdigit() and rstatus.isdigit():
      rstatus = int(rstatus)
      # skip if response code other than 2xx
      if rstatus >= 300 or rstatus < 200:
        continue

      rpath = urlparse(rpath)
      # rpath is a tuple a la ('scheme', 'netloc', 'path', 'params', 'query', 'fragment')
      path, file = os.path.split(rpath[2])
      query =  rpath[4]

      # if no file specified then index.php would be what was served
      if not file:
        file = 'index.php'
      # if no path then we're in the web root
      if not path:
        path = 'root'

      # if not a php or html doc, skip it
      extension = os.path.splitext(file)[1].lstrip('.').lower()
      if not extension == 'php' and not extension == 'html':
        continue

      current = root
      if not path == 'root':
        dirs = re.findall(dirpattern, path)
        if dirs[0] == 'blogs':
          continue
        for dir in dirs:
          if re.search(phppattern, dir):
            file = dir
            break
          elif dir == '':
            continue
          elif not dir in current:
            current[dir] = {}
          current = current[dir]

      if not file in current:
        current[file] = None

  fh.close()
  return {'root':root}


def finish_job(msg=None, status=0):
  if msg:
    print msg
  sys.exit(status)


def main():
  if sys.argv[1:]:
    logfile = sys.argv[1]
  else:
    finish_job('No logfile given', 1)

  tree = parse_log(logfile)

  pp = pprint.PrettyPrinter()
  pp.pprint(tree['root'])

  finish_job()

if __name__ == '__main__':
  main()
