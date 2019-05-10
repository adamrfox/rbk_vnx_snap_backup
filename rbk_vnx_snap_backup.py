#!/usr/bin/python

import sys
import os
import getpass
import getopt
import urllib3
import paramiko
import rubrik_cdm
urllib3.disable_warnings()


def usage():
    sys.stderr.write("Usage: rbk_vnx_snap_backup.py [-hvD] [-c creds] [-d data_mover] vnx filesystem path rubrik\n")
    sys.stderr.write("-h | --help : Prints this message\n")
    sys.stderr.write("-v | --verbose : Verbose mode, prints more messages\n")
    sys.stderr.write("-D | --DEBUG : Debug mode.  Prints out more info\n")
    sys.stderr.write("-c | --creds= : Use a file for credentials\n")
    sys.stderr.write("-d | --data_mover= : Set the (virtual) data mover [default: server_2]\n")
    sys.stderr.write("vnx : Hostname or IP of the Control Station of the VNX\n")
    sys.stderr.write("share : Share name.  For NFS put the path starting the /, for SMB, put the share name.\n")
    sys.stderr.write("path : Local path for the filesystem\n")
    sys.stderr.write("rubrik : Hostname or IP of the Rubrik\n")
    exit(0)

def vprint(message):
    if verbose:
        print message
    return()

def get_creds_from_file(file, array):
    with open(file) as fp:
        data = fp.read()
    fp.close()
    data = data.decode('uu_codec')
    data = data.decode('rot13')
    lines = data.splitlines()
    for x in lines:
        if x == "":
            continue
        xs = x.split(':')
        if xs[0] == array:
            user = xs[1]
            password = xs[2]
    return (user, password)

def find_latest_ckpt(path):
    snaps = os.listdir(path + "/.ckpt")
    latest = "1970-01-01-01.00.00"
    for ckpt in snaps:
        if ckpt > latest:
            latest = ckpt
    return(latest)



if __name__ == "__main__":
    user = ""
    password = ""
    vnx_user = ""
    vnx_password = ""
    path = ""
    filesystem = ""
    rubrik_host = ""
    rbk_ip_list = []
    dm = "server_2"
    verbose = False
    DEBUG = False

    optlist, args = getopt.getopt(sys.argv[1:], 'hvc:dD:', ['--help', '--verbose', '--creds=', '--data_mover=', '--debug'])
    for opt, a in optlist:
        if opt in ('-h', '--help'):
            usage()
        if opt in ('-v', '--verbose'):
            verbose = True
        if opt in ('-c' '--creds'):
            (user, password) = get_creds_from_file(a, 'rubrik')
            (vnx_user, vnx_password) = get_creds_from_file(a, 'vnx')
        if opt in ('d', '--data_mover'):
            dm = a
        if opt in ('-D', '--debug'):
            DEBUG = True
    if args[0] == "?":
        usage()
    if user == "":
        user = raw_input("User: ")
    if password == "":
        password = getpass.getpass("Password: ")
    if vnx_user == "":
        vnx_user = raw_input("VNX User: ")
    if vnx_password == "":
        vnx_password = getpass.getpass("VNX Password: ")
    (vnx_host, filesystem, path, rubrik_host) = args
    if filesystem.startswith("/"):
        share_type = "NFS"
    else:
        share_type = "SMB"
        share_name = filesystem
        filesystem = "/" + filesystem

# Set up Rubrik API Session and grab IP addresses if share is NFS

    rubrik = rubrik_cdm.Connect(rubrik_host, user, password)
    if share_type == "NFS":
        rbk_net = rubrik.get('internal', '/cluster/me/network_interface')
        for i in rbk_net['data']:
            for j in i['ipAddresses']:
                rbk_ip_list.append(j)
        ip_list_str = ':'.join(rbk_ip_list)

# Set up ssh session for VNX.  grab the current shares and find one with .ckpt in the path and delete it

    vnx = paramiko.SSHClient()
    vnx.set_missing_host_key_policy(paramiko.client.AutoAddPolicy)
    vnx.connect(vnx_host, username='root', password='nasadmin')
    cmd = 'export NAS_DB=/nas ; /nas/bin/server_export ' + dm
    stdin, stdout, stderr = vnx.exec_command(cmd)
    for line in stdout:
        if share_type == "NFS" and not line.startswith("export"):
            continue
        elif share_type == "SMB" and not line.startswith("share"):
            continue
        lf = line.split()
        lf1 = lf[1].split('"')
        if lf1[1].startswith(filesystem + "/.ckpt/"):
            vprint ("Deleting old ckpt export: :" + lf1[1])
            if share_type == "NFS":
                cmd = "export NAS_DB=/nas ; /nas/bin/server_export " + dm + " -Protocol nfs -unexport " + lf1[1]
            else:
                cmd = "export NAS_DB=/nas ; /nas/bin/server_export " + dm + " -Protocol cifs -unexport " + lf1[1]
            stdin, stdout, stderr = vnx.exec_command(cmd)

# Find the latest checkpoint and create an export/share to it

    latest_ckpt = find_latest_ckpt(path)
    vprint("Creating export for " + latest_ckpt)
    if share_type == "NFS":
        cmd = "export NAS_DB=/nas ; /nas/bin/server_export " + dm + " -Protocol nfs -option access=" + ip_list_str + ":root=" + ip_list_str + " " + filesystem + "/.ckpt/" + latest_ckpt
    else:
        cmd = "export NAS_DB=/nas ; /nas/bin/server_export " + dm + " -Protocol cifs -name " + share_name + " " + filesystem + "/.ckpt/" + latest_ckpt
    if DEBUG:
        print cmd
    stdin, stdout, stderr = vnx.exec_command(cmd)

# If NFS, update the export on Rubrik to point to the new ckpt path

    if share_type == "NFS":
        rubrik_nfs = rubrik.get('internal','/host/share?share_type=' + share_type)
        for ex in rubrik_nfs['data']:
            export_path = str(ex['exportPoint'])
            if export_path.startswith(filesystem + "/.ckpt"):
                print("Updating Share on Rubrik")
                payload = {"exportPoint": filesystem + "/.ckpt/" + latest_ckpt}
                endpoint = "/host/share/" + str(ex['id'])
                rbk_share = rubrik.patch('internal', endpoint, payload)
                break
















