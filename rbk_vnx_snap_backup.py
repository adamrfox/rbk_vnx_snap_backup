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
    print "Usage goes here!"
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
    latest = ["1970", "01" "01" "01.00.00"]
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

    optlist, args = getopt.getopt(sys.argv[1:], 'hvc:d:', ['--help', '--verbose', '--creds=', '--data_mover='])
    for opt, a in optlist:
        if opt in ('-h', '--help'):
            usage()
        if opt in ('-v', '--verbose'):
            verbose = True
        if opt in ('-c' '--creds'):
            if ':' in a:
                (user, password) = a.split(':')
            else:
                (user, password) = get_creds_from_file(a, 'rubrik')
                (vnx_user, vnx_password) = get_creds_from_file(a, 'vnx')
        if opt in ('d', '--data_mover'):
            dm = a
    if user == "":
        user = raw_input("User: ")
    if password == "":
        password = getpass.getpass("Password: ")
    (vnx_host, filesystem, path, rubrik_host) = args
    if filesystem.startswith("/"):
        share_type = "NFS"
    else:
        share_type = "SMB"
        share_name = filesystem
        filesystem = "/" + filesystem
    rubrik = rubrik_cdm.Connect(rubrik_host, user, password)
    if share_type == "NFS":
        rbk_net = rubrik.get('internal', '/cluster/me/network_interface')
        for i in rbk_net['data']:
            for j in i['ipAddresses']:
                rbk_ip_list.append(j)
        ip_list_str = ':'.join(rbk_ip_list)
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
    latest_ckpt = find_latest_ckpt(path)
    vprint("Creating export for " + latest_ckpt)
    if share_type == "NFS":
        cmd = "export NAS_DB=/nas ; /nas/bin/server_export " + dm + " -Protocol nfs -option access=" + ip_list_str + ":root=" + ip_list_str + " " + filesystem + "/.ckpt/" + latest_ckpt
    else:
        cmd = "export NAS_DB=/nas ; /nas/bin/server_export " + dm + " -Protocol cifs -name " + share_name + " " + filesystem + "/.ckpt/" + latest_ckpt
    print cmd
    stdin, stdout, stderr = vnx.exec_command(cmd)
    rubrik_nfs = rubrik.get('internal','/host/share?share_type=' + share_type)
    if share_type == "NFS":
        for ex in rubrik_nfs['data']:
            export_path = str(ex['exportPoint'])
            if export_path.startswith(filesystem + "/.ckpt"):
                print("Updating Share on Rubrik")
                payload = {"exportPoint": filesystem + "/.ckpt/" + latest_ckpt}
                endpoint = "/host/share/" + str(ex['id'])
                rbk_share = rubrik.patch('internal', endpoint, payload)
                break
















