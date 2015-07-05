#!/bin/bash

command -v wait_for_dd >/dev/null || . /lib/anaconda-lib.sh

# Don't leave initqueue until we've finished with the requested dd stuff
if [ -n "$dd_disk" -o -n "$dd_net" -o -n "$dd_interactive" ]; then
    wait_for_dd
fi

# Run driver-updates for LABEL=OEMDRV and any other requested disk
for dd in LABEL=OEMDRV $dd_disk; do
    dd_cmd="/sbin/initqueue --onetime --unique --name dd_disk /bin/driver-updates --disk $dd \$devnode"
    printf 'SUBSYSTEM=="block", %s, RUN+="%s"\n' "$(udevmatch $dd)" "$dd_cmd"
done > /etc/udev/rules.d/91-anaconda-driverdisk.rules

# NOTE: dd_net is handled by fetch-driver-net.sh
