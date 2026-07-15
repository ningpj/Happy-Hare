# NFC/RFID Core Migration Changelog

## July 14, 2026 — Standalone NFC integration moved into Happy Hare core

This update begins the migration of the standalone Happy Hare RFID reader
project into the native Happy Hare architecture. NFC/RFID is no longer treated
as a separately configured `nfc_gate` extension. Reader hardware, runtime
behavior, commands, macros, installer choices, and LED feedback now follow the
same ownership model as other Happy Hare components.

### Major changes

- Moved the NFC/RFID runtime modules from the standalone `extras/nfc_gates`
  package into the core `extras/mmu` package.
- Kept the physical reader drivers with the other MMU unit hardware under
  `extras/mmu/unit/nfc`.
- Added an MMU-native NFC unit component so reader managers are created during
  normal `MmuUnit` initialization.
- NFC managers now bind to physical `[mmu_nfc_reader]` objects configured by
  `mmu_hardware.cfg`.
- Added native support for shared-reader, per-lane, and hybrid reader layouts.
- Added shared-reader bypass support to the native configuration model.
- Moved all NFC GCode registration and routing into the standard Happy Hare
  command package as `mmu_nfc.py`.
- Moved NFC runtime settings into the NFC Reader section of
  `mmu_parameters.cfg`.
- Moved NFC presentation and effect selections into the NFC Reader section of
  `mmu_macro_vars.cfg`.
- Retained `config/macros/mmu_nfc.cfg` for the Happy Hare preload hooks, gate
  map handoff macros, and standard `[mmu_led_effect]` definitions.
- Converted NFC LED feedback to use Happy Hare's core `MmuLedManager` for lane,
  shared, bypass, scan, warning, ready, unresolved, and test effects.
- Expanded the installer with NFC topology, reader hardware, Spoolman, tag
  parsing, polling, scan motion, shared-reader, bypass, logging, and LED
  presentation choices.
- Added conditional installer menus so dependent NFC settings appear only when
  their parent feature is enabled.
- Removed the obsolete standalone NFC optional configuration files. Their
  settings are now rendered into the standard Happy Hare base configuration.

### Configuration ownership after migration

| Concern | Happy Hare location |
|---|---|
| Physical readers and unit assignments | `config/base/mmu_hardware.cfg` |
| Runtime behavior | `config/base/mmu_parameters.cfg` |
| Presentation and LED variables | `config/base/mmu_macro_vars.cfg` |
| Preload hooks, gate-map handoff, and LED effects | `config/macros/mmu_nfc.cfg` |
| Installer selections | `installer/Kconfig.nfc_reader` |
| NFC commands | `extras/mmu/commands/mmu_nfc.py` |
| Unit lifecycle | `extras/mmu/unit/mmu_nfc.py` |

### Retired standalone structure

- The `extras/nfc_gates` orchestration package is no longer the runtime owner.
- `config/optional/mmu_nfc.cfg` is no longer required.
- `config/optional/mmu_nfc_shared.cfg` is no longer required.
- Separate NFC LED management has been removed in favor of Happy Hare's LED
  manager.
- Separate `[nfc_gate laneN]` and `[nfc_gate shared]` construction is no longer
  required for installer-generated configurations.

### Compatibility during transition

- Native managers continue to expose the established `nfc_gate laneN` and
  `nfc_gate shared` printer status names so existing NFC macros can transition
  without an immediate interface break.
- The existing NFC command names and shared preload workflow are retained while
  their ownership moves into core Happy Hare.
- Spoolman lookup, rich-tag parsing, scan-jog behavior, shared preload staging,
  and gate-map synchronization remain available in the core layout.

### Migration direction

The intended end state is for NFC/RFID to behave like any other optional Happy
Hare capability: selected in the installer, rendered into the standard base
configuration, created through the MMU lifecycle, controlled through the core
command registry, and coordinated by Happy Hare's existing unit, LED, gate-map,
and Spoolman systems.
