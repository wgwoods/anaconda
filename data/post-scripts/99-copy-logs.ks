# Note, this script log will not be copied to the installed system.
%post --nochroot

NOSAVE_INPUT_KS_FILE=/tmp/NOSAVE_INPUT_KS
NOSAVE_LOGS_FILE=/tmp/NOSAVE_LOGS

if [ -e ${NOSAVE_LOGS_FILE} ]; then
    rm -f ${NOSAVE_LOGS_FILE}
else
    mkdir -p $ANA_INSTALL_PATH/var/log/anaconda
    for log in anaconda.log syslog X.log program.log packaging.log storage.log ifcfg.log yum.log dnf.log dnf.rpm.log lvm.log; do
        [ -e /tmp/$log ] && cp /tmp/$log $ANA_INSTALL_PATH/var/log/anaconda/
    done
    cp /tmp/ks-script*.log $ANA_INSTALL_PATH/var/log/anaconda/
    journalctl -b > $ANA_INSTALL_PATH/var/log/anaconda/journal.log
    chmod 0600 $ANA_INSTALL_PATH/var/log/anaconda/*
fi

if [ -e ${NOSAVE_INPUT_KS_FILE} ]; then
    rm -f ${NOSAVE_INPUT_KS_FILE}
else
    [ -e /run/install/ks.cfg ] && cp /run/install/ks.cfg $ANA_INSTALL_PATH/root/original-ks.cfg
fi

%end
