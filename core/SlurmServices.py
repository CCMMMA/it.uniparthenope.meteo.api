"""Services for exposing Slurm-related operational data."""

# import subprocess
from fabric import Connection
from paramiko.ssh_exception import NoValidConnectionsError, SSHException
# import ConfigParser


class SlurmServices(object):
    """Service or helper that encapsulates slurm services behavior."""
    cfg = {}

    # Constructor
    def __init__(self, cfg):
        """Initialize slurm services state."""

        self.cfg = cfg
        self._connections = {}

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

    def _get_connection(self, host):
        """Return a cached SSH connection for a host."""
        connection = self._connections.get(host)
        if connection is None:
            connection = Connection(host)
            self._connections[host] = connection
        return connection

    @staticmethod
    def _split_columns(line):
        """Return normalized whitespace-separated command columns."""
        return line.split()

    def get_as_MB(self, part):
        """Return as mb."""
        result = 1
        if "G" in part:
            result = 1000.0
        elif "T" in part:
            result = 1000000.0
        elif "P" in part:
            result = 1000000000.0
        return result

    def get_storage_status(self):
        """Return storage status."""
        storages = []
        for storage_device in self.storage_devices:
            storage = {
                "name": storage_device["name"],
                "host": storage_device["host"],
                "device": storage_device["device"]
            }
            # ssh instrdata1 'df -h /data1'|tail -n 1
            try:
                connection = self._get_connection(storage_device["host"])
                result = connection.run("df -h " + storage_device["device"], hide=True)
                line = result.stdout.strip().split("\n")[1]
                parts = self._split_columns(line)
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
            except (NoValidConnectionsError, SSHException, OSError):
                storage["status"] = "down"
            storages.append(storage)
        return storages

    def get_attributes(self, output):
        """Return attributes."""
        attributes = []
        parts = output.strip().split("|")
        for part in parts:
            name = part.strip().lower()
            name = name.replace(":", "_").replace("(", "_").replace(")", "").replace("/", "_")
            attributes.append(name)
        return attributes

    def get_item(self, attributes, output):
        """Return item."""
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
        """Implement command for slurm services."""
        attributes = None
        items = []

        try:
            connection = self._get_connection("frontend")
            result = connection.run(args, hide=True)
            lines = result.stdout.strip().split("\n")
            for output in lines:
                if attributes is None:
                    attributes = self.get_attributes(output)

                else:
                    items.append(self.get_item(attributes, output))
        except (NoValidConnectionsError, SSHException, OSError):
            pass
        return items

    def sinfo(self):
        """Implement sinfo for slurm services."""
        result = self.command('sinfo -o "%all"')
        return result

    def squeue(self):
        """Implement squeue for slurm services."""
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

  # print (str(config))
  slurm=SlurmServices(config)

  out=slurm.sinfo()
  # print (str(out))
  # print ("----------")

  out=slurm.squeue()
  # print (str(out))
  # print ("----------")

  out=slurm.get_storage_status()
  # print (str(out))
