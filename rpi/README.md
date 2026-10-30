# HAUKI — Raspberry Pi 1A+

CPython implementation of HAUKI for a Raspberry Pi 1A+ driving a Waveshare 2.13" V4
e-ink display over SPI. Prices come from the Home Assistant
[ENTSO-E integration](https://git.teiste.dedyn.io/mte/entsoe-prices)
(`sensor.electricity_price`).

## Target System

| Item | Value |
|------|-------|
| Board | Raspberry Pi Model A Plus Rev 1.1 (256 MB, ARMv6) |
| OS | Raspbian GNU/Linux 13 (trixie), 32-bit, headless |
| Python | 3.13 (system) |
| Hostname | `hauki` |

## OS Preparation

These steps are done once, by hand, on a fresh Raspberry Pi OS Lite (trixie)
install. Run them as the admin user (`mte`) over SSH. None of them is automated.

### 1. Passwordless sudo for the admin user (optional)

Only needed for non-interactive remote administration, e.g. by a coding agent over
SSH. Skip it if you prefer to type the sudo password.

```bash
sudo sh -c 'umask 337; echo "mte ALL=(ALL) NOPASSWD: ALL" > /tmp/010_mte-nopasswd && visudo -cf /tmp/010_mte-nopasswd && mv /tmp/010_mte-nopasswd /etc/sudoers.d/'
```

Undo: `sudo rm /etc/sudoers.d/010_mte-nopasswd`

### 2. Time zone and clock

HAUKI has no time zone setting of its own. Prices arrive with UTC timestamps, and the
"@ HH:MM" times on the display are converted with the OS local time zone
(`/etc/localtime`), including DST. The Pi must be set to the local zone and keep its
clock synchronised:

```bash
sudo timedatectl set-timezone Europe/Helsinki
timedatectl
```

`timedatectl` should show `Time zone: Europe/Helsinki (EET, +0200)` (EEST, +0300 in
summer) and `System clock synchronized: yes`. The Pi has no battery-backed clock, so
it relies on network time (`systemd-timesyncd`, enabled by default). At boot,
timesyncd restores the last known time, so until the first sync the clock is behind
and the displayed price can briefly be for the wrong slot.

Don't set `TZ` in the service environment: it would override `/etc/localtime`.

### 3. System packages

```bash
sudo apt update
sudo apt install fonts-dejavu-core python3-pil rsync
```

- `fonts-dejavu-core` provides `/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf`,
  the display font.
- `python3-pil` (Pillow) comes from apt instead of pip; building Pillow from source on
  ARMv6 is very slow.
- `rsync` is used to copy the code onto the Pi.

Already installed on the stock image and used by HAUKI: `python3-venv`,
`python3-spidev`, `python3-lgpio`, `python3-requests`.

> `RPi.GPIO` (provided by `python3-rpi-lgpio` on trixie) does **not** work on this
> board: it fails with `This module does not understand old-style revision codes`.
> GPIO access has to go through the kernel GPIO character device (`/dev/gpiochip0`),
> e.g. with `lgpio`.

### 4. Boot configuration: SPI on, graphics off

Edit `/boot/firmware/config.txt` (keep a backup copy):

```bash
sudo cp -p /boot/firmware/config.txt /boot/firmware/config.txt.orig
sudo nano /boot/firmware/config.txt
```

Changes against the stock file:

```diff
-#dtparam=spi=on
+dtparam=spi=on
...
-camera_auto_detect=1
+#camera_auto_detect=1
...
-display_auto_detect=1
+#display_auto_detect=1
...
-dtoverlay=vc4-kms-v3d
-max_framebuffers=2
+#dtoverlay=vc4-kms-v3d
+#max_framebuffers=2
...
 [all]
 enable_uart=1
+
+# Headless: minimum GPU memory (uses start_cd.elf / fixup_cd.dat)
+gpu_mem=16
```

- `dtparam=spi=on` creates `/dev/spidev0.0` (CE0, BCM 8), used by the display.
- Removing the KMS graphics driver and setting `gpu_mem=16` gives the memory to Linux:
  the ARM/GPU split goes from 192/64 MB to 240/16 MB (about 221 MiB visible,
  about 125 MiB available).
- With `gpu_mem=16` the firmware loads the cut-down `start_cd.elf`. Check that it
  exists in `/boot/firmware/`.

### 5. Block the VideoCore camera/codec modules

The cut-down firmware lacks the GPU services these drivers need. Without this step
they load anyway and log `Failed to open VCHI service` errors at boot.

```bash
{
  echo "# HAUKI headless: gpu_mem=16 firmware lacks the VideoCore camera/codec services"
  for m in bcm2835_codec bcm2835_v4l2 bcm2835_isp bcm2835_mmal_vchiq vc_sm_cma; do
    echo "blacklist $m"
    echo "install $m /bin/false"
  done
} | sudo tee /etc/modprobe.d/hauki-headless.conf
```

`blacklist` alone only stops automatic loading. The `install … /bin/false` lines also
stop the modules from being loaded as dependencies.

### 6. Reboot and verify

```bash
sudo reboot
```

A Pi 1 takes about four minutes before SSH answers again. Then check:

```bash
ls -l /dev/spidev0.0                 # owned by group spi
vcgencmd get_mem arm                 # arm=240M
vcgencmd get_mem gpu                 # gpu=16M
lsmod | grep -E 'vc4|mmal|vc_sm'     # no output
sudo dmesg | grep -i vchi            # no output
```

### 7. Reduce SD card writes

Stock trixie already does the usual things:

| Measure | How to check |
|---------|--------------|
| Journal in RAM only | `journalctl --header \| grep 'File path'` → `/run/log/journal/...` |
| `/tmp` in RAM | `findmnt /tmp` → `tmpfs` |
| No atime updates | `findmnt /` → `noatime` |

The remaining periodic writers are switched off:

```bash
# No daily apt list downloads / unattended upgrades — update by hand instead
sudo systemctl disable --now apt-daily.timer apt-daily-upgrade.timer

# No periodic zram writeback to /var/swap. Swap stays as compressed RAM (zram0).
sudo mkdir -p /etc/rpi/swap.conf.d
printf '# HAUKI: no periodic zram writeback to the SD card\n[Zram]\nWritebackTrigger=manual\n' \
  | sudo tee /etc/rpi/swap.conf.d/hauki.conf
sudo systemctl daemon-reload
sudo systemctl stop rpi-zram-writeback.timer
sudo systemctl reset-failed rpi-zram-writeback.timer
```

`rpi-zram-writeback.timer` is created by the `rpi-swap` generator at boot, so it can't
be disabled with `systemctl disable`. The `WritebackTrigger=manual` drop-in stops it
being created.

With the apt timers off, update the system by hand from time to time:

```bash
sudo apt update && sudo apt upgrade
```

Undo: `sudo systemctl enable --now apt-daily.timer apt-daily-upgrade.timer` and
`sudo rm /etc/rpi/swap.conf.d/hauki.conf && sudo systemctl daemon-reload`.

### 8. Service user

HAUKI runs as a dedicated system user, `hauki`. It has no home or login shell, and is
in the `spi` and `gpio` groups, which own `/dev/spidev0.*` and `/dev/gpiochip0`:

```bash
sudo useradd --system --no-create-home --home-dir /nonexistent \
  --shell /usr/sbin/nologin --groups spi,gpio hauki
sudo -u hauki test -w /dev/spidev0.0 -a -w /dev/gpiochip0 && echo OK
```

## Display

The Waveshare 2.13" V4 HAT plugs straight onto the Pi's 40-pin header, so no separate
wiring is needed. The HAT fixes the pins, and the `display` defaults in
`config.json.example` already match it (RST=17, DC=25, BUSY=24, BCM numbering).
Chip select is SPI0 CE0 (BCM 8), driven by the kernel SPI driver, so it is not configured.

## Configuration

```bash
cp config.json.example config.json
```

Set the Home Assistant `url` and long-lived `token`, and check the `prices.entity_id`
(`sensor.electricity_price`). `config.json` holds the token, so it is git-ignored and
should be readable only by its owner and the `hauki` group.

## Installing the Service

**In progress.** The display driver (`src/eink.py`) is being rewritten for `spidev` +
`lgpio`, and the deployment steps (`make prepare`, `make install`, `hauki.service`)
will be updated with it. Until then, `make help` lists the existing targets.
