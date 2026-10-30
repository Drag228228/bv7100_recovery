# OrangeFox build variables for Blackview BV7100
FDEVICE="BV7100"

fox_get_target_device() {
  local chkdev=$(echo "$BASH_SOURCE" | grep -w "$FDEVICE")
  if [ -n "$chkdev" ]; then FOX_BUILD_DEVICE="$FDEVICE"; else chkdev=$(set | grep BASH_ARGV | grep -w "$FDEVICE"); [ -n "$chkdev" ] && FOX_BUILD_DEVICE="$FDEVICE"; fi
}
[ -z "$1" -a -z "$FOX_BUILD_DEVICE" ] && fox_get_target_device

if [ "$1" = "$FDEVICE" -o "$FOX_BUILD_DEVICE" = "$FDEVICE" ]; then
  export TW_DEFAULT_LANGUAGE="en"
  export LC_ALL="C"
  export ALLOW_MISSING_DEPENDENCIES=true

  # recovery-as-boot, Virtual A/B
  export FOX_RECOVERY_INSTALL_PARTITION="/dev/block/by-name/boot"
  export FOX_VIRTUAL_AB_DEVICE=1
  export OF_AB_DEVICE=1
  export FOX_AB_DEVICE=1
  export OF_VIRTUAL_AB_DEVICE=1
  export FOX_RECOVERY_SYSTEM_PARTITION="/dev/block/mapper/system"
  export FOX_RECOVERY_VENDOR_PARTITION="/dev/block/mapper/vendor"
  export OF_NO_TREBLE_COMPATIBILITY_CHECK=1

  # never patch stock boot/encryption automatically; keep system bootable
  export OF_DONT_PATCH_ENCRYPTED_DEVICE=1
  export OF_NO_RELOAD_AFTER_DECRYPTION=1
  export OF_KEEP_DM_VERITY_FORCED_ENCRYPTION=1
  export OF_SKIP_FBE_DECRYPTION_SDKVERSION=99
  export OF_NO_MIUI_PATCH_WARNING=1
  export OF_PATCH_AVB20=0
  export FOX_DELETE_AROMAFM=1

  # screen
  export OF_SCREEN_H=2408
  export OF_STATUS_H=80
  export OF_STATUS_INDENT_LEFT=48
  export OF_STATUS_INDENT_RIGHT=48
  export OF_ALLOW_DISABLE_NAVBAR=0
  export OF_CLOCK_POS=1

  # size: the ramdisk is gzip and must fit next to the stock kernel in 32 MiB
  export FOX_REMOVE_AAPT=1
  export FOX_REMOVE_BASH=1
  export FOX_REMOVE_ZIP_BINARY=1
  export FOX_EXCLUDE_NANO_EDITOR=1
  export OF_USE_LZ4_COMPRESSION=0
  export FOX_USE_XZ_UTILS=0

  # misc
  export OF_USE_GREEN_LED=0
  export OF_FLASHLIGHT_ENABLE=0
  export OF_USE_MAGISKBOOT=1
  export OF_USE_MAGISKBOOT_FOR_ALL_PATCHES=1
  export FOX_BUGGED_AOSP_ARB_WORKAROUND="1616300800"
  export FOX_VERSION="R12.1_BV7100"
  export OF_MAINTAINER="Drag228228"
  echo "OrangeFox vars for $FDEVICE loaded"
fi
