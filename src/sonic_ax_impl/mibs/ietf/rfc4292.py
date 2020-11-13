import ipaddress

from sonic_ax_impl import mibs
from sonic_ax_impl.mibs import Namespace
from ax_interface import MIBMeta, ValueType, MIBUpdater, SubtreeMIBEntry
from ax_interface.util import ip2tuple_v4
from bisect import bisect_right
from sonic_py_common import multi_asic

class RouteUpdater(MIBUpdater):
    def __init__(self):
        super().__init__()
        self.tos = 0 # ipCidrRouteTos
        self.db_conn = Namespace.init_namespace_dbs()
        self.route_dest_map = {}
        self.route_dest_list = []
        ## loopback ip string -> ip address object
        self.loips = {}

    def reinit_data(self):
        """
        Subclass update loopback information
        """
        self.loips = {}

        loopbacks = Namespace.dbs_keys(self.db_conn, mibs.APPL_DB, "INTF_TABLE:lo:*")
        if not loopbacks:
            return

        ## Collect only ipv4 lo interfaces
        for loopback in loopbacks:
            lostr = loopback
            loipmask = lostr[len("INTF_TABLE:lo:"):]
            loip = loipmask.split('/')[0]
            ipa = ipaddress.ip_address(loip)
            if isinstance(ipa, ipaddress.IPv4Address):
                self.loips[loip] = ipa

    def update_data(self):
        """
        Update redis (caches config)
        Pulls the table references for each interface.
        """
        self.route_dest_map = {}
        self.route_dest_list = []

        ## The nexthop for loopbacks should be all zero
        for loip in self.loips:
            sub_id = ip2tuple_v4(loip) + (255, 255, 255, 255) + (self.tos,) + (0, 0, 0, 0)
            self.route_dest_list.append(sub_id)
            self.route_dest_map[sub_id] = self.loips[loip].packed

        # Get list of front end asic namespaces for multi-asic platform.
        # This list will be empty for single asic platform.
        front_ns = multi_asic.get_all_namespaces()['front_ns']

        for db_conn in Namespace.get_non_host_dbs(self.db_conn):
            # For multi-asic platform, proceed to get routes only for front end namespaces.
            if db_conn.namespace != multi_asic.DEFAULT_NAMESPACE and \
               db_conn.namespace not in front_ns:
                continue
            ipnstr = "0.0.0.0/0"
            route_str = "ROUTE_TABLE:0.0.0.0/0"
            route_entry  = db_conn.keys(mibs.APPL_DB, route_str)
            if not route_entry:
                continue
            ipn = ipaddress.ip_network(ipnstr)
            ent = db_conn.get_all(mibs.APPL_DB, route_str, blocking=True)
            nexthops = ent["nexthop"]
            ifnames = ent["ifname"]
            for nh, ifn in zip(nexthops.split(','), ifnames.split(',')):
                ## Ignore non front panel interfaces
                ## TODO: non front panel interfaces should not be in APPL_DB at very beginning
                ## This is to workaround the bug in current sonic-swss implementation
                if ifn == "eth0" or ifn == "lo" or ifn == "docker0": continue
                # Ignore internal asic routes
                if multi_asic.is_port_channel_internal(ifn, db_conn.namespace): continue
                sub_id = ip2tuple_v4(ipn.network_address) + ip2tuple_v4(ipn.netmask) + (self.tos,) + ip2tuple_v4(nh)
                self.route_dest_list.append(sub_id)
                self.route_dest_map[sub_id] = ipn.network_address.packed

        self.route_dest_list.sort()

    def route_dest(self, sub_id):
        return self.route_dest_map.get(sub_id, None)

    def route_status(self, sub_id):
        if sub_id in self.route_dest_map:
            return 1 ## active
        else:
            return None

    def get_next(self, sub_id):
        right = bisect_right(self.route_dest_list, sub_id)
        if right >= len(self.route_dest_list):
            return None

        return self.route_dest_list[right]

class IpCidrRouteTable(metaclass=MIBMeta, prefix='.1.3.6.1.2.1.4.24.4'):
    """
    'ipCidrRouteDest table in IP Forwarding Table MIB' https://tools.ietf.org/html/rfc4292
    """

    route_updater = RouteUpdater()

    ipCidrRouteDest = \
        SubtreeMIBEntry('1.1', route_updater, ValueType.IP_ADDRESS, route_updater.route_dest)

    ipCidrRouteStatus = \
        SubtreeMIBEntry('1.16', route_updater, ValueType.INTEGER, route_updater.route_status)
