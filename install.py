#!/usr/bin/python
# -*- coding: utf-8 -*-

import os
import pwd
import sys
import platform
import ConfigParser
import argparse
import shutil
import errno
import traceback

BLUE = '\033[94m'
OK = '\033[92m'
WARNING = '\033[93m'
FAIL = '\033[91m'
ENDC = '\033[0m'

def info(msg):
    print("%s [ %s ] %s" % (BLUE,msg,ENDC))
def ok(msg):
    print("%s ==> %s  %s" % (OK,msg,ENDC))
def warning(msg):
    print("%s ==> %s  %s" % (WARNING,msg,ENDC))
def fail(msg):
    print("%s ==> %s  %s" % (FAIL,msg,ENDC))

def get_c_hub():
    hub = {
        'x86_64' : 'src/domogik/xpl/tools/64bit/xPL_Hub',
        'i686' : 'src/domogik/xpl/tools/32bit/xPL_Hub',
        'arm' : 'src/domogik/xpl/tools/arm/xPL_Hub',
        'armv5tel' : 'src/domogik/xpl/tools/arm/xPL_Hub',
        'armv6l' : 'src/domogik/xpl/tools/arm/xPL_Hub'
    }
    arch = platform.machine()
    if arch in hub.keys():
        return hub[arch]
    else:
        return None

def build_file_list(user):
    d_files = [
        ('/etc/domogik', [user, 0755], ['src/domogik/examples/config/domogik.cfg.sample',  'src/domogik/examples/packages/sources.list', 'src/domogik/xplhub/examples/config/xplhub.cfg.sample']),
        ('/var/cache/domogik', [user, None], []),
        ('/var/cache/domogik/pkg-cache', [user, None], []),
        ('/var/cache/domogik/cache', [user, None], []),
        ('/var/lib/domogik', [user, None], []),
        ('/var/lib/domogik/packages', [user, None], ['src/domogik/common/__init__.py']),
        ('/var/lib/domogik/resources', [user, None], []),
        ('/var/lib/domogik/resources', [user, None], ['src/domogik/common/datatypes.json']),
        ('/var/lock/domogik', [user, None], []),
        ('/var/log/domogik', [user, None], []),
        ('/var/log/xplhub', [user, None], []),
    ]

    if os.path.exists('/etc/default'):
        d_files.append(('/etc/default/', [user, None], ['src/domogik/examples/default/domogik']))
    else:
        print "Can't find directory where i can copy system wide config"
        exit(0)

    if os.path.exists('/etc/logrotate.d'):
        d_files.append(('/etc/logrotate.d', [user, None], ['src/domogik/examples/logrotate/domogik', 'src/domogik/xplhub/examples/logrotate/xplhub']))

    if os.path.exists('/etc/init.d'):
        d_files.append(('/etc/init.d/', [user, 0755], ['src/domogik/examples/init/domogik']))
    elif os.path.exists('/etc/rc.d'):
        d_files.append(('/etc/rc.d/', [user, 0755], ['src/domogik/examples/init/domogik']))
    else:
        print("Can't find firectory for init script")
        exit(0)

    hub = get_c_hub()
    if hub is not None:
        d_files.append(('/usr/sbin/', [user, None], [hub]))

    return d_files

def copy_files(user):
    info("Copy files")
    try:
        for directory, perm, files in build_file_list(user):
            if not os.path.exists(directory):
                if perm[1] != None:
                    res = os.makedirs(directory, int(perm[1]))
                else:
                    res = os.makedirs(directory)
                if not res:
                    ok("Creating dir {0}".format(directory))
                else:
                    fail("Failed creating dir {0}".format(directory))
            else:
                ok("Directory {0} already exists".format(directory))
            if perm[0] != '': 
                os.system('chown {0} {1}'.format(perm[0], directory))
            for fname in files:
                # copy the file
                shutil.copy(os.path.join(os.path.dirname(os.path.realpath(__file__)), fname), directory)
                ok("Copyed file {0}".format(fname))
                dfname = os.path.join(directory, os.path.basename(fname))
                if perm[0] != '': 
                    os.system('chown {0} {1}'.format(perm[0], dfname))
                #if perm[1] != None: 
                #    os.system('chmod {0} {1}'.format(perm[1], dfname))
    except:
        raise

def ask_user_name():
    info("Create domogik user")
    print("As what user should domogik run? [domogik]: "),
    new_value = sys.stdin.readline().rstrip('\n')
    if new_value == "":
        d_user = 'domogik'
    else:
        d_user = new_value
    return d_user

def create_user(d_user):
    info("Create domogik user")
    if d_user not in [x[0] for x in pwd.getpwall()]:
        print("Creating the {0} user".format(d_user))
        os.system('/usr/sbin/useradd --system {0}'.format(d_user))
    if d_user not in [x[0] for x in pwd.getpwall()]:
        fail("Failed to create domogik user")
    else:
        ok("Correctly created domogik user")
    # return the user to use

def is_domogik_advanced(advanced_mode, sect, key):
    advanced_keys = {
        'domogik': ['libraries_path', 'src_prefix', 'log_dir_path', 'pid_dir_path', 'broadcast'],
        'database': ['db_prefix', 'pool_recycle'],
        'rest': ['rest_server_port', 'rest_use_ssl', 'rest_ssl_certificate'],
        'mq': ['req_rep_port', 'pub_port', 'sub_port'],
    }
    if advanced_mode:
        return True
    else:
        if sect not in advanced_keys:
            return True
        else:
            if key not in advanced_keys[sect]:
                return True
            else:
                return False

def is_xplhub_advanced(advanced_mode, sect, key):
    advanced_keys = {
        'hub': ['log_dir_path', 'log_bandwidth', 'log_invalid_data'],
    }
    if advanced_mode:
        return True
    else:
        if sect not in advanced_keys:
            return True
        else:
            if key not in advanced_keys[sect]:
                return True
            else:
                return False

def write_domogik_configfile(advanced_mode):
    # read the sample config file
    newvalues = False
    config = ConfigParser.RawConfigParser()
    config.read( ['/etc/domogik/domogik.cfg.sample'] )
    for sect in config.sections():
        info("Starting on section {0}".format(sect))
        for item in config.items(sect):
            if is_domogik_advanced(advanced_mode, sect, item[0]):
                print("Key {0} [{1}]: ".format(item[0], item[1])),
                new_value = sys.stdin.readline().rstrip('\n')
                if new_value != item[1] and new_value != '':
                    # need to write it to config file
                    config.set(sect, item[0], new_value)
                    newvalues = True
    # write the config file
    with open('/etc/domogik/domogik.cfg', 'wb') as configfile:
        ok("Writing the config file")
        config.write(configfile)

def write_xplhub_configfile(advanced_mode):
    # read the sample config file
    newvalues = False
    config = ConfigParser.RawConfigParser()
    config.read( ['/etc/domogik/xplhub.cfg.sample'] )
    for sect in config.sections():
        info("Starting on section {0}".format(sect))
        for item in config.items(sect):
            if is_xplhub_advanced(advanced_mode, sect, item[0]):
                print("Key {0} [{1}]: ".format(item[0], item[1])),
                new_value = sys.stdin.readline().rstrip('\n')
                if new_value != item[1] and new_value != '':
                    # need to write it to config file
                    config.set(sect, item[0], new_value)
                    newvalues = True
    # write the config file
    with open('/etc/domogik/xplhub.cfg', 'wb') as configfile:
        ok("Writing the config file")
        config.write(configfile)

def write_domogik_configfile_from_command_line(args):
    # read the sample config file
    config = ConfigParser.RawConfigParser()
    config.read( ['/etc/domogik/domogik.cfg.sample'] )
    for sect in config.sections():
        info("Starting on section {0}".format(sect))
        for item in config.items(sect):
            new_value = eval("args.{0}_{1}".format(sect, item[0]))
            if new_value != item[1] and new_value != '' and new_value != None:
                # need to write it to config file
                print("Set [{0}] : {1} = {2}".format(sect, item[0], new_value))
                config.set(sect, item[0], new_value)
                newvalues = True
    # write the config file
    with open('/etc/domogik/domogik.cfg', 'wb') as configfile:
        ok("Writing the config file")
        config.write(configfile)

def write_xplhub_configfile_from_command_line(args):
    # read the sample config file
    config = ConfigParser.RawConfigParser()
    config.read( ['/etc/domogik/xplhub.cfg.sample'] )
    for sect in config.sections():
        info("Starting on section {0}".format(sect))
        for item in config.items(sect):
            new_value = eval("args.{0}_{1}".format(sect, item[0]))
            if new_value != item[1] and new_value != '' and new_value != None:
                # need to write it to config file
                print("Set [{0}] : {1} = {2}".format(sect, item[0], new_value))
                config.set(sect, item[0], new_value)
                newvalues = True
    # write the config file
    with open('/etc/domogik/xplhub.cfg', 'wb') as configfile:
        ok("Writing the config file")
        config.write(configfile)


def needupdate():
    # first check if there are already some config files
    if os.path.isfile("/etc/domogik/domogik.cfg") or \
       os.path.isfile("/etc/domogik/xplhub.cfg"):
        print("Do you want to keep your current config files ? [Y/n]: "),
        new_value = sys.stdin.readline().rstrip('\n')
        if new_value == "y" or new_value == "Y" or new_value == '':
            return False
        else:
            return True
    return True

# not used
#def config(advanced, notest):
#    try:
#        am_i_root()
#        if needupdate():
#            write_configfile(advanced)
#        if not notest:
#            test_config()
#    except:
#        fail(sys.exc_info())

def update_default(user):
    info("Update /etc/default/domogik")
    os.system('sed -i "s;^DOMOGIK_USER.*$;DOMOGIK_USER={0};" /etc/default/domogik'.format(user))

def install():
    parser = argparse.ArgumentParser(description='Domogik installation.')
    parser.add_argument('--no-setup', dest='setup', action="store_true",
                   default=False, help='Don\'t install the python packages')
    parser.add_argument('--no-test', dest='test', action="store_true",
                   default=False, help='Don\'t run a config test')
    parser.add_argument('--no-config', dest='config', action="store_true",
                   default=False, help='Don\'t run a config writer')
    parser.add_argument('--no-create-user', dest='user_creation', action="store_false",
                   default=False, help='Don\'t create a user')
    parser.add_argument('--no-db-upgrade', dest='db', action="store_true",
                   default=False, help='Don\'t do a db upgrade')
    parser.add_argument("--user",
                   help="Set the domogik user")

    # generate dynamically all arguments for the various config files
    # notice that we MUST NOT have the same sections in the different files!
    parser.add_argument('--command-line', dest='command_line', action="store_true",
                   default=False, help='Configure the configuration files from the command line only')
    add_arguments_for_config_file(parser, "src/domogik/examples/config/domogik.cfg.sample")
    add_arguments_for_config_file(parser, "src/domogik/xplhub/examples/config/xplhub.cfg.sample")


    args = parser.parse_args()
    print "mq_ip=%s" % args.mq_ip
    try:
        # CHECK python version
        if sys.version_info < (2,6):
            print "Python version is to low, at least python 2.6 is needed"
            exit(0)

        # CHECK run as root
        info("Check this script is started as root")
        assert os.getuid() == 0, "This script must be started as root"
        ok("Correctly started with root privileges.")

        # RUN setup.py
        if not args.setup:
            info("Run setup.py")
            os.system('python setup.py develop')

        # ask for the domogik user
        if args.user == None or args.user == '':
            user = ask_user_name()
        else: 
            ok("User setted to '{0}' from the command line".format(args.user))
            user = args.user

        # create user
        if args.user_creation:
            create_user(user)

        # Copy files
        copy_files(user)
        update_default(user)

        # write config file
        if args.command_line:
            info("Update the config file : /etc/domogik/domogik.cfg")
            write_domogik_configfile_from_command_line(args)
            info("Update the config file : /etc/domogik/xplhub.cfg")
            write_xplhub_configfile_from_command_line(args)

        else:
            if not args.config and needupdate():
                info("Update the config file : /etc/domogik/domogik.cfg")
                write_domogik_configfile(False)
                info("Update the config file : /etc/domogik/xplhub.cfg")
                write_xplhub_configfile(False)

        # upgrade db
        if not args.db:
            # set the uid this process runs with
            user_entry = pwd.getpwnam(user)
            os.setregid(0, user_entry.pw_gid)
            os.setreuid(0, user_entry.pw_uid)
            tmp_egg_path = '/tmp/domogik-egg/'
            try:
                os.makedirs(tmp_egg_path)
            except OSError as exc: # Python >2.5
                if exc.errno == errno.EEXIST and os.path.isdir(tmp_egg_path):
                    pass
                else: 
                    raise
            try:
                os.system("export PYTHON_EGG_CACHE={0} && python src/domogik/install/installer.py".format(tmp_egg_path))
            except:
               fail(traceback.format_exc())
               try:
                   shutil.rmtree(tmp_egg_path)
               except:
                   raise

            try:
                shutil.rmtree(tmp_egg_path)
            except:
                raise
            # restore root uid
            os.setregid(0, 0)
            os.setreuid(0, 0)
        if not args.test:
            # TODO : replace python call by the dynamic python command
            os.system('python test_config.py')
        print("\n\n")
    except:
        fail(sys.exc_info())

def add_arguments_for_config_file(parser, file):
    # read the sample config file
    config = ConfigParser.RawConfigParser()
    config.read( [file] )
    for sect in config.sections():
        for item in config.items(sect):
            key = "{0}_{1}".format(sect, item[0])
            parser.add_argument("--{0}".format(key), 
                                help="Update section {0}, key {1} value".format(sect, item[0]))

if __name__ == "__main__":
    install()
