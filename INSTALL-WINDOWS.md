# Installing on Windows 11

Download the latest `.nvda-addon` from
<https://github.com/NorlayOfficial/norlay-link-checker/releases/latest>
or from <https://norlay.fit/norlay-link-checker/>. The file name below is
the current release; adjust it if a newer one is available.

The message

```
Windows cannot access the specified device, path, or file.
You may not have the appropriate permissions to access the item.
```

is produced by Windows **before NVDA ever opens the file**. Because the same
message appeared for the copy on the OneDrive desktop and for the copy on the
flash drive, the file itself is not the problem. Either the `.nvda-addon` file
association on that PC points at a program that no longer exists, or security
software is blocking the file. Both are fixed by installing without
double-clicking.

## 1. Verify the file first

Run this in PowerShell, using the real drive letter:

```powershell
$file = "E:\norlayLinkChecker-1.1.3.nvda-addon"
Get-Item -LiteralPath $file | Select-Object Length
certutil -hashfile $file SHA256
```

Expected:

```
Length: 135342
SHA256: 71768199d44eeb9661209bba19c4bb1d264b9d61867be9232776f2bfbfa1d05f
```

If `certutil` prints the hash, Windows can read the bytes and NVDA will be able
to use the file. If it cannot, the drive or the copy is faulty, not the add-on.

## 2. Option 1: install without opening the file (recommended)

This unpacks the archive straight into NVDA's add-ons folder. It never uses the
`.nvda-addon` association, the shell, or SmartScreen.

Quit NVDA first (`NVDA+Q`), then run:

```powershell
$src  = "E:\norlayLinkChecker-1.1.3.nvda-addon"
$zip  = "$env:TEMP\norlayLinkChecker-1.1.3.zip"
$dest = "$env:APPDATA\nvda\addons\norlayLinkChecker"

Copy-Item -LiteralPath $src -Destination $zip -Force
Remove-Item -Recurse -Force $dest -ErrorAction SilentlyContinue
New-Item -ItemType Directory -Force -Path $dest | Out-Null
Expand-Archive -LiteralPath $zip -DestinationPath $dest -Force
Get-ChildItem $dest | Select-Object Name
```

The last command must list `manifest.ini`, `doc` and `globalPlugins` directly.
If it lists one folder called `norlayLinkChecker-1.1.3` instead, the archive was
unpacked one level too deep; move its contents up one level.

Then start NVDA.

### Explorer-only version

1. Press `Win+R`, type `%APPDATA%\nvda\addons`, press Enter.
2. On the flash drive, rename the file ending from `.nvda-addon` to `.zip`.
3. Right-click it, choose **Extract All**.
4. Set the destination to the `addons` folder you opened, with the subfolder
   name `norlayLinkChecker`.
5. Check that `manifest.ini` is directly inside that folder, then start NVDA.

## 3. Option 2: install from inside NVDA

This also bypasses the association.

1. Start NVDA.
2. Open the NVDA menu, then **Tools**, then **Add-on Store**.
3. Press **Install from external source** (Alt+X).
4. In the File name box, **type** the full path instead of browsing to it:
   `E:\norlayLinkChecker-1.1.3.nvda-addon`
5. Press Enter, confirm the install, and restart NVDA.

## 4. Option 3: repair the association (optional)

Only needed if you want double-clicking to work in future.

1. Right-click the `.nvda-addon` file, choose **Open with**, then
   **Choose another app**.
2. Pick **NVDA** and tick **Always use this app**.
3. If NVDA is not listed, choose **More apps**, then **Look for another app on
   this PC**, and select `nvda.exe` (usually `C:\Program Files\NVDA\nvda.exe`).

A portable NVDA copy has no fixed `nvda.exe` location, which is the usual reason
the association breaks. Portable copies also keep add-ons inside the portable
folder, so use Option 2 or the Add-on Store there.

## If it still fails

Check whether antivirus removed or quarantined the file:

1. Open **Windows Security**, then **Virus and threat protection**.
2. Open **Protection history**.
3. If Norlay Link Checker appears there, choose **Restore** and allow it.

Then confirm the file was not damaged in transfer:

```powershell
Get-FileHash "$env:TEMP\norlayLinkChecker-1.1.3.zip" -Algorithm SHA256
```

The hash must still be
`71768199D44EEB9661209BBA19C4BB1D264B9D61867BE9232776F2BFBFA1D05F`.

## Confirm it loaded

Open NVDA menu, Tools, Add-on Store, Installed add-ons. **Norlay Link Checker**
should be listed with version 1.1.3. NVDA menu, Tools should also contain
**Explain link in clipboard**.

## Removing it

With NVDA closed, delete `%APPDATA%\nvda\addons\norlayLinkChecker`, or use
Add-on Store, Installed add-ons, Remove.
