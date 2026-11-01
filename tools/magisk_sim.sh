#!/bin/bash
# Patch a boot image exactly like Magisk's boot_patch.sh (x86_64 magiskboot from the official
# APK) and check the result still fits the boot partition. Exit 1 if Magisk would fail with
# "Insufficient partition size".   usage: magisk_sim.sh boot.img [Magisk.apk]
set -e
IMG=$(readlink -f "$1")
PART=${BOOT_PARTITION_SIZE:-33554432}
W=$(mktemp -d); cd "$W"
APK=${2:-}
if [ -z "$APK" ]; then
    curl -sSL -o m.apk https://github.com/topjohnwu/Magisk/releases/download/v30.2/Magisk-v30.2.apk
    APK=m.apk
fi
unzip -q -o "$APK" lib/x86_64/libmagiskboot.so lib/arm64-v8a/libmagiskinit.so \
    lib/arm64-v8a/libmagisk.so lib/arm64-v8a/libinit-ld.so assets/stub.apk
B=$W/lib/x86_64/libmagiskboot.so; chmod +x "$B"
cp lib/arm64-v8a/libmagiskinit.so magiskinit; cp lib/arm64-v8a/libmagisk.so magisk
cp lib/arm64-v8a/libinit-ld.so init-ld; cp assets/stub.apk stub.apk
"$B" unpack "$IMG"
cp ramdisk.cpio ramdisk.cpio.orig
"$B" compress=xz magisk magisk.xz; "$B" compress=xz stub.apk stub.xz; "$B" compress=xz init-ld init-ld.xz
printf 'KEEPVERITY=true\nKEEPFORCEENCRYPT=true\nRECOVERYMODE=false\nSHA1=0\n' > config
"$B" cpio ramdisk.cpio "add 0750 init magiskinit" "mkdir 0750 overlay.d" "mkdir 0750 overlay.d/sbin" \
    "add 0644 overlay.d/sbin/magisk.xz magisk.xz" "add 0644 overlay.d/sbin/stub.xz stub.xz" \
    "add 0644 overlay.d/sbin/init-ld.xz init-ld.xz" "patch" "backup ramdisk.cpio.orig" \
    "mkdir 000 .backup" "add 000 .backup/.magisk config"
"$B" repack "$IMG" new.img
SZ=$(stat -c%s new.img)
# payload end (without the AVB footer padding)
END=$(python3 -c "import struct,sys;b=open('new.img','rb').read();f=b[-64:]
print(struct.unpack('>Q',f[12:20])[0] if f[:4]==b'AVBf' else len(b))")
cd /; rm -rf "$W"
if [ "$SZ" -le "$PART" ]; then
    echo "Magisk patch OK: payload $END bytes, $((PART - END)) bytes free in the $PART byte partition"
else
    echo "Magisk patch FAILS: image $SZ bytes > partition $PART (over by $((SZ - PART)))"; exit 1
fi
