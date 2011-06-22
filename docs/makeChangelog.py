#!/usr/bin/env python

import sys
import subprocess

# Makes a GNU-Style ChangeLog from a git repository
# Handles git-svn repositories also

# Arguments : same as for git log


def process_commit(lines, files):
    # DATE NAME
    # BLANK LINE
    # Subject
    # BLANK LINE
    # ...
    # FILES
    fileincommit = False
    lines = [x.strip() for x in lines if x.strip() and not x.startswith('git-svn-id')]
    files = [x.strip() for x in files if x.strip()]
    for l in lines:
        if l.startswith('* ') and ':' in l:
            fileincommit = True
            break
    top_line = lines[0]
    print top_line.strip()
    print
    if not fileincommit:
        for f in files:
            print '\t* %s:' % f
    for l in lines[1:]:
        print '\t ', l
    print

if __name__ == "__main__":
    cmd = ['git', 'log', '--pretty=format:--START-COMMIT--%n%ad  %an <%ae>%n%n%s%n%b%n--END-COMMIT--',
           '--date=short', '--name-only']
    cmd.extend(sys.argv[1:])
    p = subprocess.Popen(args=cmd, shell=False, stdout=subprocess.PIPE)
    buf = []
    files = []
    filemode = False
    for lin in p.stdout.readlines():
        if lin.startswith("--START-COMMIT--"):
            if buf != []:
                process_commit(buf, files)
                buf = []
                files = []
                filemode = False
        elif lin.startswith("--END-COMMIT--"):
            filemode = True
        elif filemode == True:
            files.append(lin)
        else:
            buf.append(lin)
    if buf != []:
        process_commit(buf, files)
