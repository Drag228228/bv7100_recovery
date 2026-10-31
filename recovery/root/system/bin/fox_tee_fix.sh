#!/system/bin/sh
# The TEE (teed + Gatekeeper/KeyMaster TAs) writes its secure-storage files while we are in
# recovery (e.g. Gatekeeper's throttle record when the pattern is checked). The recovery's
# SELinux policy does not know the vendor types, so new files get "unlabeled" (and may be
# root-owned). Android's teed (user system, domain tee) then can't open them: Gatekeeper
# panics ("Can not open meta file") and Android rejects the correct PIN/pattern.
# Put back the stock owner and labels (vendor_file_contexts + trustkernel.rc).
# chcon of a type unknown to the loaded policy works here: root has CAP_MAC_ADMIN and
# recovery is permissive.
# usage: fox_tee_fix.sh [once]
LOG=/tmp/fox_tee_fix.log

fix() { # dir label
    [ -d "$1" ] || return 0
    chown -R 1000:1000 "$1" 2>>$LOG
    chcon -R "$2" "$1" 2>>$LOG
}

run() {
    fix /mnt/vendor/persist/t6   u:object_r:tkcore_protect_data_file:s0
    fix /mnt/vendor/protect_f/tee u:object_r:protect_f_data_file:s0
    # only the real (decrypted) /data, not the placeholder dir on rootfs
    if mountpoint -q /data; then
        fix /data/vendor/t6     u:object_r:tkcore_data_file:s0
        fix /data/vendor/t6/app u:object_r:tkcore_spta_file:s0
        [ -f /data/vendor/t6/tkcore.log ] && chcon u:object_r:tkcore_log_file:s0 /data/vendor/t6/tkcore.log 2>>$LOG
    fi
}

if [ "$1" = once ]; then
    run
    sync
    echo "once done" >>$LOG
    exit 0
fi
echo "fox_tee_fix loop start" >>$LOG
while true; do
    run
    sleep 5
done
