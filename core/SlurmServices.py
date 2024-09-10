# import subprocess
from fabric import Connection
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
# import ConfigParser
import configparser
import json, os
import operator
import sys
from datetime import datetime


class SlurmServices(object):
    cfg = {}

    # Constructor
    def __init__(self, cfg):

        self.cfg = cfg

        self.storage_devices = [
            {"name": "Working Storage", "host": "frontend", "device": "/home", "warning": 2000000.0,
             "danger": 999000.0},
            {"name": "Primary Storage", "host": "webserv", "device": "/data1", "warning": 1000000.0,
             "danger": 650000.0},
            {"name": "Secondary Storage", "host": "webserv", "device": "/data2", "warning": 1000000.0,
             "danger": 650000.0},
            {"name": "Tertialy Storage 0", "host": "instrdata0", "device": "/data1", "warning": 1000000.0,
             "danger": 650000.0},
            {"name": "Tertialy Storage 1", "host": "instrdata1", "device": "/data1", "warning": 1000000.0,
             "danger": 650000.0},
            {"name": "Tertialy Storage 2", "host": "instrdata2", "device": "/data1", "warning": 1000000.0,
             "danger": 650000.0},
        ]

    def get_as_MB(self, part):
        result = 1
        if "G" in part:
            result = 1000.0
        elif "T" in part:
            result = 1000000.0
        elif "P" in part:
            result = 1000000000.0
        return result

    def get_storage_status(self):
        storages = []
        for storage_device in self.storage_devices:
            storage = {
                "name": storage_device["name"],
                "host": storage_device["host"],
                "device": storage_device["device"]
            }
            # ssh instrdata1 'df -h /data1'|tail -n 1
            try:
                connection = Connection(storage_device["host"])
                result = connection.run("df -h " + storage_device["device"], hide=True)
                line = result.stdout.strip().split("\n")[1]
                while "  " in line:
                    line = line.replace("  ", " ")
                parts = line.split(" ")
                storage["total_mb"] = float(parts[1][:-1]) * self.get_as_MB(parts[1])
                storage["used_mb"] = float(parts[2][:-1]) * self.get_as_MB(parts[2])
                storage["available_mb"] = float(parts[3][:-1]) * self.get_as_MB(parts[3])
                storage["used_perc"] = float(parts[4].replace("%", "")) / 100.0

                if storage["available_mb"] <= float(storage_device["danger"]):
                    storage["alert"] = "danger"
                elif storage["available_mb"] <= float(storage_device["warning"]):
                    storage["alert"] = "warning"
                else:
                    storage["alert"] = "info"

                storage["status"] = "up"
            except NoValidConnectionsError:
                storage["status"] = "down"
            storages.append(storage)
        return storages

    def get_attributes(self, output):
        attributes = []
        parts = output.strip().split("|")
        for part in parts:
            name = part.strip().lower()
            name = name.replace(":", "_").replace("(", "_").replace(")", "").replace("/", "_")
            attributes.append(name)
        return attributes

    def get_item(self, attributes, output):
        index = 0
        item = {}
        parts = output.strip().split("|")
        for part in parts:
            if attributes[index] != "":
                value = part.strip()
                if value != '(null)':
                    if value.isdigit():
                        if '.' in value:
                            value = float(value)
                        else:
                            value = int(value)
                    item[attributes[index]] = value
            index = index + 1
        return item

    def command(self, args):
        attributes = None
        items = []

        try:
            connection = Connection("frontend")
            result = connection.run(args, hide=True)
            lines = result.stdout.strip().split("\n")
            for output in lines:
                if attributes is None:
                    attributes = self.get_attributes(output)

                else:
                    items.append(self.get_item(attributes, output))
        except NoValidConnectionsError:
            pass
        return items

    def sinfo(self):
        result = self.command('sinfo -o "%all"')
        return result

    def squeue(self):
        result = self.command('squeue -o "%all"')
        return result

if __name__ == "__main__":
  fname = "../etc/ccmmmaapi.development.conf"
  config = {}
  with open(fname) as f:
    content = f.readlines()
    for line in content:
      line = line.replace("\n", "").replace("\r", "")
      if line == "" or line.startswith('#') or not " = " in line:
        continue

  parts = line.split(" = ")

  if '"' in parts[1][0] and '"' in parts[1][-1:]:
    config[parts[0]] = parts[1].replace('"', '')
  else:
    if '.' in parts[1]:
      config[parts[0]] = float(parts[1])
    else:
      config[parts[0]] = int(parts[1])

  print (str(config))
  slurm=SlurmServices(config)

  out=slurm.sinfo()
  print (str(out))
  print ("----------")

  out=slurm.squeue()
  print (str(out))
  print ("----------")

  out=slurm.get_storage_status()
  print (str(out))
