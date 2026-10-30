# OrangeFox для Blackview BV7100 (mt6768)

Дерево устройства и сборка OrangeFox Recovery для **Blackview BV7100** (сток Android 12, ядро 4.19). Работает и при установленной GSI (например, Matrixx), если vendor стоковый.

## Почему прошлая сборка ломала загрузку

На BV7100 нет раздела `recovery`: рекавери — это рамдиск внутри `boot` (recovery-as-boot). Тот же рамдиск используется и при обычном запуске Android, и в нём лежит `first_stage_ramdisk` (fstab, `snapuserd` для Virtual A/B). Обычная сборка TWRP/OrangeFox кладёт свой рамдиск без стоковой `first_stage_ramdisk`, и система перестаёт загружаться.

Здесь сборка (GitHub Actions) собирает OrangeFox, а затем `tools/boot_tool.py`:

* берёт **стоковый** `boot.img` (лежит в `stock/`): ядро, dtb, заголовок, cmdline остаются побайтно стоковыми;
* заменяет рамдиск на OrangeFox, но **переносит стоковую `first_stage_ramdisk` целиком**;
* сжимает gzip (ядро понимает только gzip) и проверяет, что образ помещается в раздел (32 МиБ).

## Установка

1. Загрузчик разблокирован.
2. Скачай `OrangeFox-…-BV7100-boot-….img` из [Releases](../../releases), проверь `sha256`.
3. Сначала **сохрани текущий boot** (на случай Magisk/другого ядра).
4. ```
   fastboot flash boot OrangeFox-…-BV7100-boot-….img
   fastboot reboot recovery
   ```
   Пишется в текущий слот.

**Не трогай `vbmeta`.** Если стоял Magisk — после прошивки пропатчи этот образ Magisk'ом заново (рекавери при этом сохранится, Magisk умеет recovery-as-boot).

**Не прошивай** файлы из `debug/` и не используй «переустановку OrangeFox» из самого рекавери.

## Откат

```
xz -d stock/boot.img.xz
fastboot flash boot stock/boot.img
```

## Прошивка

Под сток `Blackview/BV7100_EEA/BV7100:12/SP1A.210812.016/1742619299` (патч 2025-02-05). При обновлении стока заменить `stock/boot.img.xz`, `stock/SHA256SUMS` и патч в `BoardConfig.mk`.

## Расшифровка

FBE v2 + метаданные (ext4, `/metadata` = `md_udc`). TEE — TrustKernel: KeyMaster 4.1 (HIDL), Gatekeeper 1.0. Блобы — `recovery/root/vendor/`, запуск — `recovery/root/init.recovery.trustkernel.rc`.

## Что вырезано, чтобы влезть в 32 МБ

Раздел `boot` 32 МБ, стоковое ядро занимает ~11 МБ, а полный OrangeFox — ~33 МБ (gzip). Поэтому `tools/boot_tool.py` урезает рамдиск по спискам `tools/ramdisk_trim*.txt` (второй и третий уровень применяются, только если первого не хватило):

1. языки интерфейса кроме English/Русский/Українська; китайский и декоративные шрифты заменены на Roboto (выбор шрифта в настройках работает, просто выглядит как Roboto); `update_engine_sideload` (установка A/B OTA-zip — для BV7100 таких прошивок нет, GSI шьются через fastbootd, он оставлен); bash, zip, ozip, keystore_cli и неиспользуемые библиотеки; отладочные символы из бинарников OrangeFox (вендорные блобы не трогаются);
2. шрифты интерфейса InterDisplay/GoogleSans → Roboto, украинский язык;
3. logd/logcat (лог самого OrangeFox `/tmp/recovery.log` остаётся).

Скрипт проверяет, что ни одна оставшаяся программа не потеряла нужную ей библиотеку, и исправляет `ramdisk-files.txt` (по нему OrangeFox перепаковывает сам себя).
