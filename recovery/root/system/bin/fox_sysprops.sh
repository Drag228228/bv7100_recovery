#!/system/bin/sh
# TrustKernel KeyMaster configures its TA with ro.build.version.release and
# ro.build.version.security_patch. The TA only accepts the values of the device's root of
# trust; anything else gives "TEE return -38" -> KEYMASTER_NOT_CONFIGURED and the
# metadata key can't be unwrapped. OrangeFox's own values (14 / build patch) never match.
#
# Same recipe as TrebleDroid's rw-system.sh (fixSPL), which GSIs use to feed this
# KeyMaster: Android release from vbmeta (com.android.build.system.os_version, else the
# boot header), patch level from the boot header. With a stock ROM these are the stock
# values anyway, so this works whatever system is installed. Never invent higher values:
# the TA would remember them and the real Android would lose its keys.
LOG=/tmp/fox_sysprops.log
exec >>$LOG 2>&1
echo "fox_sysprops start"

slot=$(getprop ro.boot.slot_suffix)
boot=/dev/block/by-name/boot$slot

# the descriptor lives in vbmeta_system (or in vbmeta when it is chained-less)
rel=$(for f in /dev/block/by-name/vbmeta*; do strings -n 2 "$f"; done 2>/dev/null \
      | grep -A1 com.android.build.system.os_version | grep -E '^[0-9]+$' | sort -n | head -n1)

# boot header v0-2: os_version at offset 44 = (A<<25 | B<<18 | C<<11 | year-2000<<4 | month)
v=$(od -An -tu4 -j44 -N4 "$boot" 2>/dev/null | tr -d ' ')
patch=""
if [ -n "$v" ] && [ "$v" != 0 ]; then
    pl=$((v & 2047))
    y=$((2000 + (pl >> 4))); m=$((pl & 15))
    [ $m -ge 1 ] && [ $m -le 12 ] && patch=$(printf '%d-%02d-01' $y $m)
    [ -n "$rel" ] || { a=$((v >> 25)); [ $a -gt 0 ] && rel=$a; }
fi

echo "vbmeta/boot: release=$rel patch=$patch"
for kv in "ro.build.version.release=$rel" "ro.build.version.security_patch=$patch"; do
    p=${kv%%=*}; val=${kv#*=}
    [ -n "$val" ] || continue
    echo "$p: $(getprop $p) -> $val"
    resetprop "$p" "$val"
done

setprop ctl.start keymaster-4-1-trustkernel
setprop ctl.start gatekeeper-1-0
echo "fox_sysprops done"
