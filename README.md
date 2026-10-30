# HAUKI - Home Assistant Update Kiosk Interface

HAUKI fetches electricity spot prices from Home Assistant and shows the current price
and the cheapest 1h, 2h and 4h windows ahead on a Waveshare 2.13" V4 e-paper display,
driven by a Raspberry Pi 1A+. It makes it easy to pick the best time to run
high-consumption appliances like washing machines, dishwashers, or ovens.

Prices come from the Home Assistant
[ENTSO-E integration](https://github.com/mteiste/entsoe-prices)
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
install. Run them as the admin user over SSH. None of them is automated.

### 1. Passwordless sudo for the admin user (optional)

Only needed for non-interactive remote administration, e.g. by a coding agent over
SSH. Skip it if you prefer to type the sudo password.

```bash
u=$(id -un)
sudo sh -c "umask 337; echo '$u ALL=(ALL) NOPASSWD: ALL' > /tmp/010_$u-nopasswd && visudo -cf /tmp/010_$u-nopasswd && mv /tmp/010_$u-nopasswd /etc/sudoers.d/"
```

The user name is taken before `sudo`, so the rule is for the admin user, not root.

Undo: `sudo rm /etc/sudoers.d/010_$(id -un)-nopasswd`

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

Check the usual measures first. On a Raspberry Pi OS (trixie) image all three are
already in place, but they come from different places:

| Measure | Provided by | How to check |
|---------|-------------|--------------|
| Journal in RAM only | Raspberry Pi OS package `raspberrypi-sys-mods` (`Storage=volatile` drop-in) | `journalctl --header \| grep 'File path'` → `/run/log/journal/...` |
| `/tmp` in RAM | Debian 13 `systemd` (`tmp.mount`) | `findmnt /tmp` → `tmpfs` |
| No atime updates | `noatime` in `/etc/fstab` of the Raspberry Pi OS image | `findmnt /` → `noatime` |

If the journal is written to `/var/log/journal` instead, install the package:

```bash
sudo apt install raspberrypi-sys-mods
sudo systemctl restart systemd-journald
```

If `/` is mounted without `noatime`, edit `/etc/fstab` and add it to the options of
the root (`/`) line, e.g. `defaults` → `defaults,noatime`:

```text
PARTUUID=xxxxxxxx-02  /  ext4  defaults,noatime  0  1
```

Then apply it without rebooting and check:

```bash
sudo mount -o remount /
findmnt /
```

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

Set `prices.metering_interval` to match how your electricity meter reports
consumption to the provider:

| Value | Meter | Cheapest 1h/2h/4h windows start |
|-------|-------|---------------------------------|
| `900` | Quarter-hour metering | at any quarter (:00, :15, :30, :45) |
| `3600` | Hourly metering | on the hour only, because each whole hour is billed at its average price |

With hourly metering the large number is the current hour's average price (what this
hour's consumption is billed at), and the current 15-minute price is shown small in
the top-right corner, under the time slot.

## Installing the Service

After the OS preparation above, deploy from the workstation:

```bash
make deploy                 # or: make deploy PI_HOST=other-host
```

This copies the working tree to `~/hauki` on the Pi and runs `make install` there,
which:

- copies `src/` to `/opt/hauki/src` (owned by root, read-only for the service)
- installs `config.json` as `/opt/hauki/config.json`, owner root, group `hauki`,
  mode 0640, so only root and the service can read the token
- installs `hauki.service`, enables it and (re)starts it

Run `make deploy` again after every change; it restarts the service.

The service runs `/usr/bin/python3 src/main.py` as the `hauki` user. There is no venv
on the Pi: every dependency comes from the apt packages above. `lgpio`'s notification
pipe lives in the systemd runtime directory `/run/hauki` (`LG_WD`), and no bytecode
cache is written. systemd restarts the service 10 s after a crash and starts it at
boot.

```bash
sudo systemctl status hauki
sudo journalctl -u hauki -f      # errors only; a working service logs nothing
```

The display test uses the same GPIO pins, so stop the service before running
`tools/display_test.py` on the Pi (`sudo systemctl stop hauki`), and start it again
afterwards.

## Development

Development happens on a workstation (x86_64 or arm64 Linux), not on the Pi:

```bash
make prepare        # .venv with Ruff + Pillow, local Node.js 22 + markdownlint
make lint           # Ruff and markdownlint; always exits 0, read the output
.venv/bin/python tools/display_test.py --png preview   # layout preview, no hardware
```

`make prepare` creates the venv with `uv` when it is available, and keeps Node.js in
`.nodejs/` and markdownlint in `node_modules/`, all inside the project. Run it again
after changing `requirements-dev.txt` or `package.json`.

## License

HAUKI is licensed under GPLv3. See [LICENSE](LICENSE) for details.

`src/epd.py` is derived from Waveshare's e-Paper driver (MIT); see
[`LICENSES/WAVESHARE`](LICENSES/WAVESHARE).
