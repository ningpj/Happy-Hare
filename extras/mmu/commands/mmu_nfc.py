# -*- coding: utf-8 -*-
# Happy Hare MMU Software
#
# Copyright (C) 2022-2026  moggieuk#6538 (discord)
#                          moggieuk@hotmail.com
#
# Goal: Command class to control and inspect the MMU NFC/RFID readers
#
# Implements commands:
#   MMU_NFC
#
# The readers themselves are owned by each mmu_unit's MmuNfcManager. This command
# resolves the correct unit (implied from GATE, or the sole/only-shared unit, or
# an explicit UNIT) and then talks to that unit's nfc_manager.
#
# (\_/)
# ( *,*)
# (")_(") Happy Hare Ready
#
# This file may be distributed under the terms of the GNU GPLv3 license.
#

# Happy Hare imports
from ..mmu_constants   import *
from .mmu_base_command import *


class MmuNfcCommand(BaseCommand):

    CMD = "MMU_NFC"

    HELP_BRIEF = "Control and inspect the MMU NFC/RFID readers"
    HELP_PARAMS = (
        "%s: %s\n" % (CMD, HELP_BRIEF)
        + "SHARED   = [0|1] Target the unit's shared reader\n"
        + "GATE     = #(int) Target the reader for this gate (implies the unit)\n"
        + "UNIT     = #(int)/name Only needed to disambiguate multiple units with shared readers\n"
        + "ENABLE   = [0|1] Top-level on/off for the reader (re-inits when enabled)\n"
        + "READ     = [0|1] Read the addressed reader once and report the UID\n"
        + "INIT     = [0|1] (Re)initialize the addressed reader\n"
        + "RELEASE  = [0|1] Release the current target on the addressed reader\n"
        + "INIT_ALL = [0|1] (Re)initialize every reader on every unit\n"
        + "DETAILS  = [0|1] Include actual cached tag UIDs in the status report\n"
        + "(no parameters for status report of all readers)"
    )
    HELP_SUPPLEMENT = (
        "Examples:\n"
        + f"{CMD}                       ...Report status of all readers (which have a cached tag)\n"
        + f"{CMD} DETAILS=1             ...As above but show the actual cached UIDs\n"
        + f"{CMD} SHARED=1 ENABLE=0     ...Disable the shared reader\n"
        + f"{CMD} GATE=3 READ=1         ...Read the reader on gate 3 and report the result\n"
        + f"{CMD} GATE=2 INIT=1         ...(Re)initialize the reader on gate 2\n"
        + f"{CMD} INIT_ALL=1            ...Re-initialize every reader quickly\n"
    )

    def __init__(self, mmu):
        super().__init__(mmu)
        self.register(
            name=self.CMD,
            handler=self._run,
            help_brief=self.HELP_BRIEF,
            help_params=self.HELP_PARAMS,
            help_supplement=self.HELP_SUPPLEMENT,
            category=CATEGORY_GENERAL,
        )

    def _run(self, gcmd):
        # Note: BaseCommand wrapper already logs commandline + handles HELP=1.
        if self.check_if_disabled(): return
        mmu = self.mmu

        details  = gcmd.get_int('DETAILS', 0, minval=0, maxval=1)
        init_all = gcmd.get_int('INIT_ALL', 0, minval=0, maxval=1)
        shared   = bool(gcmd.get_int('SHARED', 0, minval=0, maxval=1))
        gate     = gcmd.get_int('GATE', None, minval=0, maxval=mmu.num_gates - 1)
        enable   = gcmd.get_int('ENABLE', None, minval=0, maxval=1)
        read     = gcmd.get_int('READ', 0, minval=0, maxval=1)
        init     = gcmd.get_int('INIT', 0, minval=0, maxval=1)
        release  = gcmd.get_int('RELEASE', 0, minval=0, maxval=1)

        units = mmu.mmu_machine.units

        # INIT_ALL: reset everything quickly (does not touch enable/active flags)
        if init_all:
            for unit in units:
                unit.nfc_manager.init_all()
            mmu.log_always("NFC: re-initialized all readers on all units")
            return

        # No reader addressed -> status report across all units
        if not shared and gate is None:
            self._report_all(units, details)
            return

        if shared and gate is not None:
            raise gcmd.error("Specify only one of SHARED=1 or GATE=<n>")

        # Resolve the unit and its nfc_manager for the addressed reader
        mmu_unit = self._unit_for_gate(gcmd, gate) if gate is not None else self._unit_for_shared(gcmd)
        mgr = mmu_unit.nfc_manager
        label = "shared reader" if shared else ("gate %d" % gate)

        if not mgr.has_reader(shared=shared, gate=gate):
            raise gcmd.error("%s: no NFC %s configured" % (mmu_unit.name, label))

        did_action = False

        if enable is not None:
            mgr.set_enabled(enable, shared=shared, gate=gate)
            mmu.log_always("NFC: %s %s %s" % (mmu_unit.name, label, "enabled" if enable else "disabled"))
            did_action = True

        if init:
            alive = mgr.init_reader(shared=shared, gate=gate)
            mmu.log_always("NFC: %s %s init %s" % (mmu_unit.name, label, "OK" if alive else "did not respond"))
            did_action = True

        if release:
            mgr.release_reader(shared=shared, gate=gate)
            mmu.log_always("NFC: %s %s released" % (mmu_unit.name, label))
            did_action = True

        if read:
            # 'enabled' is a hard off - refuse the read; 'active' is only a guard on
            # automatic reads, so a manual READ deliberately overrides it.
            if not mgr.is_enabled(shared=shared, gate=gate):
                mmu.log_always("NFC: %s %s is disabled - use ENABLE=1 first" % (mmu_unit.name, label))
            else:
                uid = mgr.read_reader(shared=shared, gate=gate)
                if uid:
                    mmu.log_always("NFC: %s %s read UID=%s" % (mmu_unit.name, label, uid))
                else:
                    mmu.log_always("NFC: %s %s - no tag detected" % (mmu_unit.name, label))
            did_action = True

        # A bare selector (e.g. MMU_NFC GATE=3) just reports that reader's status
        if not did_action:
            self._report_one(mmu_unit, mgr, shared=shared, gate=gate, details=details)

    #
    # Unit resolution -----------------------------------------------------------
    #

    def _unit_for_gate(self, gcmd, gate):
        # Explicit UNIT (or the sole unit) wins; otherwise derive from the gate.
        unit = self.get_unit(gcmd, mode="optional")
        return unit if unit is not None else self.mmu.mmu_unit(gate)

    def _unit_for_shared(self, gcmd):
        # Explicit UNIT (or the sole unit) wins; otherwise, with multiple units,
        # auto-pick the only one that actually has a shared reader.
        unit = self.get_unit(gcmd, mode="optional")
        if unit is not None:
            return unit
        candidates = [u for u in self.mmu.mmu_machine.units if u.nfc_manager.has_reader(shared=True)]
        if len(candidates) == 1:
            return candidates[0]
        if not candidates:
            raise gcmd.error("No shared NFC reader configured on any unit")
        raise gcmd.error("UNIT parameter required: more than one unit has a shared NFC reader")

    #
    # Status reporting ----------------------------------------------------------
    #

    def _reader_line(self, label, rs, details):
        if rs is None:
            return None
        if rs.get('uid'):
            tag = rs['uid'] if details else "present"
        else:
            tag = "none"
        return "%-9s enabled=%d active=%d alive=%d tag=%s" % (
            label + ":", int(rs['enabled']), int(rs['active']), int(rs['alive']), tag)

    def _report_one(self, mmu_unit, mgr, shared, gate, details):
        status = mgr.get_status()
        if shared:
            rs, label = status['shared'], "shared"
        else:
            rs, label = status['gates'].get(gate), "gate %d" % gate
        self.mmu.log_always("NFC: %s %s" % (mmu_unit.name, self._reader_line(label, rs, details)))

    def _report_all(self, units, details):
        multi = len(units) > 1
        lines = []
        for unit in units:
            status = unit.nfc_manager.get_status()
            unit_lines = []
            shared_line = self._reader_line("shared", status['shared'], details)
            if shared_line:
                unit_lines.append(shared_line)
            for g in sorted(status['gates']):
                unit_lines.append(self._reader_line("gate %d" % g, status['gates'][g], details))
            if unit_lines:
                if multi:
                    lines.append("Unit %s:" % status['unit'])
                lines.extend(unit_lines)

        if not lines:
            self.mmu.log_always("No NFC readers configured")
        else:
            self.mmu.log_always("MMU NFC readers:\n" + "\n".join(lines))
