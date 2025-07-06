# Generating SysInfoExtended

`libgpod` relies on a file named `SysInfoExtended` stored under
`iPod_Control/Device` to identify a connected iPod. The
`ipod-listener` service automatically invokes `ipod-read-sysinfo-extended`
the first time it mounts an iPod if the file is missing. To run the tool
manually instead, follow these steps:

1. Mount the iPod so it is accessible on the filesystem. With the
   `ipod-listener` service enabled this will typically be
   `/opt/ipod-dock/mnt/ipod`.
2. Determine the block device path for the iPod, e.g. `/dev/sda`.
3. Run the utility with the device path and mount point:

   ```bash
   sudo ipod-read-sysinfo-extended /dev/sda /opt/ipod-dock/mnt/ipod
   ```

   Substitute the correct device node for `/dev/sda` if different. Root
   privileges are usually required.
4. Confirm that the file
   `/opt/ipod-dock/mnt/ipod/iPod_Control/Device/SysInfoExtended` now exists.

Having this file in place allows libgpod to determine the iPod's Firewire ID and
update the iTunes database correctly.
