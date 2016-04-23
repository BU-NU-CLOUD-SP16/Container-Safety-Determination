import socket
import subprocess


# cmd is a list: cmd and options if any
def exec_cmd(cmd):
    p = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    output, errors = p.communicate()
    if len(errors.strip()) > 0:
        print cmd, ' >>> ', errors
        return None
    return {"output": output, "retcode": p.returncode}
    # todo handle errors


# Example to start a container with all services in it
# docker run -d -p 9001:9999 -v /var/run/docker.sock:/var/run/docker.sock cloudscan
# TODO: to be refactored so that the call is more generic
def start_container(image):
    port = get_free_port()
    port_binding = str(port) + ":9999"
    daemon = "/var/run/docker.sock:/var/run/docker.sock"
    cmd = ['docker', 'run', '-d', '-p', port_binding, '-v', daemon, image]
    resp = exec_cmd(cmd)
    if resp["retcode"] == 0:
        return {"cid": resp["output"], "port": port}
    else:
        return None


# login to registry within the container
def registry_login(cid, registry, uname, passwd, email):
    subcmd = "docker login --username=%s --password=%s --email=%s %s"  \
             % (uname, passwd, email, registry)
    cmd = ['docker', 'exec', '-it', cid, 'bash', '-c', subcmd]
    return exec_cmd(cmd)


def get_free_port():
    s = socket.socket()
    s.bind(('', 0))
    port = s.getsockname()[1]
    s.close()
    return port


def spawn_instance(image, registry, uname, passwd, email):
    resp = start_container(image)
    if resp == None:
        print "Fatal error: failed spawning a new container"
        return resp
    else:
        port = resp["port"]
        cid = resp["cid"]
        ret = registry_login(cid, registry, uname, passwd, email)
        if ret != None:
            return resp
        else:
            print "Failed to login to registry. Killing the instance"
            kill_instance(cid)
            return None


def kill_instance(id):
    cmd = ['docker', 'kill', id]
    return exec_cmd(cmd)