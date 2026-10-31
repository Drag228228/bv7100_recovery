#!/system/bin/sh
# KeyMaster (TrustKernel) configures the TA with ro.build.version.release and
# ro.build.version.security_patch. The TA remembers the highest OS patch level it has
# seen (rollback protection), so the recovery's own values (14 / 2025-02-05) are
# rejected: "TEE return -38" -> every operation fails with KEYMASTER_NOT_CONFIGURED and
# the metadata key can't be unwrapped. Copy the installed system's values before
# KeyMaster starts. Never set values HIGHER than the system's: the TA would raise its
# stored level and the real Android would then fail to boot its keys.
LOG=/tmp/fox_sysprops.log
exec >>$LOG 2>&1
echo "fox_sysprops start $(date)"
slot=$(getprop ro.boot.slot_suffix)
dev=/dev/block/mapper/system$slot
i=0
while [ ! -e "$dev" ] && [ $i -lt 150 ]; do sleep 0.1; i=$((i+1)); done
if [ -e "$dev" ]; then
    mnt=/tmp/fox_sys
    mkdir -p $mnt
    if mount -o ro "$dev" $mnt; then
        for bp in $mnt/system/build.prop $mnt/build.prop; do
            [ -f "$bp" ] || continue
            for p in ro.build.version.release ro.build.version.security_patch; do
                v=$(grep -m1 "^$p=" "$bp" | cut -d= -f2-)
                [ -n "$v" ] || continue
                echo "$p: $(getprop $p) -> $v"
                resetprop "$p" "$v"
            done
            break
        done
        umount $mnt
    else
        echo "mount $dev failed"
    fi
else
    echo "$dev did not appear, keeping recovery values"
fi
setprop ctl.start keymaster-4-1-trustkernel
setprop ctl.start gatekeeper-1-0
echo "fox_sysprops done"
