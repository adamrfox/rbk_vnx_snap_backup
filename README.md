# rbk_vnx_snap_backup
A project to allow Rubrik to take snapshot-based backups of a VNX file server

Rubrik does not currently have integration with VNX for backing up snapshots.  So this script is a way to help do that via automation.

This is a Python script that requires 2 non-standard packages which are easily obtained via pip: rubrik_cdm and paramiko.
As it's Python it will be most easily run on a Linux system but Python is available for Windows or it can be easily compiled
to an .exe.  If you need help with that, let me know.

The idea is that the script will be run from a host that has the filesystems being backed up by Rubrik mounted on it.
The script will use this to find the checkpoints and determine the latest one as VNX Checkpoints are, by default, named by a
time/date stamp.  Once the most recent checkpoint is found, the script will modify an export/share on the VNX to point
directly to that checkpoint.  If it's an NFS export, the export on the VNX will be configured to only be accessed by the IPs on the Rubrik (both access= and root=).  Thenm for NFS exports, the script will modify the share on the Rubrik to match that path.  This gives a consistent view of the data and Rubrik will back it up as if it's the same filesystem.
In the case of SMB, the script will simply update the share on the VNX.  There is no need to update the share on the Rubrik
as the SMB/CIFS share handles the path change.

The idea is to run this script a bit before your backup window is set to start so that the shares/exports will be updated and the backups will then run.  

Basic assumptions of the script today:
1. The VNX has a special share/export for each filesystem you want to backup with a checkpoint that has .ckpt in the path.  This is the share/export that will be modified by the script.
2. There is a share on the Rubrik set up for that filesystem.
3. You probably want a backup window defined on the SLA for the Rubrik for these shares.  Even if it's 23.5 hours.  The idea is that there should be at least a small window when these backups will not start.  Use that small window to run this script (from cron ideally).
4. It's possible to mount the filesysems thenselves (not the special ones for Rubrik) on the host running the script.

Credentials:
Credentials are needed for both the Rubrik as well as the VNX Control Station.  These can be entered either on the commmand line or they can be put into an obfuscated file using <a href="https://github.com/adamrfox/creds_encode">creds_encode</a>.  It's not really encrypted and you should still lock this file down as best you can but it's better than plaintext.  Suggestions for better ways to do this (2-way encoding) are welcome.  For the array type use 'rubrik' and 'vnx'.

Here's the basic syntax:
<pre>
Usage: rbk_vnx_snap_backup.py [-hvD] [-c creds] [-d data_mover] vnx filesystem path rubrik
-h | --help : Prints this message
-v | --verbose : Verbose mode, prints more messages
-D | --DEBUG : Debug mode.  Prints out more info
-c | --creds= : Use a file for credentials
-d | --data_mover= : Set the (virtual) data mover [default: server_2]
vnx : Hostname or IP of the Control Station of the VNX
share : Share name.  For NFS put the path starting the /, for SMB, put the share name.
path : Local path for the filesystem
rubrik: Hostname or IP of the Rubrik
</pre>

Example:

./rbk_vnx_snap_backup.py -v -c creds_file vnx_mgmt.company.com /foo /mnt my_rurbik.company.com

Note that the filesystem /foo means it's an NFS path.  It uses a file called creds_file to get the credentials and the filesystem /foo on the VNX is mounted on /mnt on the host.

