from ax_interface.mib import MIBMeta, MIBUpdater, MIBEntry, ValueType
from sonic_ax_impl import mibs


class sysNameUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.db_conn = mibs.init_db()

    def update_data():
        return

    def get_sys_name(self):
        """
        Subclass update interface information
        """
        self.db_conn.connect(mibs.CONFIG_DB)

        device_metadata = self.db_conn.get_all(self.db_conn.CONFIG_DB, "DEVICE_METADATA|localhost")

        if device_metadata is not None and b'hostname' in device_metadata:
             return str(device_metadata['hostname'])
        else:
             return ""


class SysName(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.1.5'):
    """

    """
    updater = sysNameUpdater()

    # S-Series CPU utilization in percentage for last 5 seconds
    sysName = MIBEntry('0', ValueType.OCTET_STRING, updater.get_sys_name)
