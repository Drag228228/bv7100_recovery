$(call inherit-product, $(SRC_TARGET_DIR)/product/core_64_bit.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/aosp_base.mk)
$(call inherit-product, $(SRC_TARGET_DIR)/product/virtual_ab_ota.mk)
$(call inherit-product, vendor/twrp/config/common.mk)
$(call inherit-product, device/blackview/BV7100/device.mk)

PRODUCT_DEVICE := BV7100
PRODUCT_NAME := twrp_BV7100
PRODUCT_BRAND := Blackview
PRODUCT_MODEL := BV7100
PRODUCT_MANUFACTURER := Blackview
PRODUCT_RELEASE_NAME := BV7100

PRODUCT_GMS_CLIENTID_BASE := android-blackview
