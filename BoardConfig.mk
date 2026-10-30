#
# OrangeFox / TWRP device tree for Blackview BV7100
# SoC: MediaTek Helio G85 class (mt6768/MT6769), kernel 4.19, Android 12 stock
# No recovery partition: recovery is the ramdisk of boot (recovery-as-boot, header v2).
# The flashable image is made by tools/boot_tool.py from the STOCK boot.img.
#

DEVICE_PATH := device/blackview/BV7100

ALLOW_MISSING_DEPENDENCIES := true

# Architecture
TARGET_ARCH := arm64
TARGET_ARCH_VARIANT := armv8-2a
TARGET_CPU_ABI := arm64-v8a
TARGET_CPU_ABI2 :=
TARGET_CPU_VARIANT := generic
TARGET_CPU_VARIANT_RUNTIME := cortex-a75

TARGET_2ND_ARCH := arm
TARGET_2ND_ARCH_VARIANT := armv8-2a
TARGET_2ND_CPU_ABI := armeabi-v7a
TARGET_2ND_CPU_ABI2 := armeabi
TARGET_2ND_CPU_VARIANT := generic
TARGET_2ND_CPU_VARIANT_RUNTIME := cortex-a55

TARGET_SUPPORTS_64_BIT_APPS := true
TARGET_IS_64_BIT := true

# Platform
TARGET_BOOTLOADER_BOARD_NAME := BV7100
TARGET_NO_BOOTLOADER := true
TARGET_USES_UEFI := false
TARGET_BOARD_PLATFORM := mt6768
BOARD_HAS_MTK_HARDWARE := true

# Kernel: stock prebuilt (only used so the build can produce a boot.img;
# the final image keeps the stock kernel/dtb byte-for-byte anyway)
TARGET_PREBUILT_KERNEL := $(DEVICE_PATH)/prebuilt/Image.gz
TARGET_KERNEL_ARCH := arm64
TARGET_KERNEL_HEADER_ARCH := arm64
BOARD_KERNEL_IMAGE_NAME := Image.gz
TARGET_NO_KERNEL_OVERRIDE := true
BOARD_PREBUILT_DTBIMAGE_DIR := $(DEVICE_PATH)/prebuilt/dtb
BOARD_INCLUDE_DTB_IN_BOOTIMG := true

# Boot image layout (from stock boot.img header v2)
BOARD_BOOT_HEADER_VERSION := 2
BOARD_KERNEL_PAGESIZE := 2048
BOARD_KERNEL_BASE := 0x40078000
BOARD_KERNEL_OFFSET := 0x00008000
BOARD_RAMDISK_OFFSET := 0x07c08000
BOARD_KERNEL_TAGS_OFFSET := 0x0bc08000
BOARD_DTB_OFFSET := 0x0bc08000
BOARD_KERNEL_CMDLINE := bootopt=64S3,32N2,64N2 buildvariant=user
BOARD_MKBOOTIMG_ARGS += --header_version $(BOARD_BOOT_HEADER_VERSION)
BOARD_MKBOOTIMG_ARGS += --pagesize $(BOARD_KERNEL_PAGESIZE)
BOARD_MKBOOTIMG_ARGS += --base $(BOARD_KERNEL_BASE)
BOARD_MKBOOTIMG_ARGS += --kernel_offset $(BOARD_KERNEL_OFFSET)
BOARD_MKBOOTIMG_ARGS += --ramdisk_offset $(BOARD_RAMDISK_OFFSET)
BOARD_MKBOOTIMG_ARGS += --tags_offset $(BOARD_KERNEL_TAGS_OFFSET)
BOARD_MKBOOTIMG_ARGS += --dtb_offset $(BOARD_DTB_OFFSET)

# Recovery as boot (stock layout). Kernel only knows gzip ramdisks.
BOARD_USES_RECOVERY_AS_BOOT := true
TARGET_NO_RECOVERY := true
BOARD_RAMDISK_USE_LZ4 := false

# Partitions (MT6768_Android_scatter.txt)
BOARD_FLASH_BLOCK_SIZE := 131072
BOARD_BOOTIMAGE_PARTITION_SIZE := 33554432
BOARD_DTBOIMG_PARTITION_SIZE := 8388608

# Dynamic partitions (Virtual A/B), groups main_a/main_b in stock metadata
BOARD_SUPER_PARTITION_SIZE := 8589934592
BOARD_SUPER_PARTITION_GROUPS := main
BOARD_MAIN_SIZE := 8585740288
BOARD_MAIN_PARTITION_LIST := system vendor product

BOARD_SYSTEMIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_VENDORIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_PRODUCTIMAGE_FILE_SYSTEM_TYPE := ext4
BOARD_USERDATAIMAGE_FILE_SYSTEM_TYPE := ext4
TARGET_COPY_OUT_VENDOR := vendor
TARGET_COPY_OUT_PRODUCT := product
TARGET_USERIMAGES_USE_EXT4 := true
TARGET_USERIMAGES_USE_F2FS := true
BOARD_USES_METADATA_PARTITION := true

# A/B
AB_OTA_UPDATER := true
AB_OTA_PARTITIONS += boot dtbo vbmeta vbmeta_system vbmeta_vendor system vendor product

BOARD_AVB_ENABLE := true

# Must match stock so KeyMaster accepts the key blobs (update with stock firmware!)
PLATFORM_VERSION := 12
PLATFORM_SECURITY_PATCH := 2025-02-05
VENDOR_SECURITY_PATCH := 2025-02-05
BOOT_SECURITY_PATCH := 2025-02-05

# Recovery
TARGET_RECOVERY_FSTAB := $(DEVICE_PATH)/recovery/root/system/etc/recovery.fstab
TARGET_RECOVERY_PIXEL_FORMAT := RGBX_8888
RECOVERY_SDCARD_ON_DATA := true

# Crypto: FBE v2 + metadata encryption, TrustKernel KeyMaster 4.1 (HIDL)
TW_INCLUDE_CRYPTO := true
TW_INCLUDE_CRYPTO_FBE := true
TW_INCLUDE_FBE_METADATA_DECRYPT := true
TW_USE_FSCRYPT_POLICY := 2
TW_PREPARE_DATA_MEDIA_EARLY := true
TARGET_RECOVERY_DEVICE_MODULES += libkeymaster4 libkeymaster41 libpuresoftkeymasterdevice
TW_RECOVERY_ADDITIONAL_RELINK_LIBRARY_FILES += \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster4.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libkeymaster41.so \
    $(TARGET_OUT_SHARED_LIBRARIES)/libpuresoftkeymasterdevice.so

# TWRP UI
TW_THEME := portrait_hdpi
TARGET_SCREEN_WIDTH := 1080
TARGET_SCREEN_HEIGHT := 2408
TW_EXTRA_LANGUAGES := true
TW_DEFAULT_LANGUAGE := en
TW_SCREEN_BLANK_ON_BOOT := true
TW_BRIGHTNESS_PATH := "/sys/class/leds/lcd-backlight/brightness"
TW_MAX_BRIGHTNESS := 2047
TW_DEFAULT_BRIGHTNESS := 1200
TW_CUSTOM_BATTERY_PATH := "/sys/class/power_supply/battery"
TW_INPUT_BLACKLIST := "hbtp_vm"
TW_USE_TOOLBOX := true
TW_INCLUDE_RESETPROP := true
TW_INCLUDE_REPACKTOOLS := true
TW_INCLUDE_FASTBOOTD := true
TW_EXCLUDE_APEX := false
TW_HAS_EDL_MODE := false
TARGET_USES_MKE2FS := true
TW_FRAMERATE := 60

# Size: whole gzip ramdisk must fit next to the stock kernel in 32 MiB
TW_EXCLUDE_TWRPAPP := true
TW_EXCLUDE_NANO := true
TW_EXCLUDE_BASH := true
TW_EXCLUDE_PYTHON := true
TW_EXCLUDE_LPDUMP := false
TW_INCLUDE_NTFS_3G := false

TARGET_USES_LOGD := true
TWRP_INCLUDE_LOGCAT := true

BUILD_BROKEN_DUP_RULES := true
BUILD_BROKEN_ELF_PREBUILT_PRODUCT_COPY_FILES := true
BUILD_BROKEN_MISSING_REQUIRED_MODULES := true
