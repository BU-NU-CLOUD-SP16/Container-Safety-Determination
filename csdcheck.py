import os
import sys
import shutil
import subprocess as sub

# cmd is a list: cmd and options if any
def exec_cmd(cmd):
    p = sub.Popen(cmd,stdout=sub.PIPE,stderr=sub.PIPE)
    output, errors = p.communicate()
    print errors
    #print output
    return output
    # todo handle errors


def untarlayers(imagedir):    
    for d in os.listdir(imagedir):
        layerdir = os.path.join(imagedir,d)
        if os.path.isdir(layerdir):          
            layertar =  os.path.join(layerdir,'layer.tar')            
            exec_cmd(['tar','-xvf',layertar,'-C',layerdir])
            os.remove(layertar)


# imagename should be in the form image:tag
# Example test: python csdcheck.py python:2.7.8-slim
imagename = sys.argv[1]

print('docker pull...')
exec_cmd(['docker','pull',imagename])

tmpdir = os.path.join(os.getcwd(), 'tmp')
os.makedirs(tmpdir)

imagetar = os.path.join(tmpdir,'image.tar')
imagedir = os.path.join(tmpdir,'image')
os.makedirs(imagedir)

print('docker save...')
exec_cmd(['docker','save','-o',imagetar,imagename])
print('untar...')
exec_cmd(['tar','-xvf',imagetar,'-C',imagedir])
os.remove(imagetar)
untarlayers(imagedir)

print('sdhashing...')
outputfile = os.path.join(os.getcwd(), 'sdhashed')
exec_cmd(['sdhash','-r',imagedir,'-o',outputfile])

#todo cleanup: remove tmp dir
