# Happy Hare MMU Software
#
# Implements the NFC command surface. NFC gate objects own reader and spool
# state; this command owns all Klipper GCode registration and routing.

from .mmu_base_command import BaseCommand, CATEGORY_GENERAL
from .. import mmu_nfc_manager as nfc_manager


class MmuNfcCommand(BaseCommand):

    def __init__(self, mmu):
        super().__init__(mmu)
        self._register_commands()

    def _register_commands(self):
        commands = (
            ('NFC', self._run_lane,
             'Control or test one configured per-gate NFC reader'),
            ('NFC_SHARED', self._run_shared,
             'Control the configured shared NFC reader'),
            ('NFC_STATUS', self._run_status,
             'Report spool state for all configured NFC gates'),
            ('NFC_HELP', self._run_help,
             'Show NFC reader command help'),
            ('NFC_DOCTOR', self._run_doctor,
             'Check NFC reader setup and configuration'),
            ('NFC_REGISTER', self._run_register,
             'Assign an NFC UID to an existing Spoolman spool'),
            ('NFC_LED_TEST', self._run_led_test,
             'Test configured NFC lane LED effects'),
        )
        for name, handler, help_brief in commands:
            self.register(
                name=name,
                handler=handler,
                help_brief=help_brief,
                help_params='%s: %s' % (name, help_brief),
                category=CATEGORY_GENERAL,
                log=False)

    def _lane(self, gcmd):
        gate_number = gcmd.get_int(
            'GATE', None, minval=0, maxval=self.mmu.num_gates - 1)
        if gate_number is None:
            raise gcmd.error('NFC requires GATE=<gate>')
        gate = nfc_manager.nfc_gate_for_gate_number(gate_number)
        if gate is None:
            raise gcmd.error(
                'No enabled nfc_gate is configured for MMU gate %d'
                % gate_number)
        return gate

    def _shared(self, gcmd):
        shared = nfc_manager._shared_instance
        if shared is None or not getattr(shared, '_enabled', True):
            raise gcmd.error('No enabled shared NFC reader is configured')
        return shared

    def _defaults(self):
        return self.printer.lookup_object('nfc_gate', None)

    def _spoolman(self):
        defaults = self._defaults()
        if defaults is not None:
            return getattr(defaults, '_spoolman', None)
        for gate in nfc_manager._lane_instances:
            if getattr(gate, '_enabled', True):
                return getattr(gate, '_spoolman', None)
        return None

    def _run_lane(self, gcmd):
        gate = self._lane(gcmd)
        if nfc_manager._flag_param(gcmd, 'HELP'):
            gate._cmd_help(gcmd)
            return
        if gate._cmd_low_level_debug(gcmd):
            return
        read_value = gcmd.get('READ', None)
        if read_value is not None:
            gate._set_reading(
                gcmd, gcmd.get_int('READ', minval=0, maxval=1) == 1)
        elif nfc_manager._flag_param(gcmd, 'STATUS'):
            gcmd.respond_info(gate.status_line())
        elif gcmd.get_int('INIT', 0):
            gate._manual_init(gcmd)
        elif gcmd.get_int('SCAN', 0):
            gate._manual_scan(gcmd)
        elif gcmd.get_int('LED_TEST', 0):
            gate._lane_led_test(gcmd)
        elif gcmd.get_int('JOG_SCAN', 0):
            gate._manual_jog_scan(gcmd)
        elif gcmd.get_int('CLEAR_CACHE', 0) or gcmd.get_int('CLEAR', 0):
            gate._clear_spool_cache(gcmd)
        elif gcmd.get_int('POLL', 0):
            gate._poll()
            status = gate.status_line().strip()
            nfc_manager.logger.info(
                '[%s]: one poll complete; %s', gate._name, status)
            gcmd.respond_info(nfc_manager.color_console_tags(
                'NFC[%s]: one poll complete; %s' % (gate._name, status)))
        elif gcmd.get_int('APPLY', 0):
            gate._apply_current_spool(gcmd)
        elif gcmd.get_int('HH_SYNC', 0):
            gate._hh_sync(gcmd)
        else:
            gate._cmd_help(gcmd)

    def _run_shared(self, gcmd):
        shared = self._shared(gcmd)
        flag = nfc_manager._flag_param
        color = nfc_manager.color_console_tags
        logger = nfc_manager.logger

        if shared._cmd_low_level_debug(gcmd):
            return
        read_value = gcmd.get('READ', None)
        if read_value is not None:
            shared._set_reading(
                gcmd, gcmd.get_int('READ', minval=0, maxval=1) == 1)
        elif flag(gcmd, 'STATUS'):
            gcmd.respond_info(color(
                'NFC %s' % shared.shared_status_detail()))
        elif flag(gcmd, 'SUMMARY'):
            gcmd.respond_info(color(
                'NFC %s' % shared.shared_summary_line()))
        elif flag(gcmd, 'HELP'):
            shared._shared_help(gcmd)
        elif flag(gcmd, 'REPLACE'):
            shared._shared_replace_pending(gcmd)
        elif flag(gcmd, 'RESET'):
            shared._shared_reset_and_poll(gcmd)
        elif flag(gcmd, 'CLEAR'):
            shared._shared_clear_pending()
            shared._shared_last_error = None
            shared._shared_last_action = 'shared state cleared'
            shared._polling = False
            shared._shared_read_deadline = 0.0
            shared.reactor.update_timer(
                shared._poll_timer, shared.reactor.NEVER)
            shared._state.current_uid = None
            shared._state.current_spool = None
            logger.info('[%s]: shared state cleared', shared._name)
            gcmd.respond_info(color(
                'NFC[%s]: shared state cleared' % shared._name))
        elif flag(gcmd, 'PRELOAD_CHECK'):
            shared._shared_preload_check(gcmd)
        elif flag(gcmd, 'PRELOAD_COMMIT'):
            shared._shared_preload_commit(gcmd)
        elif flag(gcmd, 'PRELOAD_CLEAR_ASSIGNED'):
            shared._shared_preload_clear_assigned(gcmd)
        elif flag(gcmd, 'CANCEL'):
            shared._shared_clear_pending()
            shared._shared_last_error = None
            shared._shared_last_action = 'pending spool canceled'
            shared._polling = False
            shared._shared_read_deadline = 0.0
            shared.reactor.update_timer(
                shared._poll_timer, shared.reactor.NEVER)
            logger.info('[%s]: pending spool canceled', shared._name)
            gcmd.respond_info(color(
                'NFC[%s]: pending spool canceled' % shared._name))
        elif flag(gcmd, 'POLL'):
            if shared._is_printing():
                logger.warning(
                    '[%s]: shared poll skipped while printing', shared._name)
                gcmd.respond_info(
                    '[WARN] NFC[%s]: shared poll skipped while printing'
                    % shared._name)
                return
            shared._poll()
            status = shared.shared_status_line().strip()
            logger.info(
                '[%s]: shared POLL=1 complete — %s', shared._name, status)
            gcmd.respond_info(color(
                'NFC[%s]: one poll complete; %s' % (shared._name, status)))
        elif flag(gcmd, 'SCAN'):
            shared._manual_scan(gcmd)
        elif flag(gcmd, 'INIT'):
            shared._manual_init(gcmd)
        elif flag(gcmd, 'LED_TEST'):
            shared._shared_play_tag_read_effect(
                gcmd, duration=shared._shared_read_effect_duration)
        elif flag(gcmd, 'CLEAR_CACHE'):
            shared._shared_clear_cache(gcmd)
        else:
            shared._shared_help(gcmd)

    def _run_status(self, gcmd):
        gcmd.respond_info('\n'.join(
            nfc_manager._lane_status_lines(self.printer)))

    def _run_help(self, gcmd):
        gcmd.respond_info('\n'.join(nfc_manager._nfc_help(gcmd)))

    def _run_doctor(self, gcmd):
        gcmd.respond_info(nfc_manager.color_console_tags(
            '\n'.join(nfc_manager._doctor_lines(self.printer))))

    def _run_register(self, gcmd):
        nfc_manager._cmd_register_uid_to_spool(
            self.mmu.gcode, self._spoolman(), gcmd)

    def _run_led_test(self, gcmd):
        nfc_manager._cmd_led_test_all(gcmd)
