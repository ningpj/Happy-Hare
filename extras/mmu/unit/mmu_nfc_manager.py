# -*- coding: utf-8 -*-
# Happy Hare MMU Software
#
# Copyright (C) 2022-2026  moggieuk#6538 (discord)
#                          moggieuk@hotmail.com
#
# Goal: Manager class to coordinate NFC readers
#
# (\_/)
# ( *,*)
# (")_(") Happy Hare Ready
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#

import logging

# Happy Hare imports
from ..mmu_constants import *
from ..mmu_utils     import MmuError

NFC_CHECK_INTERVAL = 1 # How often to shared NFC reader

class MmuNfcManager:

    def __init__(self, config, mmu_unit, params):
        self.config = config
        self.mmu_unit = mmu_unit                # This physical MMU unit
        self.mmu_machine = mmu_unit.mmu_machine # Entire Logical combined MMU
        self.p = params                         # mmu_unit_parameters
        self.printer = config.get_printer()
        self.reactor = self.printer.get_reactor()

        # Listen of important mmu events
        self.printer.register_event_handler("mmu:enabled", self._handle_mmu_enabled)
        self.printer.register_event_handler("mmu:disabled", self._handle_mmu_disabled)
        self.printer.register_event_handler("mmu:bootup", self._handle_mmu_bootup)

        # Register event handlers
        self.printer.register_event_handler('klippy:connect', self._handle_connect)

        self._periodic_timer = self.reactor.register_timer(self._check_nfc_reader)


    def _handle_connect(self):
        self.mmu = self.mmu_machine.mmu_controller


    #
    # Internal implementation --------------------------------------------------
    #

    def _handle_mmu_enabled(self):
        """
        Event indicating that the MMU unit was enabled
        """
        pass


    def _handle_mmu_disabled(self):
        """
        Event indicating that the MMU unit was disabled
        """
        self.reactor.update_timer(self._periodic_timer, self.reactor.NEVER)


    def _handle_mmu_bootup(self):
        """
        Delayed event indicating that the MMU bootup
        """
        # initialize all rfc_readers... and report state

        if self.has_shared_nfc_reader():
            self.mmu.log_info("NFC: Shared reader listening")
            self.reactor.update_timer(self._periodic_timer, self.reactor.NOW)


    def _check_nfc_reader(self, eventtime):
        """
        Reactor callback to periodically check shared nfc reader
        """
        # Read shared reader...
        uid = "ad343ee5901"
        if uid:
            self.mmu.log_info("NFC: RFID read")
            # initiate spoolman lookup... as async thread
            #
        

        # Reschedule
        return eventtime + ENV_CHECK_INTERVAL


    def has_shared_nfc_reader(self):
        return bool(self.mmu_unit.nfc_reader)


    def has_gate_nfc_reader(self, gate):
        nfc_readers = self.mmu_unit.nfc_readers
        lgate = self.mmu_unit.local_gate(gate)
        return bool(nfc_readers and nfc_readers[lgate])

