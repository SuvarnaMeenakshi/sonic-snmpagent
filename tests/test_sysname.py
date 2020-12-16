import os
import sys
from unittest import TestCase

import tests.mock_tables.dbconnector

class TestGetNextPDU(TestCase):
    @classmethod
    def setUpClass(cls):
        #For single namespace scenario, load database_config.json
        cls.lut = MIBTable(rfc1214.SysName)
        tests.mock_tables.dbconnector.load_database_config()

    def test_getpdu_sysname(self):
        # oid.include = 1
        oid = ObjectIdentifier(9, 0, 0, 0, (1, 3, 6, 1, 2, 1, 1, 5, 0))
        get_pdu = GetPDU(
            header=PDUHeader(1, PduTypes.GET, 16, 0, 42, 0, 0, 0),
            oids=[oid]
        )

        encoded = get_pdu.encode()
        response = get_pdu.make_response(self.lut)
        print(response)

        n = len(response.values)
        value0 = response.values[0]
        self.assertEqual(value0.type_, ValueType.OCTET_STRING)
        self.assertEqual(str(value0.name), str(ObjectIdentifier(9, 0, 0, 0, (1, 3, 6, 1, 2, 1, 1, 5, 0))))
        self.assertEqual(str(value0.data), 'test_hostname')
