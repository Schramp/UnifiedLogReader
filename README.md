# UnifiedLogReader

A parser for Unified logging .tracev3 files.

NOTE: I think mandiant is running faster then this project. Check out their version as well

https://github.com/mandiant/macos-UnifiedLogs


## Project Status

### alpha (experimental)

_This is a work in progress. Currently this does not support the first version of tracev3 which is seen on macOS 10.12.0 (which uses catalog v2). It has been tested to work on catalog v3 files used in macOS 10.12.5 upto the current 10.15. Also tested on iOS 12.x successfully._

| Version              | Status          | Method of testing |
|----------------------|-----------------|-------------------|
| macOS 10.12.5- 10.15 | tested to work  | Unknown           |
| iOS 16               | tested          | diff of textlog shows minor differences (uninterpereted tags and values mostly e.g. 0 means false)|
| iOS 18               | tested to work  |  Not compared (yet) |

Support for iOS 16.x is tested.

Support for iOS 18.x is tested.

## License

MIT

## Requirements & Installation

Python 3.6+ and the following modules
* lz4
* biplist
* ipaddress

**The version on PyPi is old, and I need to discuss with @ydkhatri about the release process.**

UnifiedLogReader (and the dependencies) can be installed using **`pip install git+https://github.com/Schramp/UnifiedLogReader.git lz4 biplist ipaddress`**

Do not download from here, unless you want the latest code.
For development, if you only need the dependencies, use `pip install -r requirements.txt`

## Usage

The script needs access to files from 3 folders _(same on iOS or macOS)_
* /private/var/db/diagnostics
* /private/var/db/diagnostics/timesync
* /private/var/db/uuidtext

The tracev3 files are located within the diagnostics folder. If you have a disk image, just extract the diagnostics and uuidtext folders (shown at paths above) and provide it to this script.

Currently the script supports the default log output format, TSV and sqlite output.

## Output options

_SQLITE_ gives you every available field in an sqlite db  
_TSV_ALL_ gives you every available field in a tab-seperated file  
_LOG_DEFAULT_ gives only those fields shown by 'log' utility (with no options specified)


```
G:\>c:\Python37-32\python.exe c:\Github\UnifiedLogReader\UnifiedLogReader.py -h
usage: UnifiedLogReader.py [-h] [-f OUTPUT_FORMAT] [-l LOG_LEVEL]
                           uuidtext_path timesync_path tracev3_path
                           output_path

UnifiedLogReader is a tool to read macOS Unified Logging tracev3 files.
This is version 0.3 tested on macOS 10.12.5 - 10.15 and iOS 12.

Notes:
-----
If you have a .logarchive, then point uuidtext_path to the .logarchive folder,
 the timesync folder is within the logarchive folder

positional arguments:
  uuidtext_path         Path to uuidtext folder (/var/db/uuidtext)
  timesync_path         Path to timesync folder (/var/db/diagnostics/timesync)
  tracev3_path          Path to either tracev3 file or folder to recurse (/var/db/diagnostics)
  output_path           An existing folder where output will be saved

optional arguments:
  -h, --help            show this help message and exit
  -f OUTPUT_FORMAT, --output_format OUTPUT_FORMAT
                        SQLITE, TSV_ALL, LOG_DEFAULT  (Default is LOG_DEFAULT)
  -l LOG_LEVEL, --log_level LOG_LEVEL
                        Log levels: INFO, DEBUG, WARNING, ERROR (Default is INFO)
```

## Testing / validation

The iOS 16.x unified logging has been tested by comparing the output of "log show" on macOS to the output of this project.

```bash
UnifiedLogReader.py -t True system_logs.logarchive/ system_logs.logarchive/timesync/ system_logs.logarchive/Persist/ /tmp/decode_log/output
```
The output is not exactly ordered by time and there are small rounding errors on the timestamps (at the last digit), these differences have been ignored during comparison:

```bash
sort /tmp/decode_log/output/logs.txt | tee /tmp/decode_log/output/logs_sorted.txt | sed -E "s/^(2023....................)../\100/g" >/tmp/decode_log/output/logs_sorted_ts.txt
```

The the output is compared using diff (GNU diffutils) 3.7.

```bash
diff -W 450 --side-by-side -w  /tmp/decode_log2/output8/logs_sorted_ts.txt  /usr/users/work/MyLife/iPhone14/system_logs.logarchive_stripped_ts.txt
```

notable differences:
* whitespace
* microseconds
* constants that can be interpretted
* newlines in the mac showlog output 

```{size="tiny"}
2023-06-01 10:56:04.247100+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> Model name = <private>                                                        2023-06-01 10:56:04.247100+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> Model name = <private>
2023-06-01 10:56:04.252600+0200 0x665      Error       0x0                  95     0    fseventsd: [com.apple.fsevents:daemon] event logs in <private> with volume UUID [<private>] and f_flags[0x14809098] out of sync with    2023-06-01 10:56:04.252600+0200 0x665      Error       0x0                  95     0    fseventsd: [com.apple.fsevents:daemon] event logs in <private> with volume UUID [<private>] and f_flags[0x14809098] out of sync with 
2023-06-01 10:56:04.253200+0200 0x69c      Default     0x0                  55     0    mobiletimerd: (libMobileGestalt.dylib) Cache loaded with 5238 pre-cached in CacheData and 56 items in CacheExtra.                       2023-06-01 10:56:04.253200+0200 0x69c      Default     0x0                  55     0    mobiletimerd: (libMobileGestalt.dylib) Cache loaded with 5238 pre-cached in CacheData and 56 items in CacheExtra.
2023-06-01 10:56:04.253800+0200 0x65d      Activity    0x40                 93     0    fairplayd.H2: (libsystem_containermanager.dylib) container_system_path_for_identifier                                                   2023-06-01 10:56:04.253800+0200 0x65d      Activity    0x40                 93     0    fairplayd.H2: (libsystem_containermanager.dylib) container_system_path_for_identifier
2023-06-01 10:56:04.253900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> retrieved current device boot-args: <private>                                 2023-06-01 10:56:04.253900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> retrieved current device boot-args: <private>
2023-06-01 10:56:04.253900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> retrieved current device boot-args: <private>                                 2023-06-01 10:56:04.253900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> retrieved current device boot-args: <private>
2023-06-01 10:56:04.254800+0200 0x643      Default     0x0                  51     0    keybagd: (libMobileGestalt.dylib) Cache loaded with 5238 pre-cached in CacheData and 56 items in CacheExtra.                            2023-06-01 10:56:04.254800+0200 0x643      Default     0x0                  51     0    keybagd: (libMobileGestalt.dylib) Cache loaded with 5238 pre-cached in CacheData and 56 items in CacheExtra.
2023-06-01 10:56:04.255200+0200 0x648      Default     0x0                  61     0    thermalmonitord: (libMobileGestalt.dylib) Cache loaded with 5238 pre-cached in CacheData and 56 items in CacheExtra.                    2023-06-01 10:56:04.255200+0200 0x648      Default     0x0                  61     0    thermalmonitord: (libMobileGestalt.dylib) Cache loaded with 5238 pre-cached in CacheData and 56 items in CacheExtra.
2023-06-01 10:56:04.258200+0200 0x65d      Activity    0x41                 93     0    fairplayd.H2: (libsystem_containermanager.dylib) container_query_t                                                                      2023-06-01 10:56:04.258200+0200 0x65d      Activity    0x41                 93     0    fairplayd.H2: (libsystem_containermanager.dylib) container_query_t
2023-06-01 10:56:04.258800+0200 0x665      Error       0x0                  95     0    fseventsd: [com.apple.fsevents:daemon] event posted for <private>                                                                       2023-06-01 10:56:04.258800+0200 0x665      Error       0x0                  95     0    fseventsd: [com.apple.fsevents:daemon] event posted for <private>
2023-06-01 10:56:04.261900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> Using SensorExchangeHelper                                                    2023-06-01 10:56:04.261900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> Using SensorExchangeHelper
2023-06-01 10:56:04.261900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> Using ACSK                                                                    2023-06-01 10:56:04.261900+0200 0x648      Default     0x0                  61     0    thermalmonitord: [com.apple.cltm:thermalmonitor] <Notice> Using ACSK
2023-06-01 10:56:04.276800+0200 0x648      Default     0x0                  61     0    thermalmonitord: (CoreBrightness) [com.apple.CoreBrightness:default] Register notification block                                        2023-06-01 10:56:04.276800+0200 0x648      Default     0x0                  61     0    thermalmonitord: (CoreBrightness) [com.apple.CoreBrightness:default] Register notification block
2023-06-01 10:56:04.278100+0200 0x648      Default     0x0                  61     0    thermalmonitord: (IOMobileFramebuffer) iomfb_populate_display_infos: Local call to iomfb_match_callback                                 2023-06-01 10:56:04.278100+0200 0x648      Default     0x0                  61     0    thermalmonitord: (IOMobileFramebuffer) iomfb_populate_display_infos: Local call to iomfb_match_callback
2023-06-01 10:56:04.278200+0200 0x648      Default     0x0                  61     0    thermalmonitord: (IOMobileFramebuffer) iomfb_match_callback: primary                                                                    2023-06-01 10:56:04.278200+0200 0x648      Default     0x0                  61     0    thermalmonitord: (IOMobileFramebuffer) iomfb_match_callback: primary
2023-06-01 10:56:04.278400+0200 0x643      Activity    0x21                 51     0    keybagd: (NearField) registerForRemoteCallbacks                                                                                         2023-06-01 10:56:04.278400+0200 0x643      Activity    0x21                 51     0    keybagd: (NearField) registerForRemoteCallbacks
2023-06-01 10:56:04.284300+0200 0x643      Default     0x21                 51     0    keybagd: (NearField) [com.apple.nfc:Logging] -[NFHardwareManager <private>]:177                                                         2023-06-01 10:56:04.284300+0200 0x643      Default     0x21                 51     0    keybagd: (NearField) [com.apple.nfc:Logging] -[NFHardwareManager <private>]:177
2023-06-01 10:56:04.352100+0200 0x688      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_register: com.apple.iomfb_bics_daemon, criteria: check   2023-06-01 10:56:04.352100+0200 0x688      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_register: com.apple.iomfb_bics_daemon, criteria: check
2023-06-01 10:56:04.472700+0200 0x688      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] _xpc_activity_register: com.apple.iomfb_bics_daemon (0x9969061c0),    2023-06-01 10:56:04.472700+0200 0x688      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] _xpc_activity_register: com.apple.iomfb_bics_daemon (0x9969061c0), 
2023-06-01 10:56:04.472700+0200 0x688      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_set_criteria: com.apple.iomfb_bics_daemon (0x9969061c0   2023-06-01 10:56:04.472700+0200 0x688      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_set_criteria: com.apple.iomfb_bics_daemon (0x9969061c0
2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_set_criteria, lower half: com.apple.iomfb_bics_daemon    2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_set_criteria, lower half: com.apple.iomfb_bics_daemon 
2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] _xpc_activity_set_criteria: com.apple.iomfb_bics_daemon (0x9969061c   2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] _xpc_activity_set_criteria: com.apple.iomfb_bics_daemon (0x9969061c
2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_set_criteria: com.apple.iomfb_bics_daemon (0x9969061c0   2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] xpc_activity_set_criteria: com.apple.iomfb_bics_daemon (0x9969061c0
2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] __XPC_ACTIVITY_CALLING_HANDLER__: com.apple.iomfb_bics_daemon (0x99 <
2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] _xpc_activity_set_state: com.apple.iomfb_bics_daemon (0x9969061c0),   2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] _xpc_activity_set_state: com.apple.iomfb_bics_daemon (0x9969061c0),
                                                                                                                                                                                                                              > 2023-06-01 10:56:04.472800+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (libxpc.dylib) [com.apple.xpc.activity:Client] __XPC_ACTIVITY_CALLING_HANDLER__: com.apple.iomfb_bics_daemon (0x99
2023-06-01 10:56:04.475400+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (IOMobileFramebuffer) iomfb_populate_display_infos: Local call to iomfb_match_callback                               2023-06-01 10:56:04.475400+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (IOMobileFramebuffer) iomfb_populate_display_infos: Local call to iomfb_match_callback
2023-06-01 10:56:04.475500+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (IOMobileFramebuffer) iomfb_match_callback: primary                                                                  2023-06-01 10:56:04.475500+0200 0x6bc      Default     0x0                  97     0    IOMFB_bics_daemon: (IOMobileFramebuffer) iomfb_match_callback: primary
2023-06-01 10:56:04.497700+0200 0x65d      Activity    0x42                 93     0    fairplayd.H2: (libsystem_containermanager.dylib) container_copy_object                                                                  2023-06-01 10:56:04.497700+0200 0x65d      Activity    0x42                 93     0    fairplayd.H2: (libsystem_containermanager.dylib) container_copy_object
2023-06-01 10:56:04.509200+0200 0x673      Default     0x0                  75     0    bluetoothuserd: [com.apple.bluetoothuser:daemon] Launching bluetoothuserd (<private>)                                                   2023-06-01 10:56:04.509200+0200 0x673      Default     0x0                  75     0    bluetoothuserd: [com.apple.bluetoothuser:daemon] Launching bluetoothuserd (<private>)
2023-06-01 10:56:04.611900+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> updated state, will   2023-06-01 10:56:04.611900+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> updated state, will
2023-06-01 10:56:04.612000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> updated state, will   2023-06-01 10:56:04.612000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> updated state, will
2023-06-01 10:56:04.612000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): Notifying <private> of state    2023-06-01 10:56:04.612000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): Notifying <private> of state 
2023-06-01 10:56:04.612000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:ApplicationManager] Third party driver feature flag <private> enabled                                         2023-06-01 10:56:04.612000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:ApplicationManager] Third party driver feature flag <private> enabled
2023-06-01 10:56:04.612100+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:ApplicationManager] Hardware does not support third party drivers                                             2023-06-01 10:56:04.612100+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:ApplicationManager] Hardware does not support third party drivers
2023-06-01 10:56:04.612100+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:ApplicationManager] Third party driver boot arg <private> enabled                                             2023-06-01 10:56:04.612100+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:ApplicationManager] Third party driver boot arg <private> enabled
2023-06-01 10:56:04.612100+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> did not update stat   2023-06-01 10:56:04.612100+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> did not update stat
2023-06-01 10:56:04.612200+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): Notifying <private> of state    2023-06-01 10:56:04.612200+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): Notifying <private> of state 
2023-06-01 10:56:04.616800+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> did not update stat   2023-06-01 10:56:04.616800+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): <private> did not update stat
2023-06-01 10:56:04.616800+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): completed                       2023-06-01 10:56:04.616800+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Daemon has activated): completed
2023-06-01 10:56:04.616900+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): starting                            2023-06-01 10:56:04.616900+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): starting
2023-06-01 10:56:04.616900+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): Notifying <private> of state upda   2023-06-01 10:56:04.616900+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): Notifying <private> of state upda
2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> updated state:,<private | 2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> updated state:
                                                                                                                                                                                                                              > <private>
2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> updated state, will not   2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> updated state, will not
2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> updated state, will not   2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> updated state, will not
2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): Notifying <private> of state upda   2023-06-01 10:56:04.618000+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): Notifying <private> of state upda
2023-06-01 10:56:04.618600+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> did not update state      2023-06-01 10:56:04.618600+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> did not update state
2023-06-01 10:56:04.618600+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): Notifying <private> of state upda   2023-06-01 10:56:04.618600+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): Notifying <private> of state upda
2023-06-01 10:56:04.620700+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> did not update state      2023-06-01 10:56:04.620700+0200 0x64d      Default     0x0                  73     0    driverkitd: [com.apple.km:StateManagement] State refresh (id: <private>, reason: Sent new drivers): <private> did not update state

```

