import os
import sys
import shutil
import subprocess as sub

# cmd is a list: cmd and options if any
def exec_cmd(cmd):
    p = sub.Popen(cmd,stdout=sub.PIPE,stderr=sub.PIPE)
    output, errors = p.communicate()
    if len(errors.strip()) > 0:
        print errors
    return output
    # todo handle errors

srcdir = '/path/to/ubuntudir'
dstdir = '/path/to/outputdir'

# For each file in srcdir, calculate sdhash and write to file in dstdir
# Example: sdhash for file srcdir/usr/local/bin/prog1 will be written to dstdir/usr/local/bin/prog1

for root, subdirs, files in os.walk(srcdir):
    for subdir in subdirs:
        sub_path = os.path.join(root, subdir)
        sub_dest = sub_path.replace(srcdir,dstdir,1)
        if not os.path.exists(sub_dest):
            os.makedirs(os.path.join(sub_dest))
    
    for filename in files:
        file_path = os.path.join(root, filename)
        file_dest = file_path.replace(srcdir,dstdir,1)
        
        res = exec_cmd(['sdhash',file_path])
        with open(file_dest, 'w') as f:
            f.write(res)
