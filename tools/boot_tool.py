#!/usr/bin/env python3
"""
boot_tool.py — recovery-as-boot helper for Blackview BV7100 (MT6769, boot header v2).

On this phone ONE boot ramdisk serves both OrangeFox and the normal Android boot.
A ramdisk taken straight from a TWRP/OrangeFox build loses the stock
/first_stage_ramdisk (fstab + snapuserd for Virtual A/B), and Android no longer
boots. This tool therefore:

  * keeps the STOCK kernel, dtb, header, addresses and cmdline untouched,
  * takes the OrangeFox ramdisk,
  * replaces its /first_stage_ramdisk with the STOCK one (byte-identical),
  * compresses with gzip (the stock kernel only has CONFIG_RD_GZIP),
  * refuses to write an image that does not fit the boot partition.

Commands:
  info    <boot.img>
  inject  <stock_boot.img> <orangefox_boot.img | ramdisk(.cpio|.gz|.lz4)> <out.img>
"""
import gzip
import hashlib
import os
import struct
import sys
import zlib

KEEP_FROM_STOCK = ('first_stage_ramdisk',)
PART_SIZE = int(os.environ.get('BOOT_PARTITION_SIZE', '33554432'))


def align(x, a):
    return (x + a - 1) // a * a


class Boot:
    def __init__(self, data):
        if data[:8] != b'ANDROID!':
            raise SystemExit('not an Android boot image')
        (self.kernel_size, self.kernel_addr, self.ramdisk_size, self.ramdisk_addr,
         self.second_size, self.second_addr, self.tags_addr, self.page_size,
         self.version, self.os_version) = struct.unpack_from('<10I', data, 8)
        if self.version > 2:
            raise SystemExit('header v%d not handled here' % self.version)
        self.name = data[48:64]
        self.cmdline = data[64:576]
        self.extra_cmdline = data[608:1632]
        self.recovery_dtbo_size, self.recovery_dtbo_offset, self.header_size = 0, 0, 0
        self.dtb_size, self.dtb_addr = 0, 0
        if self.version >= 1:
            self.recovery_dtbo_size, self.recovery_dtbo_offset, self.header_size = struct.unpack_from('<IQI', data, 1632)
        if self.version >= 2:
            self.dtb_size, self.dtb_addr = struct.unpack_from('<IQ', data, 1648)
        pg = self.page_size
        o = pg
        self.kernel = data[o:o + self.kernel_size]; o += align(self.kernel_size, pg)
        self.ramdisk = data[o:o + self.ramdisk_size]; o += align(self.ramdisk_size, pg)
        self.second = data[o:o + self.second_size]; o += align(self.second_size, pg)
        self.recovery_dtbo = data[o:o + self.recovery_dtbo_size]; o += align(self.recovery_dtbo_size, pg)
        self.dtb = data[o:o + self.dtb_size]; o += align(self.dtb_size, pg)
        self.payload_end = o
        self.raw_header = bytearray(data[:pg])

    def build(self, ramdisk):
        pg = self.page_size
        h = self.raw_header
        struct.pack_into('<I', h, 16, len(ramdisk))
        sha = hashlib.sha1()
        for blob in (self.kernel, ramdisk, self.second):
            sha.update(blob); sha.update(struct.pack('<I', len(blob)))
        if self.version >= 1:
            sha.update(self.recovery_dtbo); sha.update(struct.pack('<I', len(self.recovery_dtbo)))
        if self.version >= 2:
            sha.update(self.dtb); sha.update(struct.pack('<I', len(self.dtb)))
        h[576:608] = sha.digest().ljust(32, b'\0')
        out = bytearray(h)
        for blob in (self.kernel, ramdisk, self.second, self.recovery_dtbo, self.dtb):
            out += blob + b'\0' * (align(len(blob), pg) - len(blob))
        return bytes(out)


def decompress(blob):
    if blob[:2] == b'\x1f\x8b':
        return gzip.decompress(blob)
    if blob[:4] == b'\x02\x21\x4c\x18':          # lz4 legacy
        import lz4.block
        o, out = 4, bytearray()
        while o + 4 <= len(blob):
            n, = struct.unpack_from('<I', blob, o)
            if n == 0x184C2102:
                o += 4; continue
            o += 4
            out += lz4.block.decompress(blob[o:o + n], uncompressed_size=8 << 20)
            o += n
        return bytes(out)
    if blob[:6] == b'070701':
        return blob
    raise SystemExit('unknown ramdisk compression: %s' % blob[:6].hex())


def cpio_parse(d):
    """Return list of (name, header_fields(list of 13 ints), data) in newc format."""
    out, o = [], 0
    while o + 110 <= len(d):
        if d[o:o + 6] != b'070701':
            raise SystemExit('bad cpio magic at %d' % o)
        f = [int(d[o + 6 + i * 8:o + 14 + i * 8], 16) for i in range(13)]
        nsize, fsize = f[11], f[6]
        name = d[o + 110:o + 110 + nsize - 1].decode()
        p = align(o + 110 + nsize, 4)
        data = d[p:p + fsize]
        o = align(p + fsize, 4)
        if name == 'TRAILER!!!':
            break
        out.append((name, f, data))
    return out


def cpio_write(entries):
    out = bytearray()
    ino = 300000
    for name, f, data in entries + [('TRAILER!!!', [0] * 13, b'')]:
        f = list(f)
        if name != 'TRAILER!!!':
            ino += 1
            f[0] = ino
        f[4] = f[4] if name != 'TRAILER!!!' else 1   # nlink
        f[6] = len(data)
        f[11] = len(name.encode()) + 1
        hdr = b'070701' + b''.join(b'%08X' % v for v in f)
        out += hdr + name.encode() + b'\0'
        out += b'\0' * (align(len(out), 4) - len(out))
        out += data
        out += b'\0' * (align(len(out), 4) - len(out))
    out += b'\0' * (align(len(out), 512) - len(out))
    return bytes(out)


def norm(n):
    return n[2:] if n.startswith('./') else n.lstrip('/')


def under(name, roots):
    n = norm(name)
    return any(n == r or n.startswith(r + '/') for r in roots)


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'info':
        b = Boot(open(sys.argv[2], 'rb').read())
        print('header v%d page %d kernel %d ramdisk %d (%s) dtb %d, payload %d of %d bytes' %
              (b.version, b.page_size, b.kernel_size, b.ramdisk_size, b.ramdisk[:4].hex(), b.dtb_size,
               b.payload_end, PART_SIZE))
        print('cmdline:', b.cmdline.split(b'\0')[0].decode(errors='replace'))
        return
    if cmd != 'inject':
        print(__doc__); sys.exit(1)

    stock_path, src_path, out_path = sys.argv[2:5]
    stock = Boot(open(stock_path, 'rb').read())
    src = open(src_path, 'rb').read()
    fox_rd = Boot(src).ramdisk if src[:8] == b'ANDROID!' else src

    stock_entries = cpio_parse(decompress(stock.ramdisk))
    fox_entries = cpio_parse(decompress(fox_rd))

    keep = [e for e in stock_entries if under(e[0], KEEP_FROM_STOCK)]
    if not keep:
        raise SystemExit('stock ramdisk has no first_stage_ramdisk?!')
    merged = [e for e in fox_entries if not under(e[0], KEEP_FROM_STOCK)] + keep
    names = {norm(e[0]) for e in merged}
    for must in ('init', 'first_stage_ramdisk/fstab.mt6768', 'first_stage_ramdisk/system/bin/snapuserd'):
        if must not in names:
            raise SystemExit('merged ramdisk is missing %s' % must)

    cpio = cpio_write(merged)
    comp = gzip.compress(cpio, compresslevel=9, mtime=0)
    img = stock.build(comp)

    # verification: re-parse, compare kernel/dtb/cmdline and stock first-stage files
    chk = Boot(img)
    assert chk.kernel == stock.kernel and chk.dtb == stock.dtb and chk.cmdline == stock.cmdline
    chk_entries = {norm(n): d for n, f, d in cpio_parse(decompress(chk.ramdisk))}
    for n, f, d in keep:
        assert chk_entries[norm(n)] == d, 'first-stage file changed: ' + n

    if len(img) > PART_SIZE:
        raise SystemExit('TOO BIG: %d bytes > boot partition %d (ramdisk gz %d bytes, need to cut %d bytes)' %
                         (len(img), PART_SIZE, len(comp), len(img) - PART_SIZE))
    open(out_path, 'wb').write(img)
    print('OK: %s %d bytes (%d%% of boot partition); ramdisk cpio %d -> gzip %d; kept %d stock first-stage entries'
          % (out_path, len(img), 100 * len(img) // PART_SIZE, len(cpio), len(comp), len(keep)))


if __name__ == '__main__':
    main()
