LOCAL_PATH := device/blackview/BV7100

PRODUCT_SHIPPING_API_LEVEL := 31
PRODUCT_USE_DYNAMIC_PARTITIONS := true
PRODUCT_TARGET_VNDK_VERSION := 31

# A/B
AB_OTA_POSTINSTALL_CONFIG += \
    RUN_POSTINSTALL_system=true \
    POSTINSTALL_PATH_system=system/bin/otapreopt_script \
    FILESYSTEM_TYPE_system=ext4 \
    POSTINSTALL_OPTIONAL_system=true

PRODUCT_PACKAGES += \
    otapreopt_script \
    update_engine \
    update_engine_sideload \
    update_verifier \
    checkpoint_gc

# fastbootd
PRODUCT_PACKAGES += \
    android.hardware.fastboot@1.0-impl-mock \
    fastbootd

# Keymaster / gatekeeper client side
PRODUCT_PACKAGES += \
    android.hardware.keymaster@4.0 \
    android.hardware.keymaster@4.1 \
    android.hardware.gatekeeper@1.0 \
    libgatekeeper \
    libkeymaster4 \
    libkeymaster41 \
    libpuresoftkeymasterdevice

PRODUCT_PROPERTY_OVERRIDES += \
    ro.crypto.dm_default_key.options_format.version=2 \
    ro.crypto.volume.metadata.method=dm-default-key \
    ro.crypto.volume.filenames_mode=aes-256-cts \
    ro.crypto.volume.options=::v2 \
    ro.crypto.allow_encrypt_override=true

PRODUCT_SOONG_NAMESPACES += $(LOCAL_PATH)
